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

"""Runtime source-aware access overlay helpers."""

from core.runtime_config.schemas import GroupLifecyclePolicy, ResourceAccessPolicy

_SERVICE_EXPORTS = {
    "clear_runtime_override",
    "get_effective_resources_for_group",
    "get_effective_resources_for_user",
    "get_effective_resource_image",
    "get_effective_resource_metadata",
    "get_effective_resource_requirements",
    "get_resource_catalog",
    "get_database_resource",
    "get_database_resources",
    "get_group_lifecycle_policy",
    "get_resource_access_policy",
    "get_runtime_overrides",
    "get_spawn_block_reason_for_user",
    "set_database_resource",
    "delete_database_resource",
    "set_runtime_override",
}


def __getattr__(name: str):
    if name in _SERVICE_EXPORTS:
        from core.runtime_config import service

        return getattr(service, name)
    raise AttributeError(name)


__all__ = ["GroupLifecyclePolicy", "ResourceAccessPolicy", *_SERVICE_EXPORTS]
