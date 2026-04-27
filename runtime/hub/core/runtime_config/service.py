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

"""Source-aware runtime access and database resource catalog service."""

from __future__ import annotations

import json

from pydantic import BaseModel

from core.config import HubConfig
from core.runtime_config.registry import group_lifecycle_key, key_domain, key_subject, resource_access_key
from core.runtime_config.schemas import GroupLifecyclePolicy, ResourceAccessPolicy, RuntimeResourceWrite


def _load_json(value: str) -> dict:
    return json.loads(value or "{}")


def _normalize_metadata(metadata: dict) -> dict:
    return {
        "group": metadata.get("group") or "OTHERS",
        "description": metadata.get("description") or "",
        "subDescription": metadata.get("subDescription") or "",
        "accelerator": metadata.get("accelerator") or "",
        "acceleratorKeys": metadata.get("acceleratorKeys") or [],
        "allowGitClone": bool(metadata.get("allowGitClone", False)),
    }


def _validate_resource_definition(data: RuntimeResourceWrite) -> None:
    safe_key = data.key.replace("-", "").replace("_", "").replace(":", "").replace(".", "")
    if not data.key or not safe_key.isalnum():
        raise ValueError("resource key may only contain letters, numbers, '.', ':', '_' and '-'")
    if not data.image:
        raise ValueError("image is required")
    if "cpu" not in data.requirements or "memory" not in data.requirements:
        raise ValueError("requirements must include cpu and memory")
    unknown = sorted(set(_normalize_metadata(data.metadata).get("acceleratorKeys", [])) - set(HubConfig.get().accelerators))
    if unknown:
        raise ValueError(f"unknown accelerator profile(s): {', '.join(unknown)}")


def _validate_value(key: str, value: dict) -> BaseModel:
    domain = key_domain(key)
    subject = key_subject(key)
    config = HubConfig.get()
    if domain == "resource_access" and subject not in config.resources.images and get_database_resource(subject) is None:
        raise ValueError(f"Unknown resource '{subject}'")
    if domain == "group_lifecycle":
        return GroupLifecyclePolicy.model_validate(value)
    return ResourceAccessPolicy.model_validate(value)


def set_runtime_override(
    key: str,
    value: dict,
    *,
    actor: str | None,
    enabled: bool = True,
    expected_revision: int | None = None,
) -> dict:
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
            row = existing
        else:
            row = RuntimeConfigOverride(
                key=key,
                domain=domain,
                value_json=json.dumps(new_value, sort_keys=True),
                enabled=enabled,
                revision=1,
                updated_by=actor,
            )
            session.add(row)
        session.flush()
        return _override_to_dict(row)


def clear_runtime_override(key: str, *, actor: str | None = None) -> None:
    _ = actor
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
        "source": "database",
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


def get_database_resources() -> list[dict]:
    try:
        from core.database import get_session
        from core.runtime_config.models import RuntimeResourceDefinition
    except ModuleNotFoundError:
        return []

    try:
        session = get_session()
    except RuntimeError:
        return []
    try:
        rows = session.query(RuntimeResourceDefinition).order_by(RuntimeResourceDefinition.key).all()
        return [_resource_to_dict(row) for row in rows]
    finally:
        session.close()


def get_database_resource(resource_key: str) -> dict | None:
    try:
        from core.database import get_session
        from core.runtime_config.models import RuntimeResourceDefinition
    except ModuleNotFoundError:
        return None

    try:
        session = get_session()
    except RuntimeError:
        return None
    try:
        row = session.query(RuntimeResourceDefinition).filter(RuntimeResourceDefinition.key == resource_key).first()
        if not row or not row.enabled:
            return None
        return _resource_to_dict(row)
    finally:
        session.close()


