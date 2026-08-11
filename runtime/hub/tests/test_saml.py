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

import asyncio
import importlib.util
import inspect
import sys
import types
from contextlib import suppress
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"

# ---------------------------------------------------------------------------
# Stub external dependencies so the module can be imported without installing
# JupyterHub, python3-saml, Tornado, etc.
# ---------------------------------------------------------------------------

if "traitlets" not in sys.modules:
    traitlets_module = types.ModuleType("traitlets")
    traitlets_module.Bool = lambda default=False, **kw: default
    traitlets_module.Unicode = lambda default="", **kw: default
    traitlets_module.Int = lambda default=0, **kw: default
    sys.modules["traitlets"] = traitlets_module

if "jupyterhub" not in sys.modules:
    sys.modules["jupyterhub"] = types.ModuleType("jupyterhub")

if "jupyterhub.auth" not in sys.modules:
    auth_module = types.ModuleType("jupyterhub.auth")

    class _StubAuthenticator:
        """Mirrors the parts of jupyterhub.auth.Authenticator that SAML relies on.

        Kept faithful to the real signatures (both policy checks are synchronous
        on the base class) so tests exercise the same contract as production.
        """

        login_service = ""
        allow_all = False
        blocked_users = frozenset()
        allowed_users = frozenset()

        def normalize_username(self, username):
            return username.lower()

        def validate_username(self, username):
            return bool(username) and "/" not in username

        def check_blocked_users(self, username, authentication=None):
            if not self.blocked_users:
                return True
            return username not in self.blocked_users

        def check_allowed(self, username, authentication=None):
            if self.allow_all:
                return True
            return username in self.allowed_users

    auth_module.Authenticator = _StubAuthenticator
    sys.modules["jupyterhub.auth"] = auth_module

if "jupyterhub.handlers" not in sys.modules:
    handlers_module = types.ModuleType("jupyterhub.handlers")
    handlers_module.BaseHandler = type("BaseHandler", (), {})
    sys.modules["jupyterhub.handlers"] = handlers_module

if "jupyterhub.utils" not in sys.modules:
    utils_module = types.ModuleType("jupyterhub.utils")

    def _url_path_join(*pieces):
        """Mirror jupyterhub.utils.url_path_join, including leading/trailing slashes.

        A naive join drops the leading slash, which matters here: a cookie Path
        that does not start with "/" is ignored by browsers (RFC 6265 5.2.4),
        so a lossy stub would hide a real scoping regression.
        """
        pieces = list(pieces)
        while pieces and not pieces[-1]:
            del pieces[-1]
        if not pieces:
            return ""
        initial = pieces[0].startswith("/")
        final = pieces[-1].endswith("/")
        result = "/".join(s for s in (p.strip("/") for p in pieces) if s)
        if initial:
            result = "/" + result
        if final:
            result = result + "/"
        return "/" if result == "//" else result

    utils_module.url_path_join = _url_path_join

    async def _maybe_future(obj):
        """Mirror jupyterhub.utils.maybe_future: await awaitables, pass through values."""
        if inspect.isawaitable(obj):
            return await obj
        return obj

    utils_module.maybe_future = _maybe_future
    sys.modules["jupyterhub.utils"] = utils_module

if "tornado" not in sys.modules:
    # Prefer the real package when it is installed; sibling test modules import
    # tornado.escape, which a bare stub would shadow. Fall back to a stub marked
    # as a namespace package so those imports still resolve if it is absent.
    if importlib.util.find_spec("tornado") is not None:
        import tornado  # noqa: F401
    else:
        tornado_module = types.ModuleType("tornado")
        tornado_module.__path__ = []
        sys.modules["tornado"] = tornado_module

# Unlike the stubs above, tornado.web is installed unconditionally. Sibling test
# modules register a bare HTTPError stub that discards its status code, so
# honouring an existing registration would make these assertions depend on
# collection order. Both this stub and real Tornado expose ``status_code``.
if not hasattr(sys.modules.get("tornado.web"), "HTTPError") or not hasattr(
    getattr(sys.modules.get("tornado.web"), "HTTPError", None), "status_code"
):

    def _http_error_init(self, code, msg="", *args, **kwargs):
        Exception.__init__(self, f"HTTP {code}: {msg}")
        self.status_code = code
        self.log_message = msg

    web_module = types.ModuleType("tornado.web")
    web_module.HTTPError = type("HTTPError", (Exception,), {"__init__": _http_error_init, "status_code": None})
    sys.modules["tornado.web"] = web_module

if "onelogin" not in sys.modules:
    sys.modules["onelogin"] = types.ModuleType("onelogin")

if "onelogin.saml2" not in sys.modules:
    sys.modules["onelogin.saml2"] = types.ModuleType("onelogin.saml2")

if "onelogin.saml2.auth" not in sys.modules:
    saml_auth_module = types.ModuleType("onelogin.saml2.auth")
    saml_auth_module.OneLogin_Saml2_Auth = MagicMock
    sys.modules["onelogin.saml2.auth"] = saml_auth_module

