# Copyright (C) 2025 Advanced Micro Devices, Inc. All rights reserved.

import asyncio
import copy
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"

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


class DummyMetric:
    def labels(self, **_kwargs):
        return self

    def inc(self):
        pass

    def observe(self, _value):
        pass


class TestKubeSpawner:
    def get_pod_manifest(self):
        manifest = {"spec": copy.deepcopy(self.extra_pod_config or {})}
        security_context = manifest["spec"].setdefault("securityContext", {})
        if self.fs_gid is not None:
            security_context["fsGroup"] = self.fs_gid
        if self.supplemental_gids:
            security_context["supplementalGroups"] = list(self.supplemental_gids)
        return manifest


def load_spawner_module():
    metrics_module = types.ModuleType("core.metrics")
    for metric_name in (
        "pod_failure_total",
        "repo_clone_failed_total",
        "session_runtime_minutes",
        "spawn_duration_seconds",
        "spawn_failed_total",
        "spawn_gpu_total",
    ):
        setattr(metrics_module, metric_name, DummyMetric())

    jupyterhub_module = types.ModuleType("jupyterhub")
    jupyterhub_module.__path__ = []
    user_module = types.ModuleType("jupyterhub.user")
    user_module.User = type("User", (), {})
    kubespawner_module = types.ModuleType("kubespawner")
    kubespawner_module.KubeSpawner = TestKubeSpawner
    tornado_module = types.ModuleType("tornado")
    web_module = types.ModuleType("tornado.web")
    web_module.HTTPError = type("HTTPError", (Exception,), {})

    with patch.dict(
        sys.modules,
        {
            "core.metrics": metrics_module,
            "jupyterhub": jupyterhub_module,
            "jupyterhub.user": user_module,
            "kubespawner": kubespawner_module,
            "tornado": tornado_module,
            "tornado.web": web_module,
        },
    ):
        return load_module("gpu_access_test_spawner", CORE / "spawner" / "kubernetes.py")


kubernetes = load_spawner_module()
RemoteLabKubeSpawner = kubernetes.RemoteLabKubeSpawner


class DummyLog:
    def debug(self, _message):
        pass


class ResourceMetadata:
    acceleratorKeys = ["gpu-a"]
    acceleratorOverrides = None
    allowGitClone = False
    defaultPath = None
    env = {}
    launchMode = None


class HubConfig:
    def get_resource_metadata(self, _resource_type):
        return ResourceMetadata()


def make_spawner(supplemental_gids: list[int] | None = None):
    spawner = object.__new__(RemoteLabKubeSpawner)
    spawner._hub_config = HubConfig()
    spawner.resource_images = {"cpu": "cpu-image", "gpu": "gpu-image"}
    spawner.resource_requirements = {
        "cpu": {"cpu": "1", "memory": "1Gi"},
        "gpu": {"cpu": "1", "memory": "1Gi", "amd.com/gpu": "1"},
    }
    spawner.accelerator_options = {"gpu-a": {}}
    spawner.node_selector_mapping = {}
    spawner.environment_mapping = {}
    spawner.cmd = []
    spawner.args = []
    spawner.default_url = ""
    spawner.node_affinity_required = []
    spawner.extra_resource_guarantees = {}
    spawner.extra_resource_limits = {}
    spawner.init_containers = []
    spawner.extra_container_config = {}
    spawner.environment = {}
    spawner.fs_gid = 100
    spawner.supplemental_gids = list(supplemental_gids or [])
    spawner.extra_pod_config = {}
    spawner.log = DummyLog()
    spawner._resolve_user_resources = lambda: ["cpu", "gpu"]
    return spawner


def test_gpu_pod_requests_accelerator_without_changing_generic_supplemental_groups():
    spawner = make_spawner(supplemental_gids=[1234])

    spawner._configure_spawner("gpu", "gpu-a")
    gpu_manifest = spawner.get_pod_manifest()

    assert spawner.extra_resource_guarantees == {"amd.com/gpu": "1"}
    assert spawner.extra_resource_limits == {"amd.com/gpu": "1"}
    assert gpu_manifest["spec"]["securityContext"] == {"fsGroup": 100, "supplementalGroups": [1234]}

    spawner._configure_spawner("cpu")
    cpu_manifest = spawner.get_pod_manifest()

    assert spawner.extra_resource_guarantees == {}
    assert spawner.extra_resource_limits == {}
    assert cpu_manifest["spec"]["securityContext"] == {"fsGroup": 100, "supplementalGroups": [1234]}


