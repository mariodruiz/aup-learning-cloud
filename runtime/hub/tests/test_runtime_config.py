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

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if "core" not in sys.modules:
    core_module = types.ModuleType("core")
    core_module.__path__ = [str(CORE)]
    sys.modules["core"] = core_module

from core.runtime_config.registry import key_domain, key_subject  # noqa: E402
from core.runtime_config.schemas import GroupLifecyclePolicy, ResourceAccessPolicy, RuntimeResourceWrite  # noqa: E402
from core.runtime_config.service import get_effective_resources_for_group  # noqa: E402


def test_runtime_key_registry_accepts_source_aware_access_keys():
    assert key_domain("groups.team-a.lifecycle") == "group_lifecycle"
    assert key_domain("resources.Course-CV.access") == "resource_access"
    assert key_subject("resources.Course-CV.access") == "Course-CV"


def test_group_lifecycle_policy_blocks_group_resources(monkeypatch):
    import core.runtime_config.service as service

    monkeypatch.setattr(
        service,
        "get_group_lifecycle_policy",
        lambda _group: GroupLifecyclePolicy(spawnSuspended=True),
    )

    result = get_effective_resources_for_group("team-a", {"team-a": ["Course-CV"]})

    assert result == []


def test_group_lifecycle_policy_serializes_datetime_values():
    policy = GroupLifecyclePolicy(startsAt="2026-01-01T00:00:00Z", expiresAt="2026-01-02T00:00:00Z")

    dumped = policy.model_dump(mode="json", exclude_none=True)

    assert dumped == {
        "spawnSuspended": False,
        "startsAt": "2026-01-01T00:00:00Z",
        "expiresAt": "2026-01-02T00:00:00Z",
    }
    json.dumps(dumped)


def test_resource_access_policy_rejects_contradictory_groups():
    with pytest.raises(ValueError, match="both added and denied"):
        ResourceAccessPolicy(addGroups=["team-a"], denyGroups=["team-a"])


def test_resource_access_overlay_adds_and_removes_groups(monkeypatch):
    import core.runtime_config.service as service

    class DummyResources:
        images = {"Course-CV": "image", "Course-DL": "image"}

    class DummyConfig:
        resources = DummyResources()

    policies = {
        "Course-CV": ResourceAccessPolicy(denyGroups=["team-a"]),
        "Course-DL": ResourceAccessPolicy(addGroups=["team-a"]),
    }

    monkeypatch.setattr(service.HubConfig, "get", lambda: DummyConfig())
    monkeypatch.setattr(service, "get_database_resources", lambda: [])
    monkeypatch.setattr(service, "get_group_lifecycle_policy", lambda _group: GroupLifecyclePolicy())
    monkeypatch.setattr(service, "get_resource_access_policy", lambda resource: policies.get(resource, ResourceAccessPolicy()))

    result = get_effective_resources_for_group("team-a", {"team-a": ["Course-CV"]})

    assert result == ["Course-DL"]


def test_database_resource_can_be_added_by_access_overlay(monkeypatch):
    import core.runtime_config.service as service

    class DummyResources:
        images = {"Course-CV": "image"}

    class DummyConfig:
        resources = DummyResources()

    monkeypatch.setattr(service.HubConfig, "get", lambda: DummyConfig())
    monkeypatch.setattr(
        service,
        "get_database_resources",
        lambda: [
            {
                "key": "Database-Course",
                "enabled": True,
            }
        ],
    )
    monkeypatch.setattr(service, "get_group_lifecycle_policy", lambda _group: GroupLifecyclePolicy())
    monkeypatch.setattr(
        service,
        "get_resource_access_policy",
        lambda resource: ResourceAccessPolicy(addGroups=["team-a"]) if resource == "Database-Course" else ResourceAccessPolicy(),
    )

    result = get_effective_resources_for_group("team-a", {"team-a": []})

    assert result == ["Database-Course"]


def test_resource_catalog_marks_helm_and_database_sources(monkeypatch):
    import core.runtime_config.service as service

    class DummyResources:
        images = {"Course-CV": "helm-image"}

    class DummyConfig:
        resources = DummyResources()

        def get_resource_image(self, key):
            return self.resources.images[key]

        def get_resource_metadata(self, _key):
            return None

        def get_resource_requirements(self, _key):
            return None

    monkeypatch.setattr(service.HubConfig, "get", lambda: DummyConfig())
    monkeypatch.setattr(
        service,
        "get_database_resources",
        lambda: [
            {
                "key": "Database-Course",
                "source": "database",
                "image": "db-image",
                "requirements": {"cpu": "1", "memory": "2Gi"},
                "metadata": {"group": "OTHERS"},
                "enabled": True,
                "locked": False,
            }
        ],
    )

    result = service.get_resource_catalog()

    assert result[0]["key"] == "Course-CV"
    assert result[0]["source"] == "helm"
    assert result[0]["locked"] is True
    assert result[1]["key"] == "Database-Course"
    assert result[1]["source"] == "database"
    assert result[1]["locked"] is False


def test_resource_catalog_can_hide_disabled_database_resources(monkeypatch):
    import core.runtime_config.service as service

    class DummyResources:
        images = {}

    class DummyConfig:
        resources = DummyResources()

    monkeypatch.setattr(service.HubConfig, "get", lambda: DummyConfig())
    monkeypatch.setattr(
        service,
        "get_database_resources",
        lambda: [
            {
                "key": "Disabled-Course",
                "source": "database",
                "image": "db-image",
                "requirements": {"cpu": "1", "memory": "2Gi"},
                "metadata": {"group": "OTHERS"},
                "enabled": False,
                "locked": False,
            }
        ],
    )

    assert service.get_resource_catalog(include_disabled=False) == []
    assert service.get_resource_catalog(include_disabled=True)[0]["key"] == "Disabled-Course"


def test_database_resource_validation_rejects_invalid_requirements(monkeypatch):
    import core.runtime_config.service as service

    class DummyConfig:
        accelerators = {}

    monkeypatch.setattr(service.HubConfig, "get", lambda: DummyConfig())

    with pytest.raises(ValueError, match="unknown requirement"):
        service._validate_resource_definition(
            RuntimeResourceWrite(
                key="Database-Course",
                image="example/runtime:1",
                requirements={"cpu": "1", "memory": "2Gi", "example.com/gpu": "1"},
            )
        )

    with pytest.raises(ValueError, match="memory_limit"):
        service._validate_resource_definition(
            RuntimeResourceWrite(
                key="Database-Course",
                image="example/runtime:1",
                requirements={"cpu": "1", "memory": "4Gi", "memory_limit": "2Gi"},
            )
        )