if "onelogin.saml2.idp_metadata_parser" not in sys.modules:
    parser_module = types.ModuleType("onelogin.saml2.idp_metadata_parser")
    parser_module.OneLogin_Saml2_IdPMetadataParser = MagicMock()
    sys.modules["onelogin.saml2.idp_metadata_parser"] = parser_module

if "onelogin.saml2.settings" not in sys.modules:
    sys.modules["onelogin.saml2.settings"] = types.ModuleType("onelogin.saml2.settings")

if "core" not in sys.modules:
    core_module = types.ModuleType("core")
    core_module.__path__ = [str(CORE)]
    sys.modules["core"] = core_module


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


saml_module = load_module("core.authenticators.saml", CORE / "authenticators" / "saml.py")
CustomSAMLAuthenticator = saml_module.CustomSAMLAuthenticator
SAML_REQUEST_ID_COOKIE = saml_module.SAML_REQUEST_ID_COOKIE
_prepare_tornado_request = saml_module._prepare_tornado_request


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class DummyRequest:
    def __init__(
        self,
        host="hub.example.com",
        protocol="https",
        path="/hub/login",
        headers=None,
        arguments=None,
        body_arguments=None,
    ):
        self.host = host
        self.protocol = protocol
        self.path = path
        self.headers = headers or {}
        self.arguments = arguments or {}
        self.body_arguments = body_arguments or {}


class DummyHub:
    def __init__(self, base_url="/hub/"):
        self.base_url = base_url


class DummyHandler:
    def __init__(self, request=None, hub=None):
        self.request = request or DummyRequest()
        self.hub = hub or DummyHub()

    def get_argument(self, name, default=None):
        values = self.request.arguments.get(name)
        if values:
            return values[0] if isinstance(values, list) else values
        return default


def _make_auth(**overrides):
    auth = CustomSAMLAuthenticator()
    for key, value in overrides.items():
        setattr(auth, key, value)
    return auth


# ---------------------------------------------------------------------------
# Tests: _prepare_tornado_request
# ---------------------------------------------------------------------------


def test_prepare_tornado_request_basic():
    handler = DummyHandler()
    result = _prepare_tornado_request(handler)

    assert result["https"] == "on"
    assert result["http_host"] == "hub.example.com"
    assert result["script_name"] == "/hub/login"
    assert result["path_info"] == ""
    assert result["get_data"] == {}
    assert result["post_data"] == {}


def test_prepare_tornado_request_with_forwarded_headers():
    request = DummyRequest(
        host="internal:8081",
        protocol="http",
        headers={"X-Forwarded-Host": "public.example.com", "X-Forwarded-Proto": "https"},
    )
    handler = DummyHandler(request=request)
    result = _prepare_tornado_request(handler)

    assert result["https"] == "on"
    assert result["http_host"] == "public.example.com"


def test_prepare_tornado_request_http_protocol():
    request = DummyRequest(protocol="http")
    handler = DummyHandler(request=request)
    result = _prepare_tornado_request(handler)

    assert result["https"] == "off"


def test_prepare_tornado_request_post_data():
    request = DummyRequest(
        body_arguments={"SAMLResponse": [b"base64data"], "RelayState": [b"/hub/home"]},
    )
    handler = DummyHandler(request=request)
    result = _prepare_tornado_request(handler)

    assert result["post_data"]["SAMLResponse"] == "base64data"
    assert result["post_data"]["RelayState"] == "/hub/home"


# ---------------------------------------------------------------------------
# Tests: authenticate
# ---------------------------------------------------------------------------


def test_authenticate_returns_none_when_no_data():
    auth = _make_auth()
    result = asyncio.run(auth.authenticate(None, data=None))
    assert result is None


def test_authenticate_returns_none_for_empty_username():
    auth = _make_auth()
    result = asyncio.run(auth.authenticate(None, data={"username": "  "}))
    assert result is None


def test_authenticate_rejects_colon_in_username():
    auth = _make_auth()
    result = asyncio.run(auth.authenticate(None, data={"username": "saml:injected"}))
    assert result is None


def test_authenticate_normalizes_username():
    auth = _make_auth()
    result = asyncio.run(
        auth.authenticate(
            None,
            data={
                "username": "  Alice@Example.COM  ",
                "saml_attributes": {"email": ["alice@example.com"]},
                "session_index": "idx-123",
            },
        )
    )

    assert result is not None
    assert result["name"] == "saml:alice@example.com"
    assert result["auth_state"]["saml_attributes"] == {"email": ["alice@example.com"]}
    assert result["auth_state"]["session_index"] == "idx-123"


def test_authenticate_passes_valid_username():
    auth = _make_auth()
    result = asyncio.run(auth.authenticate(None, data={"username": "bob"}))

    assert result is not None
    assert result["name"] == "saml:bob"


def test_authenticate_prefixes_username():
    auth = _make_auth()
    result = asyncio.run(auth.authenticate(None, data={"username": "carol@example.com"}))

    assert result is not None
    assert result["name"].startswith(saml_module.SAML_USERNAME_PREFIX)


# ---------------------------------------------------------------------------
# Tests: _build_saml_settings
# ---------------------------------------------------------------------------


