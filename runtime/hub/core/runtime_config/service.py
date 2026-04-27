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

"""Source-aware runtime access overlay service."""

from __future__ import annotations

import json

from pydantic import BaseModel

from core.config import HubConfig
from core.runtime_config.registry import group_lifecycle_key, key_domain, key_subject, resource_access_key
from core.runtime_config.schemas import GroupLifecyclePolicy, ResourceAccessPolicy


def _load_json(value: str) -> dict:
    return json.loads(value or "{}")


def _validate_value(key: str, value: dict) -> BaseModel:
    domain = key_domain(key)
    subject = key_subject(key)
    config = HubConfig.get()
    if domain == "resource_access" and subject not in config.resources.images:
        raise ValueError(f"Unknown resource '{subject}'")
    if domain == "group_lifecycle":
        return GroupLifecyclePolicy.model_validate(value)
    return ResourceAccessPolicy.model_validate(value)


def set_runtime_override(
    key: str,
    value: dict,
    *,
    actor: str | None,
    reason: str = "",
    enabled: bool = True,
    expected_revision: int | None = None,
) -> dict:
    """Create or update a source-aware runtime overlay."""
    domain = key_domain(key)
    model = _validate_value(key, value)
    new_value = model.model_dump(exclude_none=True)

    from core.database import session_scope
    from core.runtime_config.models import RuntimeConfigOverride

    with session_scope() as session:
        existing = session.query(RuntimeConfigOverride).filter(RuntimeConfigOverride.key == key).first()
        if existing and expected_revision is not None and existing.revision != expected_revision:
            raise ValueError(f"Revision mismatch: current={existing.revision}, expected={expected_revision}")
        if existing:
            existing.value_json = json.dumps(new_value, sort_keys=True)
            existing.enabled = enabled
            existing.revision += 1
            existing.updated_by = actor
            existing.reason = reason
            row = existing
        else:
            row = RuntimeConfigOverride(
                key=key,
                domain=domain,
                value_json=json.dumps(new_value, sort_keys=True),
                enabled=enabled,
                revision=1,
                updated_by=actor,
                reason=reason,
            )
            session.add(row)
        session.flush()
        return _override_to_dict(row)


def clear_runtime_override(key: str, *, actor: str | None = None, reason: str = "") -> None:
    _ = actor, reason
    key_domain(key)
    from core.database import session_scope
    from core.runtime_config.models import RuntimeConfigOverride

    with session_scope() as session:
        existing = session.query(RuntimeConfigOverride).filter(RuntimeConfigOverride.key == key).first()
        if existing:
            session.delete(existing)


def get_runtime_overrides() -> list[dict]:
    from core.database import get_session
    from core.runtime_config.models import RuntimeConfigOverride

    session = get_session()
    try:
        rows = session.query(RuntimeConfigOverride).order_by(RuntimeConfigOverride.key).all()
        return [_override_to_dict(row) for row in rows]
    finally:
        session.close()


def _override_to_dict(row) -> dict:
    return {
        "key": row.key,
        "domain": row.domain,
        "value": _load_json(row.value_json),
        "enabled": row.enabled,
        "revision": row.revision,
        "updatedBy": row.updated_by,
        "reason": row.reason,
        "source": "database",
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


def _get_enabled_override(key: str) -> dict | None:
    from core.database import get_session
    from core.runtime_config.models import RuntimeConfigOverride

    try:
        session = get_session()
    except RuntimeError:
        return None
    try:
        row = session.query(RuntimeConfigOverride).filter(RuntimeConfigOverride.key == key).first()
        if not row or not row.enabled:
            return None
        return _load_json(row.value_json)
    finally:
        session.close()


def get_group_lifecycle_policy(group_name: str) -> GroupLifecyclePolicy:
    value = _get_enabled_override(group_lifecycle_key(group_name))
    return GroupLifecyclePolicy.model_validate(value or {})


def get_resource_access_policy(resource_key: str) -> ResourceAccessPolicy:
    value = _get_enabled_override(resource_access_key(resource_key))
    return ResourceAccessPolicy.model_validate(value or {})


def get_spawn_block_reason_for_user(user) -> str | None:
    assert user.orm_user is not None
    for group in user.orm_user.groups:
        reason = get_group_lifecycle_policy(group.name).block_reason()
        if reason:
            return reason
    return None


def get_effective_resources_for_group(group_name: str, team_resource_mapping: dict[str, list[str]]) -> list[str]:
    if get_group_lifecycle_policy(group_name).block_reason():
        return []
    available = list(team_resource_mapping.get(group_name, []))
    for resource_key in HubConfig.get().resources.images:
        policy = get_resource_access_policy(resource_key)
        if group_name in policy.denyGroups and resource_key in available:
            available.remove(resource_key)
        if group_name in policy.addGroups and resource_key not in available:
            available.append(resource_key)
    return list(dict.fromkeys(available))


def get_effective_resources_for_user(user, team_resource_mapping: dict[str, list[str]]) -> list[str]:
    if get_spawn_block_reason_for_user(user):
        return []
    assert user.orm_user is not None
    available: list[str] = []
    for group in user.orm_user.groups:
        available.extend(get_effective_resources_for_group(group.name, team_resource_mapping))
    return list(dict.fromkeys(available))