def test_gpu_pod_without_generic_supplemental_groups_uses_storage_fs_group_only():
    spawner = make_spawner()

    spawner._configure_spawner("gpu", "gpu-a")

    assert spawner.extra_resource_guarantees == {"amd.com/gpu": "1"}
    assert spawner.extra_resource_limits == {"amd.com/gpu": "1"}
    assert spawner.get_pod_manifest()["spec"]["securityContext"] == {"fsGroup": 100}


def test_unauthorized_gpu_selection_is_rejected_before_spawner_configuration():
    spawner = make_spawner()
    spawner._resolve_user_resources = lambda: ["cpu"]
    spawner._configure_spawner = lambda *_args: pytest.fail("unauthorized resource configured the spawner")

    with pytest.raises(RuntimeError, match="not authorized"):
        spawner.options_from_form({"runtime": ["20"], "resource_type": ["gpu"], "gpu_selection_gpu": ["gpu-a"]})


def test_auto_accelerator_is_a_gpu_sentinel_only_for_multiple_authorized_keys():
    spawner = make_spawner()
    spawner._hub_config = types.SimpleNamespace(
        get_resource_metadata=lambda _resource_type: types.SimpleNamespace(acceleratorKeys=["gpu-a", "gpu-b"])
    )
    spawner.accelerator_options = {"gpu-a": {}, "gpu-b": {}}

    assert spawner._resolve_accelerator_selection("gpu", "auto") == "auto"


@pytest.mark.parametrize("selection", [None, "", "   "])
def test_single_authorized_accelerator_defaults_blank_selection(selection: str | None):
    spawner = make_spawner()

    assert spawner._resolve_accelerator_selection("gpu", selection) == "gpu-a"


@pytest.mark.parametrize(
    ("resource_type", "accelerator_keys", "selection", "error"),
    [
        ("cpu", ["gpu-a", "gpu-b"], "auto", "does not allow GPU selection"),
        ("gpu", ["gpu-a"], "auto", "requires selecting an accelerator"),
    ],
)
def test_auto_accelerator_is_rejected_outside_multiple_authorized_gpu_keys(
    resource_type: str, accelerator_keys: list[str], selection: str, error: str
):
    spawner = make_spawner()
    spawner._hub_config = types.SimpleNamespace(
        get_resource_metadata=lambda _resource_type: types.SimpleNamespace(acceleratorKeys=accelerator_keys)
    )

    with pytest.raises(RuntimeError, match=error):
        spawner._resolve_accelerator_selection(resource_type, selection)


@pytest.mark.parametrize(
    ("accelerator_keys", "accelerator_options", "selection", "error"),
    [
        (["gpu-a"], {"gpu-a": {}}, "gpu-x", "not authorized"),
        (["gpu-a"], {"gpu-a": {}, "gpu-b": {}}, "gpu-b", "not authorized"),
        (["gpu-a", "gpu-b"], {"gpu-a": {}}, "gpu-b", "not configured"),
    ],
)
def test_concrete_accelerator_requires_resource_authorization_and_global_configuration(
    accelerator_keys: list[str], accelerator_options: dict[str, dict[str, str]], selection: str, error: str
):
    spawner = make_spawner()
    spawner._hub_config = types.SimpleNamespace(
        get_resource_metadata=lambda _resource_type: types.SimpleNamespace(acceleratorKeys=accelerator_keys)
    )
    spawner.accelerator_options = accelerator_options

    with pytest.raises(RuntimeError, match=error):
        spawner._resolve_accelerator_selection("gpu", selection)


# ---------------------------------------------------------------------------
# _resolve_auto_accelerator – K8s integration and error-handling tests
# ---------------------------------------------------------------------------


class FakeApiException(Exception):
    def __init__(self, status):
        self.status = status
        super().__init__(f"HTTP {status}")