def test_build_saml_settings_auto_derives_sp_urls():
    auth = _make_auth(
        idp_entity_id="https://idp.example.com/entity",
        idp_sso_url="https://idp.example.com/sso",
        idp_x509_cert="CERTDATA",
    )
    request = DummyRequest(path="/hub/login")
    handler = DummyHandler(request=request)

    settings = auth._build_saml_settings(handler)

    assert settings["sp"]["entityId"] == "https://hub.example.com/hub/metadata"
    assert settings["sp"]["assertionConsumerService"]["url"] == "https://hub.example.com/hub/acs"
    assert settings["idp"]["entityId"] == "https://idp.example.com/entity"
    assert settings["idp"]["singleSignOnService"]["url"] == "https://idp.example.com/sso"


def test_build_saml_settings_uses_explicit_sp_urls():
    auth = _make_auth(
        idp_entity_id="https://idp.example.com/entity",
        idp_sso_url="https://idp.example.com/sso",
        sp_entity_id="https://custom.example.com/sp",
        sp_acs_url="https://custom.example.com/acs",
    )
    handler = DummyHandler()

    settings = auth._build_saml_settings(handler)

    assert settings["sp"]["entityId"] == "https://custom.example.com/sp"
    assert settings["sp"]["assertionConsumerService"]["url"] == "https://custom.example.com/acs"


def test_build_saml_settings_multi_auth_prefix():
    auth = _make_auth(
        idp_entity_id="https://idp.example.com/entity",
        idp_sso_url="https://idp.example.com/sso",
    )
    request = DummyRequest(path="/hub/saml/login")
    handler = DummyHandler(request=request)

    settings = auth._build_saml_settings(handler)

    assert settings["sp"]["entityId"] == "https://hub.example.com/hub/saml/metadata"
    assert settings["sp"]["assertionConsumerService"]["url"] == "https://hub.example.com/hub/saml/acs"


def test_build_saml_settings_never_advertises_single_logout():
    """SLO is not implemented, so settings must not claim the endpoint.

    There is no /slo handler and process_slo() is never called; carrying a
    SingleLogoutService entry would describe a flow this SP cannot complete.
    """
    auth = _make_auth(
        idp_entity_id="https://idp.example.com/entity",
        idp_sso_url="https://idp.example.com/sso",
    )
    handler = DummyHandler()

    settings = auth._build_saml_settings(handler)

    assert "singleLogoutService" not in settings["idp"]
    assert not hasattr(auth, "idp_slo_url")


def test_slo_endpoint_from_idp_metadata_is_dropped(monkeypatch):
    """Published IdP metadata commonly includes SLO; it must not survive the merge."""
    saml_module._idp_metadata_cache.clear()
    monkeypatch.setattr(
        saml_module.OneLogin_Saml2_IdPMetadataParser,
        "parse_remote",
        lambda _url: {
            "idp": {
                "entityId": "https://idp.example.com/entity",
                "singleSignOnService": {"url": "https://idp.example.com/sso"},
                "singleLogoutService": {"url": "https://idp.example.com/slo"},
            }
        },
    )
    auth = _make_auth(idp_metadata_url="https://idp.example.com/metadata")

    settings = auth._build_saml_settings(DummyHandler())

    assert settings["idp"]["entityId"] == "https://idp.example.com/entity"
    assert "singleLogoutService" not in settings["idp"]
    saml_module._idp_metadata_cache.clear()


def test_build_saml_settings_signed_requests():
    auth = _make_auth(
        idp_entity_id="https://idp.example.com/entity",
        idp_sso_url="https://idp.example.com/sso",
        sp_private_key="PRIVATE_KEY_DATA",
    )
    handler = DummyHandler()

    settings = auth._build_saml_settings(handler)

    assert settings["security"]["authnRequestsSigned"] is True
    assert settings["security"]["signMetadata"] is True


def test_build_saml_settings_unsigned_requests():
    auth = _make_auth(
        idp_entity_id="https://idp.example.com/entity",
        idp_sso_url="https://idp.example.com/sso",
    )
    handler = DummyHandler()

    settings = auth._build_saml_settings(handler)

    assert settings["security"]["authnRequestsSigned"] is False
    assert settings["security"]["signMetadata"] is False


def test_build_saml_settings_fail_closed_when_no_signing():
    auth = _make_auth(
        idp_entity_id="https://idp.example.com/entity",
        idp_sso_url="https://idp.example.com/sso",
        want_assertions_signed=False,
        want_response_signed=False,
    )
    handler = DummyHandler()

    settings = auth._build_saml_settings(handler)

    assert settings["security"]["wantAssertionsSigned"] is True


def test_build_saml_settings_security_defaults():
    auth = _make_auth(
        idp_entity_id="https://idp.example.com/entity",
        idp_sso_url="https://idp.example.com/sso",
    )
    handler = DummyHandler()

    settings = auth._build_saml_settings(handler)

    assert settings["security"]["wantAssertionsSigned"] is True
    assert settings["security"]["wantMessagesSigned"] is False
    assert settings["security"]["nameIdEncrypted"] is False


# ---------------------------------------------------------------------------
# Tests: get_handlers
# ---------------------------------------------------------------------------


