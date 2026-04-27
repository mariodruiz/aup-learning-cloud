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

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.runtime_config.registry import key_domain, key_subject  # noqa: E402
from core.runtime_config.schemas import GroupLifecyclePolicy, ResourceAccessPolicy  # noqa: E402
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
        lambda _group: GroupLifecyclePolicy(spawnSuspended=True, reason="closed"),
    )

    result = get_effective_resources_for_group("team-a", {"team-a": ["Course-CV"]})

    assert result == []


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
    monkeypatch.setattr(service, "get_group_lifecycle_policy", lambda _group: GroupLifecyclePolicy())
    monkeypatch.setattr(service, "get_resource_access_policy", lambda resource: policies.get(resource, ResourceAccessPolicy()))

    result = get_effective_resources_for_group("team-a", {"team-a": ["Course-CV"]})

    assert result == ["Course-DL"]
