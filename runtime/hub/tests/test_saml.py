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
import sys
import types
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
    auth_module.Authenticator = type("Authenticator", (), {"login_service": ""})
    sys.modules["jupyterhub.auth"] = auth_module

if "jupyterhub.handlers" not in sys.modules:
    handlers_module = types.ModuleType("jupyterhub.handlers")
    handlers_module.BaseHandler = type("BaseHandler", (), {})
    sys.modules["jupyterhub.handlers"] = handlers_module

if "jupyterhub.utils" not in sys.modules:
    utils_module = types.ModuleType("jupyterhub.utils")
    utils_module.url_path_join = lambda *parts: "/".join(p.strip("/") for p in parts if p)
    sys.modules["jupyterhub.utils"] = utils_module

if "tornado" not in sys.modules:
    sys.modules["tornado"] = types.ModuleType("tornado")

if "tornado.web" not in sys.modules:
    web_module = types.ModuleType("tornado.web")
    web_module.HTTPError = type("HTTPError", (Exception,), {"__init__": lambda self, code, msg="": None})
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
_prepare_tornado_request = saml_module._prepare_tornado_request


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class DummyRequest:
    def __init__(self, host="hub.example.com", protocol="https", path="/hub/login",
                 headers=None, arguments=None, body_arguments=None):
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
    result = asyncio.run(auth.authenticate(None, data={
        "username": "  Alice@Example.COM  ",
        "saml_attributes": {"email": ["alice@example.com"]},
        "session_index": "idx-123",
    }))

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


def test_build_saml_settings_slo_url():
    auth = _make_auth(
        idp_entity_id="https://idp.example.com/entity",
        idp_sso_url="https://idp.example.com/sso",
        idp_slo_url="https://idp.example.com/slo",
    )
    handler = DummyHandler()

    settings = auth._build_saml_settings(handler)

    assert "singleLogoutService" in settings["idp"]
    assert settings["idp"]["singleLogoutService"]["url"] == "https://idp.example.com/slo"


def test_build_saml_settings_no_slo_url():
    auth = _make_auth(
        idp_entity_id="https://idp.example.com/entity",
        idp_sso_url="https://idp.example.com/sso",
    )
    handler = DummyHandler()

    settings = auth._build_saml_settings(handler)

    assert "singleLogoutService" not in settings["idp"]


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


def test_get_handlers_returns_three_routes():
    auth = _make_auth()
    handlers = auth.get_handlers(None)

    routes = [h[0] for h in handlers]
    assert r"/login" in routes
    assert r"/acs" in routes
    assert r"/metadata" in routes
    assert len(handlers) == 3


# ---------------------------------------------------------------------------
# Tests: login_url
# ---------------------------------------------------------------------------


def test_login_url():
    auth = _make_auth()
    url = auth.login_url("/hub")
    assert "login" in url


# ---------------------------------------------------------------------------
# Tests: IdP metadata URL caching
# ---------------------------------------------------------------------------


def test_build_saml_settings_fetches_idp_metadata_once(monkeypatch):
    saml_module._cached_idp_metadata = None
    saml_module._cached_idp_metadata_at = 0.0

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

    saml_module._cached_idp_metadata = None
    saml_module._cached_idp_metadata_at = 0.0


def test_idp_metadata_refetched_after_ttl(monkeypatch):
    saml_module._cached_idp_metadata = None
    saml_module._cached_idp_metadata_at = 0.0

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

    saml_module._cached_idp_metadata = None
    saml_module._cached_idp_metadata_at = 0.0


def test_idp_metadata_falls_back_to_stale_on_refresh_failure(monkeypatch):
    saml_module._cached_idp_metadata = None
    saml_module._cached_idp_metadata_at = 0.0

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

    saml_module._cached_idp_metadata = None
    saml_module._cached_idp_metadata_at = 0.0