def test_get_handlers_scopes_routes_under_saml_when_standalone():
    """Standalone SAML must not shadow JupyterHub's own /hub/login page.

    Regression: unscoped routes registered ahead of JupyterHub's defaults, so
    /hub/login redirected straight to the IdP and the login template never
    rendered (no SSO card, announcements or login errors).
    """
    auth = _make_auth()
    handlers = auth.get_handlers(None)

    routes = [h[0] for h in handlers]
    assert routes == ["/saml/login", "/saml/acs", "/saml/metadata"]


def test_get_handlers_stays_unscoped_when_wrapped_by_multiauthenticator():
    """MultiAuthenticator adds the /saml prefix itself; adding it here too
    would produce /saml/saml/login."""

    class WrappedSAMLAuthenticator(CustomSAMLAuthenticator):
        pass

    routes = [h[0] for h in WrappedSAMLAuthenticator().get_handlers(None)]
    assert routes == ["/login", "/acs", "/metadata"]


# ---------------------------------------------------------------------------
# Tests: login_url
# ---------------------------------------------------------------------------


def test_login_url_points_at_the_scoped_route_when_standalone():
    assert _make_auth().login_url("/hub") == "/hub/saml/login"


def test_login_url_stays_unscoped_when_wrapped_by_multiauthenticator():
    class WrappedSAMLAuthenticator(CustomSAMLAuthenticator):
        pass

    assert WrappedSAMLAuthenticator().login_url("/hub") == "/hub/login"


# ---------------------------------------------------------------------------
# Tests: IdP metadata URL caching
# ---------------------------------------------------------------------------


def test_build_saml_settings_fetches_idp_metadata_once(monkeypatch):
    saml_module._idp_metadata_cache.clear()

    call_count = 0

    def mock_parse_remote(url):
        nonlocal call_count
        call_count += 1
        return {"idp": {"entityId": "https://fetched.example.com"}}

    monkeypatch.setattr(
        saml_module.OneLogin_Saml2_IdPMetadataParser,
        "parse_remote",
        mock_parse_remote,
    )

    auth = _make_auth(
        idp_metadata_url="https://idp.example.com/metadata",
        idp_entity_id="https://original.example.com",
        idp_sso_url="https://idp.example.com/sso",
    )
    handler = DummyHandler()

    settings1 = auth._build_saml_settings(handler)
    settings2 = auth._build_saml_settings(handler)

    assert settings1["idp"]["entityId"] == "https://fetched.example.com"
    assert settings2["idp"]["entityId"] == "https://fetched.example.com"
    assert call_count == 1

    saml_module._idp_metadata_cache.clear()


def test_idp_metadata_refetched_after_ttl(monkeypatch):
    saml_module._idp_metadata_cache.clear()

    call_count = 0

    def mock_parse_remote(url):
        nonlocal call_count
        call_count += 1
        return {"idp": {"entityId": f"https://fetched-{call_count}.example.com"}}

    monkeypatch.setattr(
        saml_module.OneLogin_Saml2_IdPMetadataParser,
        "parse_remote",
        mock_parse_remote,
    )

    fake_clock = [1000.0]
    monkeypatch.setattr(saml_module.time, "monotonic", lambda: fake_clock[0])

    auth = _make_auth(
        idp_metadata_url="https://idp.example.com/metadata",
        idp_metadata_ttl_seconds=300,
    )

    first = auth._get_idp_metadata()
    fake_clock[0] += 301
    second = auth._get_idp_metadata()

    assert call_count == 2
    assert first["idp"]["entityId"] != second["idp"]["entityId"]

    saml_module._idp_metadata_cache.clear()


def test_idp_metadata_falls_back_to_stale_on_refresh_failure(monkeypatch):
    saml_module._idp_metadata_cache.clear()

    state = {"calls": 0}

    def mock_parse_remote(url):
        state["calls"] += 1
        if state["calls"] == 1:
            return {"idp": {"entityId": "https://good.example.com"}}
        raise RuntimeError("IdP unreachable")

    monkeypatch.setattr(
        saml_module.OneLogin_Saml2_IdPMetadataParser,
        "parse_remote",
        mock_parse_remote,
    )

    fake_clock = [1000.0]
    monkeypatch.setattr(saml_module.time, "monotonic", lambda: fake_clock[0])

    auth = _make_auth(
        idp_metadata_url="https://idp.example.com/metadata",
        idp_metadata_ttl_seconds=300,
    )

    auth._get_idp_metadata()
    fake_clock[0] += 301
    result = auth._get_idp_metadata()

    assert state["calls"] == 2
    assert result["idp"]["entityId"] == "https://good.example.com"

    saml_module._idp_metadata_cache.clear()


