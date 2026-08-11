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

const GITHUB_PREFIX = "github:";
const SAML_PREFIX = "saml:";

/**
 * Username prefixes owned by an external identity provider.
 *
 * Mirrors `_EXTERNAL_USER_PREFIXES` in `runtime/hub/core/handlers.py`. Keep the
 * two in step: the Hub rejects native password operations for every prefix
 * listed there, so a prefix missing here makes the UI offer actions the
 * backend will refuse.
 */
const EXTERNAL_PREFIXES = [GITHUB_PREFIX, SAML_PREFIX] as const;

export function isGitHubUser(username: string): boolean {
  return username.startsWith(GITHUB_PREFIX);
}

export function isSamlUser(username: string): boolean {
  return username.startsWith(SAML_PREFIX);
}

export function isCurrentUserGitHub(): boolean {
  return isGitHubUser(window.jhdata?.user ?? "");
}

/** True when the account is managed by an external IdP rather than the Hub. */
export function isExternalUser(username: string): boolean {
  return EXTERNAL_PREFIXES.some((prefix) => username.startsWith(prefix));
}

/**
 * True only for Hub-managed local accounts.
 *
 * Defined as "carries no external provider prefix" rather than "is not a
 * GitHub user", so a new provider does not silently fall into this bucket.
 */
export function isNativeUser(username: string): boolean {
  return !isExternalUser(username);
}

/** Short provider label for badges, or null for local accounts. */
export function externalProviderLabel(username: string): string | null {
  if (isGitHubUser(username)) return "GitHub";
  if (isSamlUser(username)) return "SSO";
  return null;
}
