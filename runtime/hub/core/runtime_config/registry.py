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

"""Allowlist for source-aware runtime overlay keys."""

from __future__ import annotations

from re import fullmatch
from typing import Literal, TypeAlias

RuntimeDomain: TypeAlias = Literal["group_lifecycle", "resource_access"]


def group_lifecycle_key(group_name: str) -> str:
    return f"groups.{group_name}.lifecycle"


def resource_access_key(resource_key: str) -> str:
    return f"resources.{resource_key}.access"


def key_domain(key: str) -> RuntimeDomain:
    if fullmatch(r"groups\.[A-Za-z0-9_.:-]+\.lifecycle", key):
        return "group_lifecycle"
    if fullmatch(r"resources\.[A-Za-z0-9_.:-]+\.access", key):
        return "resource_access"
    raise ValueError(f"Runtime override key is not allowlisted: {key}")


def key_subject(key: str) -> str:
    domain = key_domain(key)
    if domain == "group_lifecycle":
        return key.removeprefix("groups.").removesuffix(".lifecycle")
    return key.removeprefix("resources.").removesuffix(".access")