def set_database_resource(payload: dict, *, actor: str | None) -> dict:
    data = RuntimeResourceWrite.model_validate(payload)
    if data.key in HubConfig.get().resources.images:
        raise ValueError("Helm-provisioned resources are locked; use a database-managed resource key")
    _validate_resource_definition(data)

    from core.database import session_scope
    from core.runtime_config.models import RuntimeResourceDefinition

    with session_scope() as session:
        existing = session.query(RuntimeResourceDefinition).filter(RuntimeResourceDefinition.key == data.key).first()
        if existing and data.expectedRevision is not None and existing.revision != data.expectedRevision:
            raise ValueError(f"Revision mismatch: current={existing.revision}, expected={data.expectedRevision}")
        if existing:
            existing.image = data.image
            existing.requirements_json = json.dumps(data.requirements, sort_keys=True)
            existing.metadata_json = json.dumps(_normalize_metadata(data.metadata), sort_keys=True)
            existing.enabled = data.enabled
            existing.revision += 1
            existing.updated_by = actor
            row = existing
        else:
            row = RuntimeResourceDefinition(
                key=data.key,
                image=data.image,
                requirements_json=json.dumps(data.requirements, sort_keys=True),
                metadata_json=json.dumps(_normalize_metadata(data.metadata), sort_keys=True),
                enabled=data.enabled,
                revision=1,
                updated_by=actor,
            )
            session.add(row)
        session.flush()
        return _resource_to_dict(row)


def delete_database_resource(resource_key: str) -> None:
    if resource_key in HubConfig.get().resources.images:
        raise ValueError("Helm-provisioned resources cannot be deleted from the runtime catalog")

    from core.database import session_scope
    from core.runtime_config.models import RuntimeConfigOverride, RuntimeResourceDefinition

    with session_scope() as session:
        row = session.query(RuntimeResourceDefinition).filter(RuntimeResourceDefinition.key == resource_key).first()
        if row:
            session.delete(row)
        access = session.query(RuntimeConfigOverride).filter(RuntimeConfigOverride.key == resource_access_key(resource_key)).first()
        if access:
            session.delete(access)


def _resource_to_dict(row) -> dict:
    return {
        "key": row.key,
        "source": "database",
        "image": row.image,
        "requirements": _load_json(row.requirements_json),
        "metadata": _load_json(row.metadata_json),
        "enabled": row.enabled,
        "locked": False,
        "revision": row.revision,
        "updatedBy": row.updated_by,
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
    resource_keys = set(HubConfig.get().resources.images)
    resource_keys.update(resource["key"] for resource in get_database_resources() if resource.get("enabled", True))
    for resource_key in resource_keys:
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


def get_resource_catalog() -> list[dict]:
    config = HubConfig.get()
    resources = []
    for key in sorted(config.resources.images):
        metadata = config.get_resource_metadata(key)
        requirements = config.get_resource_requirements(key)
        resources.append(
            {
                "key": key,
                "source": "helm",
                "image": config.get_resource_image(key),
                "requirements": requirements.model_dump(by_alias=True, exclude_none=True)
                if requirements
                else {"cpu": "2", "memory": "4Gi"},
                "metadata": metadata.model_dump(exclude_none=True) if metadata else {},
                "enabled": True,
                "locked": True,
            }
        )
    resources.extend(get_database_resources())
    return resources


def get_effective_resource_image(resource_key: str, helm_images: dict[str, str]) -> str | None:
    if resource_key in helm_images:
        return helm_images[resource_key]
    resource = get_database_resource(resource_key)
    return resource["image"] if resource else None


def get_effective_resource_requirements(resource_key: str, helm_requirements: dict[str, dict]) -> dict | None:
    if resource_key in helm_requirements:
        return helm_requirements[resource_key]
    resource = get_database_resource(resource_key)
    return resource["requirements"] if resource else None


def get_effective_resource_metadata(resource_key: str, helm_metadata: dict[str, dict]) -> dict:
    if resource_key in helm_metadata:
        return helm_metadata[resource_key]
    resource = get_database_resource(resource_key)
    return resource["metadata"] if resource else {}
