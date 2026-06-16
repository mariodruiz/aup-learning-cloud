# Authentication Guide

This guide describes the current authentication behavior of AUP Learning Cloud, including auth modes, GitHub team sync, native accounts, password handling, and admin bootstrap.

## Overview

Authentication is controlled by `custom.authMode`.

Supported modes:

| Mode | Meaning |
|------|---------|
| `auto-login` | Shared local mode with no credentials |
| `dummy` | Testing mode that accepts any username/password |
| `github` | GitHub App only |
| `multi` | GitHub App plus native local accounts |

The current checked-in single-node defaults use `auto-login`.

## Current Login Behavior

### `auto-login`

- no credential prompt
- useful for local demos and simple installs
- quota is usually auto-disabled unless explicitly turned on

### `dummy`

- any username and password is accepted
- useful only for testing
- not suitable for real user management

### `github`

- only GitHub App is offered
- organization membership can be enforced through `allowed_organizations`
- GitHub teams can be synchronized into Hub groups

### `multi`

- a combined login page is shown
- GitHub App and local accounts both appear on the same page
- local users are backed by the custom first-use authenticator

## Admin Bootstrap

Admin bootstrap is optional.

```yaml
custom:
  adminUser:
    enabled: true
```

When enabled, the chart creates the `jupyterhub-admin-credentials` secret and the Hub bootstraps the `admin` user.

Retrieve credentials with:

```bash
kubectl -n jupyterhub get secret jupyterhub-admin-credentials \
  -o jsonpath='{.data.admin-password}' | base64 -d && echo

kubectl -n jupyterhub get secret jupyterhub-admin-credentials \
  -o jsonpath='{.data.api-token}' | base64 -d && echo
```

## GitHub App

GitHub App configuration lives under `hub.config.GitHubOAuthenticator`.

```yaml
custom:
  githubOrgName: "your-github-org"

hub:
  config:
    GitHubOAuthenticator:
      oauth_callback_url: "https://your.domain.com/hub/github/oauth_callback"
      client_id: "TODO"
      client_secret: "TODO"
      allowed_organizations:
        - your-github-org
      scope:
        - read:user
        - read:org
```

### What The Custom Authenticator Adds

The current GitHub authenticator does more than the stock OAuth login flow:

- preserves OAuth auth state for later use
- refreshes user tokens proactively when refresh tokens are available
- re-fetches GitHub team membership during refresh
- gracefully handles GitHub App installation redirects that return to the OAuth callback URL without normal OAuth state

### GitHub Team Sync

In GitHub-backed deployments, the Hub can:

- fetch the user's team memberships during login
- refresh team memberships again at spawn time
- map those teams into JupyterHub groups
- use group membership to control visible resources

The org name used for synchronization comes from `custom.githubOrgName`.

## GitHub App Integration For Repositories

GitHub App integration is optional and is related to private repository cloning, not to basic OAuth login itself.

```yaml
custom:
  gitClone:
    githubAppName: "your-app-slug"
```

When configured, GitHub-authenticated users can install or authorize the app and use repo-picker flows on the spawn page.

For setup instructions, see [GitHub App Setup](github-app-setup.md).

## Native Accounts

Native accounts are used in `multi` mode.

Important behavior:

- users cannot self-register arbitrarily
- admins can create users from the web admin console or CLI scripts
- native passwords can be reset by admins
- users can be forced to change password on next login

The custom first-use authenticator currently sets `create_users = False`, so local accounts must exist before a user can sign in.

## Native Password Policy

Current local password checks require:

- at least 8 characters
- at least one uppercase letter
- at least one lowercase letter
- at least one digit
- at least one special character

That policy applies when admins set passwords and when users change them.

### Forced Password Change Flow

The Hub exposes:

- `/auth/check-force-password-change`
- `/auth/change-password`

This supports workflows such as:

- admin creates a local user
- admin sets an initial password
- the user logs in and is required to choose a new password on first use

## Group-Based Resource Access

Resource visibility is controlled by `custom.teams.mapping`.

```yaml
custom:
  teams:
    mapping:
      github-users:
        - cpu
        - gpu
      native-users:
        - cpu
        - Course-CV
```

In current behavior:

- GitHub users are assigned a fallback `github-users` group
- native users can be assigned `native-users`
- GitHub-synced groups and system-managed groups have protection rules in the admin surface

## Admin And Script Workflows

### Create A Batch Of Users

```bash
python scripts/generate_users_template.py --prefix student --count 50 --output users.csv
python scripts/manage_users.py create users.csv
```

### Set Or Rotate Passwords

```bash
python scripts/manage_users.py set-passwords users.csv --generate
```

### Grant Or Revoke Admin

```bash
python scripts/manage_users.py set-admin teacher01 teacher02
python scripts/manage_users.py set-admin --revoke student01
```

The web admin console under `/hub/admin` can also create users, reset passwords, and toggle admin privileges.

## Recommended Operational Flow

### Single-Node

After editing auth-related values, redeploy with:

```bash
sudo ./auplc-installer rt upgrade
```

### Manual / Multi-Node Helm

```bash
cd runtime
helm upgrade --install jupyterhub ./chart \
  -n jupyterhub --create-namespace \
  -f values-multi-nodes.yaml
```

## Troubleshooting

### GitHub Users Do Not See Expected Resources

Check:

- `custom.githubOrgName`
- `hub.config.GitHubOAuthenticator.allowed_organizations`
- `custom.teams.mapping`
- whether the user actually belongs to the expected GitHub teams

### No Admin User Was Created

Confirm that `custom.adminUser.enabled: true` is set, then restart or upgrade the runtime.

```bash
kubectl logs -n jupyterhub deployment/hub | grep -i admin
```

### Native Users Cannot Log In

Confirm:

- the deployment is using `multi` mode
- the user was created by an administrator first
- the user has a valid local password record

### Password Change Keeps Failing

This usually means the new password does not satisfy the current strength policy. Re-check length, uppercase, lowercase, digit, and special-character requirements.

## Related Documentation

- [GitHub App Setup](github-app-setup.md)
- [User Management Guide](user-management.md)
- [Configuration Reference](configuration-reference.md)
