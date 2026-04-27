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

"""Typed runtime overlay schemas."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field, model_validator


class GroupLifecyclePolicy(BaseModel):
    """Operational lifecycle policy for a JupyterHub group."""

    spawnSuspended: bool = False
    startsAt: datetime | None = None
    expiresAt: datetime | None = None

    model_config = {"extra": "ignore"}

    def block_reason(self, now: datetime | None = None) -> str | None:
        reference = self.startsAt or self.expiresAt
        current_time = now or datetime.now(tz=reference.tzinfo if reference and reference.tzinfo else timezone.utc)
        if reference and reference.tzinfo is None and current_time.tzinfo is not None:
            current_time = current_time.replace(tzinfo=None)
        if self.spawnSuspended:
            return "Group spawn access is suspended"
        if self.startsAt and current_time < self.startsAt:
            return "Group spawn access has not started"
        if self.expiresAt and current_time > self.expiresAt:
            return "Group spawn access has expired"
        return None


class ResourceAccessPolicy(BaseModel):
    """Runtime access overlay for a Helm-owned resource."""

    addGroups: list[str] = Field(default_factory=list)
    denyGroups: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def validate_disjoint_groups(self) -> ResourceAccessPolicy:
        overlap = sorted(set(self.addGroups) & set(self.denyGroups))
        if overlap:
            raise ValueError(f"groups cannot be both added and denied: {', '.join(overlap)}")
        return self


class RuntimeOverrideWrite(BaseModel):
    value: dict
    enabled: bool = True
    expectedRevision: int | None = None

    model_config = {"extra": "forbid"}


class RuntimeResourceWrite(BaseModel):
    key: str
    image: str
    requirements: dict[str, str]
    metadata: dict = Field(default_factory=dict)
    enabled: bool = True
    expectedRevision: int | None = None

    model_config = {"extra": "forbid"}
