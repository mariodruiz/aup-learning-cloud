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

import type { RuntimeControlsResource, RuntimeControlsResponse, RuntimeOverlay } from "../types/runtimeControls.js";
import { adminApiRequest } from "./client.js";

export async function getRuntimeControls(): Promise<RuntimeControlsResponse> {
  return adminApiRequest<RuntimeControlsResponse>("/runtime-controls");
}

export async function setRuntimeOverlay(
  key: string,
  value: Record<string, unknown>,
  expectedRevision?: number
): Promise<RuntimeOverlay> {
  return adminApiRequest<RuntimeOverlay>(`/runtime-controls/${encodeURIComponent(key)}`, {
    method: "PATCH",
    body: JSON.stringify({ value, expectedRevision }),
  });
}

export async function resetRuntimeOverlay(key: string): Promise<{ message: string }> {
  return adminApiRequest<{ message: string }>(`/runtime-controls/${encodeURIComponent(key)}`, {
    method: "DELETE",
  });
}

export async function saveRuntimeResource(resource: RuntimeControlsResource): Promise<RuntimeControlsResource> {
  const body = {
    key: resource.key,
    image: resource.image,
    requirements: resource.requirements,
    metadata: resource.metadata,
    enabled: resource.enabled ?? true,
    expectedRevision: resource.revision,
  };
  return adminApiRequest<RuntimeControlsResource>("/runtime-controls/resources", {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function deleteRuntimeResource(resourceKey: string): Promise<{ message: string }> {
  return adminApiRequest<{ message: string }>(`/runtime-controls/resources/${encodeURIComponent(resourceKey)}`, {
    method: "DELETE",
  });
}
