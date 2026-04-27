// Copyright (C) 2025 Advanced Micro Devices, Inc. All rights reserved.
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

import type { ResourceMetadata, ResourceRequirements } from "./resource.js";

export interface GroupLifecyclePolicy {
  spawnSuspended: boolean;
  startsAt?: string | null;
  expiresAt?: string | null;
  reason: string;
}

export interface ResourceAccessPolicy {
  addGroups: string[];
  denyGroups: string[];
}

export interface RuntimeOverlay {
  key: string;
  domain: string;
  value: Record<string, unknown>;
  enabled: boolean;
  revision: number;
  updatedBy?: string | null;
  reason?: string | null;
  source: "database";
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface RuntimeControlsGroup {
  name: string;
  source: "helm" | "database";
  baselineResources: string[];
  effectiveResources: string[];
  lifecycle: GroupLifecyclePolicy;
}

export interface RuntimeControlsResource {
  key: string;
  source: "helm";
  image: string;
  requirements: ResourceRequirements;
  metadata: Partial<ResourceMetadata>;
  access: ResourceAccessPolicy;
  baselineGroups: string[];
}

export interface RuntimeControlsResponse {
  groups: RuntimeControlsGroup[];
  resources: RuntimeControlsResource[];
  overrides: RuntimeOverlay[];
}