def test_idp_metadata_cached_per_url(monkeypatch):
    saml_module._idp_metadata_cache.clear()

    def mock_parse_remote(url):
        return {"idp": {"entityId": url}}

    monkeypatch.setattr(
        saml_module.OneLogin_Saml2_IdPMetadataParser,
        "parse_remote",
        mock_parse_remote,
    )

    auth_a = _make_auth(idp_metadata_url="https://a.example.com/metadata")
    auth_b = _make_auth(idp_metadata_url="https://b.example.com/metadata")

    result_a = auth_a._get_idp_metadata()
    result_b = auth_b._get_idp_metadata()

    assert result_a["idp"]["entityId"] == "https://a.example.com/metadata"
    assert result_b["idp"]["entityId"] == "https://b.example.com/metadata"

    saml_module._idp_metadata_cache.clear()


# ---------------------------------------------------------------------------
# Tests: ACS handler authentication flow
#
# These drive SAMLACSHandler.post end-to-end against a stubbed
# OneLogin_Saml2_Auth. The settings-construction tests above never enter this
# path, which is where the authentication contract with JupyterHub lives.
# ---------------------------------------------------------------------------


_UNSET = object()


class FakeSamlAuth:
    """Stand-in for OneLogin_Saml2_Auth with a successful assertion."""

    def __init__(self, nameid="alice@example.com", attributes=None, errors=None):
        self._nameid = nameid
        self._attributes = attributes or {}
        self._errors = errors or []
        self.request_id_received = _UNSET

    def process_response(self, request_id=None):
        # Record what the ACS forwarded: python3-saml only enforces
        # InResponseTo when this is not None.
        self.request_id_received = request_id
        return None

    def get_errors(self):
        return self._errors

    def get_last_error_reason(self):
        return "stubbed failure"

    def is_authenticated(self):
        return not self._errors

    def get_nameid(self):
        return self._nameid

    def get_attributes(self):
        return self._attributes

    def get_session_index(self):
        return "session-index-1"


class RecordingACSHandler:
    """Captures the side effects the ACS handler performs on success."""

    # Default models the normal SP-initiated flow: the browser returns the
    # correlation cookie set at /saml/login. Pass request_id_cookie=None
    # explicitly to simulate an unsolicited response.
    def __init__(self, request=None, hub=None, relay_state="", request_id_cookie="ONELOGIN_req-1"):
        self.request = request or DummyRequest(path="/hub/saml/acs")
        self.hub = hub or DummyHub()
        self.relay_state = relay_state
        self.saved_auth_state = None
        self.logged_in_user = None
        self.redirected_to = None
        self.created_usernames = []
        # Signed cookies the browser would send back, plus what the handler did.
        self.secure_cookies = {} if request_id_cookie is None else {SAML_REQUEST_ID_COOKIE: request_id_cookie}
        self.saml_request_id_seen = None
        self.set_cookies = {}
        self.cleared_cookies = []

    def set_secure_cookie(self, name, value, **kwargs):
        self.set_cookies[name] = {"value": value, **kwargs}

    def get_secure_cookie(self, name, max_age_days=None):
        value = self.secure_cookies.get(name)
        return value.encode() if isinstance(value, str) else value

    def clear_cookie(self, name, **kwargs):
        self.cleared_cookies.append(name)
        self.secure_cookies.pop(name, None)

    def get_argument(self, name, default=None):
        if name == "RelayState":
            return self.relay_state or default
        return default

    def find_user(self, name):
        return None

    def user_from_username(self, name):
        self.created_usernames.append(name)
        return self

    async def save_auth_state(self, auth_state):
        self.saved_auth_state = auth_state

    def set_login_cookie(self, user):
        self.logged_in_user = user

    def redirect(self, url):
        self.redirected_to = url

    def _validate_next_url(self, url):
        # Mirror JupyterHub: reject cross-origin targets.
        return "" if "://" in url else url

    @property
    def name(self):
        return self.created_usernames[-1] if self.created_usernames else None


def _acs_handler_class(authenticator):
    handlers = dict(authenticator.get_handlers(app=None))
    return handlers[f"{authenticator.url_scope}/acs"]


def _status_of(error):
    """Return the HTTP status an HTTPError carries."""
    return error.status_code


def _run_acs(authenticator, handler, fake_auth, monkeypatch):
    monkeypatch.setattr(saml_module, "OneLogin_Saml2_Auth", lambda req, settings: fake_auth)
    acs_class = _acs_handler_class(authenticator)
    # The handler is duck-typed rather than a real BaseHandler subclass, so
    # bind the production helper that post() relies on instead of stubbing it.
    handler._consume_request_id = acs_class._consume_request_id.__get__(handler, type(handler))
    result = asyncio.run(acs_class.post(handler))
    handler.saml_request_id_seen = fake_auth.request_id_received
    return result


def test_acs_authenticates_and_logs_in_user(monkeypatch):
    """The success path must complete without raising and set a login cookie.

    Regression: the handler previously called check_blocked_user (singular),
    which does not exist on jupyterhub.auth.Authenticator, so every successful
    assertion raised AttributeError -> HTTP 500.
    """
    auth = _make_auth(idp_entity_id="idp", idp_sso_url="https://idp/sso", idp_x509_cert="cert")
    auth.allow_all = True
    handler = RecordingACSHandler()

    _run_acs(auth, handler, FakeSamlAuth(), monkeypatch)

    assert handler.created_usernames == ["saml:alice@example.com"]
    assert handler.logged_in_user is handler
    assert handler.redirected_to == "/hub/home"