def _make_k8s_modules(core_v1_mock=None, api_exception_cls=FakeApiException):
    """Build fake kubernetes_asyncio module hierarchy for inline imports."""
    rest_module = types.ModuleType("kubernetes_asyncio.client.rest")
    rest_module.ApiException = api_exception_cls

    client_module = types.ModuleType("kubernetes_asyncio.client")
    client_module.ApiClient = AsyncMock
    client_module.CoreV1Api = lambda _api: core_v1_mock
    client_module.rest = rest_module

    k8s_module = types.ModuleType("kubernetes_asyncio")
    k8s_module.client = client_module

    return {
        "kubernetes_asyncio": k8s_module,
        "kubernetes_asyncio.client": client_module,
        "kubernetes_asyncio.client.rest": rest_module,
    }


def _make_auto_spawner():
    spawner = object.__new__(RemoteLabKubeSpawner)
    spawner.node_selector_mapping = {
        "gpu-a": {"kubernetes.io/hostname": "node-a"},
        "gpu-b": {"kubernetes.io/hostname": "node-b"},
    }
    spawner.quota_rates = {"gpu-a": 10, "gpu-b": 10}
    spawner.log = types.SimpleNamespace(
        debug=lambda _msg: None,
        info=lambda _msg: None,
        warning=lambda _msg: None,
    )
    return spawner


def _fake_node(name, labels, gpu_allocatable=1):
    return types.SimpleNamespace(
        metadata=types.SimpleNamespace(name=name, labels=labels),
        status=types.SimpleNamespace(allocatable={"amd.com/gpu": str(gpu_allocatable)}),
    )


def _fake_pod(node_name, gpu_requests=1):
    container = types.SimpleNamespace(
        resources=types.SimpleNamespace(requests={"amd.com/gpu": str(gpu_requests)})
    )
    return types.SimpleNamespace(
        spec=types.SimpleNamespace(node_name=node_name, containers=[container])
    )


def test_auto_accelerator_raises_on_forbidden():
    v1 = types.SimpleNamespace(
        list_node=AsyncMock(side_effect=FakeApiException(403)),
        list_pod_for_all_namespaces=AsyncMock(),
    )
    mods = _make_k8s_modules(core_v1_mock=v1)
    spawner = _make_auto_spawner()

    with patch.dict(sys.modules, mods):
        with pytest.raises(RuntimeError, match="403"):
            asyncio.get_event_loop().run_until_complete(
                spawner._resolve_auto_accelerator("gpu", ["gpu-a", "gpu-b"])
            )


def test_auto_accelerator_falls_back_on_transient_api_error():
    v1 = types.SimpleNamespace(
        list_node=AsyncMock(side_effect=FakeApiException(503)),
        list_pod_for_all_namespaces=AsyncMock(),
    )
    mods = _make_k8s_modules(core_v1_mock=v1)
    spawner = _make_auto_spawner()

    with patch.dict(sys.modules, mods):
        result = asyncio.get_event_loop().run_until_complete(
            spawner._resolve_auto_accelerator("gpu", ["gpu-a", "gpu-b"])
        )
    assert result in ("gpu-a", "gpu-b")


def test_auto_accelerator_falls_back_on_generic_exception():
    v1 = types.SimpleNamespace(
        list_node=AsyncMock(side_effect=ConnectionError("timeout")),
        list_pod_for_all_namespaces=AsyncMock(),
    )
    mods = _make_k8s_modules(core_v1_mock=v1)
    spawner = _make_auto_spawner()

    with patch.dict(sys.modules, mods):
        result = asyncio.get_event_loop().run_until_complete(
            spawner._resolve_auto_accelerator("gpu", ["gpu-a", "gpu-b"])
        )
    assert result in ("gpu-a", "gpu-b")


def test_auto_accelerator_prefers_node_with_free_gpus():
    nodes = types.SimpleNamespace(items=[
        _fake_node("node-a", {"kubernetes.io/hostname": "node-a"}, gpu_allocatable=1),
        _fake_node("node-b", {"kubernetes.io/hostname": "node-b"}, gpu_allocatable=1),
    ])
    pods = types.SimpleNamespace(items=[
        _fake_pod("node-a", gpu_requests=1),
    ])
    v1 = types.SimpleNamespace(
        list_node=AsyncMock(return_value=nodes),
        list_pod_for_all_namespaces=AsyncMock(return_value=pods),
    )
    mods = _make_k8s_modules(core_v1_mock=v1)
    spawner = _make_auto_spawner()

    with patch.dict(sys.modules, mods):
        result = asyncio.get_event_loop().run_until_complete(
            spawner._resolve_auto_accelerator("gpu", ["gpu-a", "gpu-b"])
        )
    assert result == "gpu-b"
