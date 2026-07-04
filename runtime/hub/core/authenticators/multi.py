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

"""
Multi Authenticator

Provides support for multiple authentication methods on a single login page.
"""

from __future__ import annotations

from html import escape

from multiauthenticator import MultiAuthenticator
from multiauthenticator.multiauthenticator import PREFIX_SEPARATOR

from core.authenticators.saml import SAML_USERNAME_PREFIX

LOCAL_ACCOUNT_PREFIX = "LocalAccount"

_GITHUB_ICON = (
    '<svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">'
    '<path fill-rule="evenodd" d="M10 0C4.477 0 0 4.484 0 10.017c0 4.425 2.865 8.18 6.839 9.504'
    ".5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343"
    "-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032"
    ".892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951"
    " 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564"
    " 9.564 0 0110 4.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027"
    ".546 1.379.203 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.942"
    ".359.31.678.921.678 1.856 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019"
    ' 10.019 0 0020 10.017C20 4.484 15.522 0 10 0z" clip-rule="evenodd"/></svg>'
)

_SSO_ICON = (
    '<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">'
    '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"'
    ' d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>'
    "</svg>"
)

_SSO_BTN_CLASSES = (
    "w-full flex justify-center items-center py-3 px-4 border border-gray-300"
    " rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white"
    " hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2"
    " focus:ring-blue-500 transition duration-300"
)

_DIVIDER = (
    '<div class="relative mb-6">'
    '<div class="absolute inset-0 flex items-center"><div class="w-full border-t border-gray-300"></div></div>'
    '<div class="relative flex justify-center text-sm">'
    '<span class="px-2 bg-white text-gray-500">Or use local account</span>'
    "</div></div>"
)

_TERMS_OF_USE = (
    '<p class="text-xs text-gray-500 text-center mb-6">'
    "By signing in you agree to the AUP Learning Cloud Terms of Use.</p>"
)


class CustomMultiAuthenticator(MultiAuthenticator):
    """
    MultiAuthenticator with custom login page HTML and refresh_user support.

    Provides a unified login page supporting multiple authentication methods.
    Delegates ``refresh_user`` to the sub-authenticator that owns the user.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from core.authenticators.saml import CustomSAMLAuthenticator

        # SAML applies its own authoritative "saml:" prefix in authenticate(),
        # so suppress the library's login_service-derived prefix to avoid
        # stacking (e.g. "amd sso:saml:user").
        for authenticator in self._authenticators:
            if isinstance(authenticator, CustomSAMLAuthenticator):
                authenticator.prefix = ""

    def validate_username(self, username):
        """Reject usernames that could spoof a prefixed authenticator."""
        if not super().validate_username(username):
            return False
        # Only local (unprefixed) accounts need checking.
        # Prefixed names like "github:user" are created by the OAuth flow
        # itself and are legitimate; block them only when they don't come
        # from a registered prefix.
        if PREFIX_SEPARATOR in username:
            from core.authenticators.saml import CustomSAMLAuthenticator

            known_prefixes = [a.username_prefix for a in self._authenticators if a.username_prefix]
            if any(isinstance(a, CustomSAMLAuthenticator) for a in self._authenticators):
                known_prefixes.append(SAML_USERNAME_PREFIX)
            if not any(username.startswith(p) for p in known_prefixes):
                return False
        return True

    def _find_authenticator_for_user(self, user):
        """Return the sub-authenticator whose prefix matches *user.name*.

        Authenticators with a non-empty prefix are checked first so that
        a catch-all empty prefix (local accounts) never shadows others.
        """
        from core.authenticators.saml import CustomSAMLAuthenticator

        fallback = None
        for authenticator in self._authenticators:
            if isinstance(authenticator, CustomSAMLAuthenticator):
                if user.name.startswith(SAML_USERNAME_PREFIX):
                    return authenticator
                continue
            prefix = authenticator.username_prefix
            if not prefix:
                fallback = authenticator
                continue
            if user.name.startswith(prefix):
                return authenticator
        return fallback

    async def refresh_user(self, user, handler=None):
        authenticator = self._find_authenticator_for_user(user)
        if authenticator is None:
            return True
        return await authenticator.refresh_user(user, handler)

    def get_custom_html(self, base_url):
        from core.authenticators.github_oauth import CustomGitHubOAuthenticator
        from core.authenticators.saml import CustomSAMLAuthenticator

        sso_buttons = []
        local_form = ""
        has_saml = False

        for authenticator in self._authenticators:
            login_service = escape(getattr(authenticator, "login_service", "SSO"))
            url = authenticator.login_url(base_url)

            if isinstance(authenticator, CustomGitHubOAuthenticator):
                sso_buttons.append(
                    f'<div class="mb-4">'
                    f'<a href="{url}{{% if next is defined and next|length %}}?next={{{{next}}}}{{% endif %}}"'
                    f' class="{_SSO_BTN_CLASSES}">'
                    f"{_GITHUB_ICON}Sign in with GitHub</a></div>"
                )
            elif isinstance(authenticator, CustomSAMLAuthenticator):
                has_saml = True
                sso_buttons.append(
                    f'<div class="mb-4">'
                    f'<a href="{url}{{% if next is defined and next|length %}}?next={{{{next}}}}{{% endif %}}"'
                    f' class="{_SSO_BTN_CLASSES}">'
                    f"{_SSO_ICON}Sign in with {login_service}</a></div>"
                )
            else:
                local_form = (
                    f'{_DIVIDER}'
                    f'<form action="{url}" method="post" role="form" class="space-y-6">'
                    f'<input type="hidden" name="_xsrf" value="{{{{ xsrf }}}}" />'
                    f'<div>'
                    f'<label for="username_input" class="block text-sm font-medium text-gray-700 mb-1">Username</label>'
                    f'<input id="username_input" type="text" autocapitalize="off" autocorrect="off"'
                    f' autocomplete="username" name="username" autofocus="autofocus"'
                    f' class="block w-full pl-3 pr-3 py-2 border border-gray-300 rounded-md shadow-sm'
                    f' placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />'
                    f"</div>"
                    f"<div>"
                    f'<label for="password_input" class="block text-sm font-medium text-gray-700 mb-1">Password</label>'
                    f'<input id="password_input" type="password" autocomplete="current-password" name="password"'
                    f' class="block w-full pl-3 pr-3 py-2 border border-gray-300 rounded-md shadow-sm'
                    f' placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />'
                    f"</div>"
                    f'<div class="mt-6">'
                    f'<button id="login_submit" type="submit"'
                    f' class="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm'
                    f' text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2'
                    f' focus:ring-offset-2 focus:ring-blue-500 transition duration-300">Login</button>'
                    f"</div></form>"
                )

        parts = sso_buttons
        if has_saml:
            parts.append(_TERMS_OF_USE)
        if local_form:
            parts.append(local_form)
        return "\n".join(parts)