def test_acs_persists_auth_state_with_saml_attributes(monkeypatch):
    auth = _make_auth(idp_entity_id="idp", idp_sso_url="https://idp/sso", idp_x509_cert="cert")
    auth.allow_all = True
    handler = RecordingACSHandler()
    attributes = {"groups": ["staff", "research"]}

    _run_acs(auth, handler, FakeSamlAuth(attributes=attributes), monkeypatch)

    assert handler.saved_auth_state == {
        "saml_attributes": attributes,
        "session_index": "session-index-1",
    }


def test_acs_rejects_blocked_user(monkeypatch):
    """check_blocked_users is synchronous on the base class; it must still be honoured."""
    auth = _make_auth(idp_entity_id="idp", idp_sso_url="https://idp/sso", idp_x509_cert="cert")
    auth.allow_all = True
    auth.blocked_users = {"saml:alice@example.com"}
    handler = RecordingACSHandler()

    try:
        _run_acs(auth, handler, FakeSamlAuth(), monkeypatch)
    except saml_module.web.HTTPError as error:
        assert _status_of(error) == 403
    else:
        raise AssertionError("blocked user was not rejected")

    assert handler.logged_in_user is None


def test_acs_rejects_user_not_allowed(monkeypatch):
    """With allow_all off and no allow rules, the assertion must not grant access."""
    auth = _make_auth(idp_entity_id="idp", idp_sso_url="https://idp/sso", idp_x509_cert="cert")
    auth.allow_all = False
    handler = RecordingACSHandler()

    try:
        _run_acs(auth, handler, FakeSamlAuth(), monkeypatch)
    except saml_module.web.HTTPError as error:
        assert _status_of(error) == 403
    else:
        raise AssertionError("disallowed user was not rejected")

    assert handler.logged_in_user is None


def test_acs_rejects_failed_assertion(monkeypatch):
    auth = _make_auth(idp_entity_id="idp", idp_sso_url="https://idp/sso", idp_x509_cert="cert")
    auth.allow_all = True
    handler = RecordingACSHandler()

    try:
        _run_acs(auth, handler, FakeSamlAuth(errors=["invalid_response"]), monkeypatch)
    except saml_module.web.HTTPError as error:
        assert _status_of(error) == 401
    else:
        raise AssertionError("invalid assertion was accepted")

    assert handler.logged_in_user is None


def test_acs_rejects_username_containing_prefix_separator(monkeypatch):
    """A NameID with ':' could forge another provider's identity."""
    auth = _make_auth(idp_entity_id="idp", idp_sso_url="https://idp/sso", idp_x509_cert="cert")
    auth.allow_all = True
    handler = RecordingACSHandler()

    try:
        _run_acs(auth, handler, FakeSamlAuth(nameid="github:victim"), monkeypatch)
    except saml_module.web.HTTPError as error:
        assert _status_of(error) == 401
    else:
        raise AssertionError("username containing ':' was accepted")

    assert handler.logged_in_user is None


def test_acs_uses_username_attribute_when_configured(monkeypatch):
    auth = _make_auth(
        idp_entity_id="idp",
        idp_sso_url="https://idp/sso",
        idp_x509_cert="cert",
        username_attribute="uid",
    )
    auth.allow_all = True
    handler = RecordingACSHandler()

    _run_acs(auth, handler, FakeSamlAuth(attributes={"uid": ["bob@example.com"]}), monkeypatch)

    assert handler.created_usernames == ["saml:bob@example.com"]


def test_acs_honours_valid_relay_state(monkeypatch):
    auth = _make_auth(idp_entity_id="idp", idp_sso_url="https://idp/sso", idp_x509_cert="cert")
    auth.allow_all = True
    handler = RecordingACSHandler(relay_state="/hub/user/alice/lab")

    _run_acs(auth, handler, FakeSamlAuth(), monkeypatch)

    assert handler.redirected_to == "/hub/user/alice/lab"


def test_acs_rejects_cross_origin_relay_state(monkeypatch):
    """RelayState is attacker-controllable and must not redirect off-site."""
    auth = _make_auth(idp_entity_id="idp", idp_sso_url="https://idp/sso", idp_x509_cert="cert")
    auth.allow_all = True
    handler = RecordingACSHandler(relay_state="https://evil.example.com/steal")

    _run_acs(auth, handler, FakeSamlAuth(), monkeypatch)

    assert handler.redirected_to == "/hub/home"


def test_saml_prefix_literals_match_the_authenticator_constant():
    """Modules that cannot import saml.py duplicate its prefix as a literal.

    core.groups and core.handlers load in every deployment, including
    native-only installs that do not ship onelogin/xmlsec, so they spell the
    prefix out. This guards the duplication against drift.
    """
    prefix = saml_module.SAML_USERNAME_PREFIX
    groups_source = (CORE / "groups.py").read_text(encoding="utf-8")
    handlers_source = (CORE / "handlers.py").read_text(encoding="utf-8")

    assert f'SAML_USERNAME_PREFIX_LITERAL = "{prefix}"' in groups_source
    assert f'_EXTERNAL_USER_PREFIXES = ("github:", "{prefix}")' in handlers_source


