# Copyright (C) 2025 Advanced Micro Devices, Inc. All rights reserved.
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
SAML 2.0 Authenticator

SP-initiated SAML 2.0 SSO authenticator for JupyterHub using python3-saml.
Designed for Okta integration but compatible with any SAML 2.0 IdP.
"""

from __future__ import annotations

import logging
from jupyterhub.auth import Authenticator
from jupyterhub.handlers import BaseHandler
from jupyterhub.utils import url_path_join
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.idp_metadata_parser import OneLogin_Saml2_IdPMetadataParser
from tornado import web
from traitlets import Bool, Unicode

log = logging.getLogger("jupyterhub.auth.saml")

_cached_idp_metadata: dict | None = None


def _prepare_tornado_request(handler):
    """Convert a Tornado request into the dict format expected by python3-saml."""
    request = handler.request
    host = request.headers.get("X-Forwarded-Host", request.host)
    proto = request.headers.get("X-Forwarded-Proto", request.protocol)
    path = request.path
    return {
        "https": "on" if proto == "https" else "off",
        "http_host": host,
        "script_name": path,
        "path_info": "",
        "get_data": {k: handler.get_argument(k) for k in handler.request.arguments},
        "post_data": {
            k: v[-1].decode("utf-8", errors="replace")
            for k, v in handler.request.body_arguments.items()
        },
    }


class CustomSAMLAuthenticator(Authenticator):
    """SAML 2.0 SP-initiated SSO authenticator for JupyterHub."""

    login_service = Unicode(
        "AMD SSO",
        config=True,
        help="Label shown on the login button (e.g. 'AMD SSO', 'Okta SSO').",
    )

    idp_metadata_url = Unicode(
        "",
        config=True,
        help="URL to fetch IdP metadata XML. Preferred over manual IdP config.",
    )

    idp_entity_id = Unicode(
        "",
        config=True,
        help="IdP entity ID. Required if idp_metadata_url is not set.",
    )

    idp_sso_url = Unicode(
        "",
        config=True,
        help="IdP Single Sign-On URL. Required if idp_metadata_url is not set.",
    )

    idp_slo_url = Unicode(
        "",
        config=True,
        help="IdP Single Logout URL (optional).",
    )

    idp_x509_cert = Unicode(
        "",
        config=True,
        help="IdP X.509 signing certificate (PEM, base64-encoded body only).",
    )

    sp_entity_id = Unicode(
        "",
        config=True,
        help="SP entity ID. Auto-derived from request if not set.",
    )

    sp_acs_url = Unicode(
        "",
        config=True,
        help="SP Assertion Consumer Service URL. Auto-derived from request if not set.",
    )

    sp_x509_cert = Unicode(
        "",
        config=True,
        help="SP certificate for signed requests (optional).",
    )

    sp_private_key = Unicode(
        "",
        config=True,
        help="SP private key for signed requests (optional).",
    )

    username_attribute = Unicode(
        "",
        config=True,
        help="SAML attribute to use as username. Empty means use NameID.",
    )

    group_attribute = Unicode(
        "",
        config=True,
        help="SAML attribute containing group memberships (optional).",
    )

    want_assertions_signed = Bool(
        True,
        config=True,
        help="Require SAML assertions to be signed.",
    )

    want_response_signed = Bool(
        False,
        config=True,
        help="Require the SAML response envelope to be signed.",
    )

    def _get_base_url(self, handler):
        """Derive the external base URL from request headers."""
        request = handler.request
        host = request.headers.get("X-Forwarded-Host", request.host)
        proto = request.headers.get("X-Forwarded-Proto", request.protocol)
        return f"{proto}://{host}"

    def _get_handler_prefix(self, handler):
        """Derive the handler prefix from the request path.

        In standalone mode, handlers are at /hub/login, /hub/acs, etc.
        In multi-auth mode with url_prefix="/saml", they're at
        /hub/saml/login, /hub/saml/acs, etc. We need to determine the
        correct base path for SP URLs (entity ID, ACS URL).
        """
        path = handler.request.path
        hub_base = handler.hub.base_url.rstrip("/")
        # Strip the handler-specific suffix to get the prefix
        for suffix in ("/login", "/acs", "/metadata"):
            if path.endswith(suffix):
                return path[: -len(suffix)]
        return hub_base

    def _build_saml_settings(self, handler):
        """Build the python3-saml settings dict from configured traitlets."""
        base_url = self._get_base_url(handler)
        prefix = self._get_handler_prefix(handler)

        entity_id = self.sp_entity_id or f"{base_url}{prefix}/metadata"
        acs_url = self.sp_acs_url or f"{base_url}{prefix}/acs"

        settings = {
            "strict": True,
            "debug": False,
            "sp": {
                "entityId": entity_id,
                "assertionConsumerService": {
                    "url": acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
                "x509cert": self.sp_x509_cert,
                "privateKey": self.sp_private_key,
                "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
            },
            "idp": {
                "entityId": self.idp_entity_id,
                "singleSignOnService": {
                    "url": self.idp_sso_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "x509cert": self.idp_x509_cert,
            },
            "security": {
                "wantAssertionsSigned": self.want_assertions_signed,
                "wantMessagesSigned": self.want_response_signed,
                "authnRequestsSigned": bool(self.sp_private_key),
                "nameIdEncrypted": False,
                "wantNameId": True,
                "wantNameIdEncrypted": False,
                "wantAssertionsEncrypted": False,
                "signMetadata": bool(self.sp_private_key),
            },
        }

        if self.idp_slo_url:
            settings["idp"]["singleLogoutService"] = {
                "url": self.idp_slo_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            }

        # Merge IdP metadata if URL is configured (overrides inline IdP config)
        global _cached_idp_metadata
        if self.idp_metadata_url:
            if _cached_idp_metadata is None:
                log.info("Fetching IdP metadata from %s", self.idp_metadata_url)
                _cached_idp_metadata = OneLogin_Saml2_IdPMetadataParser.parse_remote(
                    self.idp_metadata_url
                )
            for key in ("idp",):
                if key in _cached_idp_metadata:
                    settings[key].update(_cached_idp_metadata[key])

        return settings

    def login_url(self, base_url):
        return url_path_join(base_url, "login")

    async def authenticate(self, handler, data=None):
        if data is None:
            return None

        username = data.get("username", "").strip().lower()
        if not username:
            return None

        if ":" in username:
            log.warning("Rejected SAML username containing ':': %s", username)
            return None

        auth_state = {
            "saml_attributes": data.get("saml_attributes", {}),
            "session_index": data.get("session_index"),
        }

        return {"name": username, "auth_state": auth_state}

    async def refresh_user(self, user, handler=None):
        return True

    def get_handlers(self, app):
        authenticator = self

        class SAMLLoginHandler(BaseHandler):
            """Initiates SP-initiated SAML SSO by redirecting to the IdP."""

            async def get(self):
                saml_settings = authenticator._build_saml_settings(self)
                req = _prepare_tornado_request(self)
                auth = OneLogin_Saml2_Auth(req, saml_settings)

                next_url = self.get_argument("next", "")
                redirect_url = auth.login(return_to=next_url)
                self.redirect(redirect_url)

        class SAMLACSHandler(BaseHandler):
            """Assertion Consumer Service — receives and validates the SAML Response."""

            def check_xsrf_cookie(self):
                pass

            async def post(self):
                saml_settings = authenticator._build_saml_settings(self)
                req = _prepare_tornado_request(self)
                auth = OneLogin_Saml2_Auth(req, saml_settings)
                auth.process_response()

                errors = auth.get_errors()
                if errors:
                    log.error(
                        "SAML response validation failed: %s (reason: %s)",
                        errors,
                        auth.get_last_error_reason(),
                    )
                    raise web.HTTPError(401, "SAML authentication failed")

                if not auth.is_authenticated():
                    raise web.HTTPError(401, "SAML authentication failed")

                # Extract username
                if authenticator.username_attribute:
                    attrs = auth.get_attributes()
                    values = attrs.get(authenticator.username_attribute, [])
                    username = values[0] if values else ""
                else:
                    username = auth.get_nameid()

                saml_attributes = auth.get_attributes()
                session_index = auth.get_session_index()

                data = {
                    "username": username,
                    "saml_attributes": saml_attributes,
                    "session_index": session_index,
                }

                authenticated = await authenticator.authenticate(self, data)
                if authenticated is None:
                    raise web.HTTPError(401, "SAML authentication failed: invalid username")

                user_name = authenticated["name"]
                user = self.find_user(user_name)
                if user is None:
                    user = self.user_from_username(user_name)

                if authenticated.get("auth_state"):
                    await user.save_auth_state(authenticated["auth_state"])

                self.set_login_cookie(user)

                relay_state = self.get_argument("RelayState", "")
                next_url = relay_state or url_path_join(self.hub.base_url, "home")
                self.redirect(next_url)

        class SAMLMetadataHandler(BaseHandler):
            """Serves SP metadata XML for IdP configuration."""

            def check_xsrf_cookie(self):
                pass

            async def get(self):
                from onelogin.saml2.settings import OneLogin_Saml2_Settings

                saml_settings = authenticator._build_saml_settings(self)
                settings = OneLogin_Saml2_Settings(saml_settings, sp_validation_only=True)
                metadata = settings.get_sp_metadata()
                errors = settings.validate_metadata(metadata)

                if errors:
                    log.error("SP metadata validation errors: %s", errors)
                    raise web.HTTPError(500, "Invalid SP metadata")

                self.set_header("Content-Type", "application/xml")
                self.write(metadata)

        return [
            (r"/login", SAMLLoginHandler),
            (r"/acs", SAMLACSHandler),
            (r"/metadata", SAMLMetadataHandler),
        ]