# ---------------------------------------------------------------------------
# Tests: metadata endpoint and setup-time diagnostics
# ---------------------------------------------------------------------------


class RecordingMetadataHandler(RecordingACSHandler):
    """Captures what the SP metadata endpoint writes back."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.headers = {}
        self.written = None

    def set_header(self, name, value):
        self.headers[name] = value

    def write(self, chunk):
        self.written = chunk


def _metadata_handler_class(authenticator):
    handlers = dict(authenticator.get_handlers(app=None))
    return handlers[f"{authenticator.url_scope}/metadata"]


def _install_settings_stub(monkeypatch, metadata=b"<EntityDescriptor/>", errors=()):
    class FakeSettings:
        def __init__(self, settings, sp_validation_only=False):
            self.settings = settings

        def get_sp_metadata(self):
            return metadata

        def validate_metadata(self, _metadata):
            return list(errors)

    module = sys.modules["onelogin.saml2.settings"]
    monkeypatch.setattr(module, "OneLogin_Saml2_Settings", FakeSettings, raising=False)


def test_metadata_endpoint_serves_sp_xml(monkeypatch):
    """Operators configure their IdP from this endpoint; it must serve XML."""
    auth = _make_auth(idp_entity_id="idp", idp_sso_url="https://idp/sso", idp_x509_cert="cert")
    handler = RecordingMetadataHandler(request=DummyRequest(path="/hub/saml/metadata"))
    _install_settings_stub(monkeypatch)

    asyncio.run(_metadata_handler_class(auth).get(handler))

    assert handler.headers["Content-Type"] == "application/xml"
    assert handler.written == b"<EntityDescriptor/>"


def test_metadata_endpoint_rejects_invalid_sp_metadata(monkeypatch):
    auth = _make_auth(idp_entity_id="idp", idp_sso_url="https://idp/sso", idp_x509_cert="cert")
    handler = RecordingMetadataHandler(request=DummyRequest(path="/hub/saml/metadata"))
    _install_settings_stub(monkeypatch, errors=["sp_entityId_not_found"])

    try:
        asyncio.run(_metadata_handler_class(auth).get(handler))
    except saml_module.web.HTTPError as error:
        assert _status_of(error) == 500
    else:
        raise AssertionError("invalid SP metadata was served")

    assert handler.written is None


def test_missing_username_attribute_is_reported_with_the_available_attributes(monkeypatch, caplog):
    """A misconfigured username_attribute must be distinguishable from a failed login."""
    auth = _make_auth(
        idp_entity_id="idp",
        idp_sso_url="https://idp/sso",
        idp_x509_cert="cert",
        username_attribute="uid",
    )
    auth.allow_all = True
    handler = RecordingACSHandler()
    fake = FakeSamlAuth(attributes={"emailAddress": ["alice@example.com"]})

    with caplog.at_level("ERROR", logger="jupyterhub.auth.saml"), suppress(saml_module.web.HTTPError):
        _run_acs(auth, handler, fake, monkeypatch)

    assert "no usable value for username_attribute" in caplog.text
    assert "emailAddress" in caplog.text
    assert handler.logged_in_user is None


def test_missing_nameid_points_the_operator_at_username_attribute(monkeypatch, caplog):
    auth = _make_auth(idp_entity_id="idp", idp_sso_url="https://idp/sso", idp_x509_cert="cert")
    auth.allow_all = True
    handler = RecordingACSHandler()

    with caplog.at_level("ERROR", logger="jupyterhub.auth.saml"), suppress(saml_module.web.HTTPError):
        _run_acs(auth, handler, FakeSamlAuth(nameid=""), monkeypatch)

    assert "contains no NameID" in caplog.text
    assert handler.logged_in_user is None


def test_first_idp_metadata_fetch_failure_is_explained_before_raising(monkeypatch, caplog):
    """No cached copy means fail closed, but the cause must not be silent."""
    saml_module._idp_metadata_cache.clear()

    def explode(_url):
        raise OSError("connection refused")

    monkeypatch.setattr(saml_module.OneLogin_Saml2_IdPMetadataParser, "parse_remote", explode)
    auth = _make_auth(idp_metadata_url="https://idp.example.com/metadata")

    with caplog.at_level("ERROR", logger="jupyterhub.auth.saml"):
        try:
            auth._get_idp_metadata()
        except OSError:
            pass
        else:
            raise AssertionError("missing metadata must fail closed")

    assert "no cached copy exists" in caplog.text
    assert "idp_metadata_url" in caplog.text
    saml_module._idp_metadata_cache.clear()


# ---------------------------------------------------------------------------
# Tests: InResponseTo correlation (unsolicited response rejection)
# ---------------------------------------------------------------------------


class RecordingLoginHandler(RecordingACSHandler):
    """Captures the redirect and correlation cookie set by /saml/login."""

    def __init__(self, next_url="", **kwargs):
        super().__init__(request=DummyRequest(path="/hub/saml/login"), **kwargs)
        self.next_url = next_url

    def get_argument(self, name, default=None):
        if name == "next":
            return self.next_url or default
        return default


class FakeLoginAuth(FakeSamlAuth):
    def __init__(self, request_id="ONELOGIN_abc123", **kwargs):
        super().__init__(**kwargs)
        self._request_id = request_id
        self.return_to = _UNSET

    def login(self, return_to=None):
        self.return_to = return_to
        return "https://idp.example.com/sso?SAMLRequest=..."

    def get_last_request_id(self):
        return self._request_id


def _run_login(authenticator, handler, fake_auth, monkeypatch):
    monkeypatch.setattr(saml_module, "OneLogin_Saml2_Auth", lambda req, settings: fake_auth)
    handlers = dict(authenticator.get_handlers(app=None))
    login_class = handlers[f"{authenticator.url_scope}/login"]
    return asyncio.run(login_class.get(handler))


def _saml_auth():
    auth = _make_auth(idp_entity_id="idp", idp_sso_url="https://idp/sso", idp_x509_cert="cert")
    auth.allow_all = True
    return auth


def test_login_stores_the_request_id_in_a_cross_site_capable_cookie(monkeypatch):
    """The IdP posts to the ACS cross-site, so the cookie needs SameSite=None.

    Browsers only honour SameSite=None together with Secure, which is why the
    Secure flag is unconditional rather than tied to the deployment scheme.
    """
    auth = _saml_auth()
    handler = RecordingLoginHandler()

    _run_login(auth, handler, FakeLoginAuth(), monkeypatch)

    cookie = handler.set_cookies[SAML_REQUEST_ID_COOKIE]
    assert cookie["value"] == "ONELOGIN_abc123"
    assert cookie["samesite"] == "None"
    assert cookie["secure"] is True
    assert cookie["httponly"] is True
    # Must be absolute: browsers ignore a relative cookie Path (RFC 6265 5.2.4).
    assert cookie["path"] == "/hub/saml"
    assert handler.redirected_to.startswith("https://idp.example.com/sso")


def test_acs_forwards_the_stored_request_id_so_inresponseto_is_enforced(monkeypatch):
    """Regression: process_response() was called with no request_id, which
    disables python3-saml's InResponseTo check entirely."""
    auth = _saml_auth()
    handler = RecordingACSHandler(request_id_cookie="ONELOGIN_abc123")

    _run_acs(auth, handler, FakeSamlAuth(), monkeypatch)

    assert handler.saml_request_id_seen == "ONELOGIN_abc123"
    assert handler.logged_in_user is handler


def test_acs_consumes_the_request_id_cookie_so_it_cannot_be_replayed(monkeypatch):
    auth = _saml_auth()
    handler = RecordingACSHandler(request_id_cookie="ONELOGIN_abc123")

    _run_acs(auth, handler, FakeSamlAuth(), monkeypatch)

    assert SAML_REQUEST_ID_COOKIE in handler.cleared_cookies
    assert SAML_REQUEST_ID_COOKIE not in handler.secure_cookies


def test_acs_rejects_an_unsolicited_response_by_default(monkeypatch, caplog):
    """No correlation cookie means the assertion answers no request we made."""
    auth = _saml_auth()
    handler = RecordingACSHandler(request_id_cookie=None)

    with caplog.at_level("ERROR", logger="jupyterhub.auth.saml"):
        try:
            _run_acs(auth, handler, FakeSamlAuth(), monkeypatch)
        except saml_module.web.HTTPError as error:
            assert _status_of(error) == 403
        else:
            raise AssertionError("unsolicited SAML response was accepted")

    assert handler.logged_in_user is None
    assert "unsolicited" in caplog.text.lower()
    assert "reject_unsolicited_responses=False" in caplog.text


def test_acs_allows_idp_initiated_login_when_the_operator_opts_in(monkeypatch):
    """Opting out must still work, for Okta-dashboard-tile style launches."""
    auth = _saml_auth()
    auth.reject_unsolicited_responses = False
    handler = RecordingACSHandler(request_id_cookie=None)

    _run_acs(auth, handler, FakeSamlAuth(), monkeypatch)

    assert handler.logged_in_user is handler
    # No request id to correlate against, so InResponseTo cannot be enforced.
    assert handler.saml_request_id_seen is None


def test_expired_correlation_cookie_is_treated_as_unsolicited(monkeypatch):
    """A user who idles at the IdP past the TTL gets a clean rejection."""
    auth = _saml_auth()
    handler = RecordingACSHandler(request_id_cookie=None)

    try:
        _run_acs(auth, handler, FakeSamlAuth(), monkeypatch)
    except saml_module.web.HTTPError as error:
        assert _status_of(error) == 403
    else:
        raise AssertionError("expired correlation must not authenticate")


def test_request_id_cookie_lifetime_is_derived_from_the_configured_ttl(monkeypatch):
    auth = _saml_auth()
    auth.request_id_cookie_max_age_seconds = 300
    handler = RecordingLoginHandler()

    _run_login(auth, handler, FakeLoginAuth(), monkeypatch)

    assert handler.set_cookies[SAML_REQUEST_ID_COOKIE]["expires_days"] == 300 / 86400
