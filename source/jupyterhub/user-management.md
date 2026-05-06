# User Management Guide

This guide covers the current user-management surfaces in AUP Learning Cloud.

There are now two real workflows:

- **Web admin console** at `/hub/admin`
- **CLI scripts** for spreadsheet-driven bulk operations

The web console is now the primary day-to-day interface.

## Prerequisites

For CLI workflows, install the documented Python dependencies first:

```bash
pip install pandas openpyxl requests
```

If you are using script-based operations against the Hub API, set:

```bash
export JUPYTERHUB_URL="http://localhost:30890"
export JUPYTERHUB_TOKEN=$(kubectl -n jupyterhub get secret jupyterhub-admin-credentials \
  -o jsonpath='{.data.api-token}' | base64 -d)
```

## Admin Bootstrap

If you want the chart to create the initial admin credentials automatically:

```yaml
custom:
  adminUser:
    enabled: true
```

Then retrieve the credentials with:

```bash
kubectl -n jupyterhub get secret jupyterhub-admin-credentials \
  -o jsonpath='{.data.admin-password}' | base64 -d && echo

kubectl -n jupyterhub get secret jupyterhub-admin-credentials \
  -o jsonpath='{.data.api-token}' | base64 -d && echo
```

## Web Admin Console

Open `/hub/admin` after logging in as an admin user.

### Users View

The **Users** page supports:

- searching and paging users
- filtering to users with active servers
- inline quota editing when quota is enabled
- starting and stopping user servers
- creating native users
- editing user details
- resetting passwords for native users
- batch password reset for selected native users
- batch quota update for selected users
- batch delete for deletable users
- opening a per-user usage detail view

Important behavior from the current implementation:

- admin users and the currently logged-in admin are protected from deletion
- password reset actions apply only to native users
- unlimited quota can be entered with `-1`, `∞`, or `unlimited`
- user creation flows can pre-fill quota when quota is enabled

### Common User Actions

#### Create Native Users

Use **Create Users** in the Users view to:

- enter one username or many usernames at once
- generate random passwords or set a shared password
- force password change on first login
- optionally grant admin privileges

After creation, copy the generated credentials table and deliver it securely to users.

#### Reset Passwords

The current admin flow exposes:

- `/admin/reset-password`
- `/admin/api/set-password`
- `/admin/api/batch-set-password`

This is available only for native users, not GitHub-authenticated identities.

#### Start And Stop Servers

Admins can start or stop user servers directly from the Users page, which is helpful for:

- recovering stuck sessions
- clearing idle notebook servers manually
- preparing classroom demos or labs

### Groups View

The **Groups** page distinguishes among:

- **GitHub-synced groups**
- **system-managed groups**
- **manual groups**

It supports:

- creating manual groups
- searching groups
- editing group properties
- reviewing group-to-resource mappings
- adding and removing users from editable groups
- manual GitHub sync through **Sync Now** when `custom.githubOrgName` is configured

Current protection model:

- **system-managed groups** are read-only for membership edits
- **GitHub-synced groups** are protected from deletion, but admins can still add extra users manually
- **native-users** may appear as a normal editable group unless it was created with a protected source property

### Dashboard View

The **Dashboard** page provides:

- total users
- active sessions
- total usage minutes
- active users this week
- usage trends
- resource distribution
- top-user views
- live active sessions
- pending spawns

Use this as the primary operational view for current platform usage.

## CLI Scripts

The repository still includes CLI tools for bulk management.

### Generate Templates

```bash
# Generate a CSV template
python scripts/generate_users_template.py --prefix student --count 50 --output users.csv

# Generate an Excel template
python scripts/generate_users_template.py --prefix AUP --count 30 --output aup_users.xlsx

# Generate explicit names
python scripts/generate_users_template.py --names alice bob charlie --output custom_users.csv
```

### Manage Users

```bash
# Create users from a file
python scripts/manage_users.py create users.csv

# List users
python scripts/manage_users.py list

# Export users
python scripts/manage_users.py export backup.xlsx

# Delete users
python scripts/manage_users.py delete remove_list.csv --yes
```

### Manage Admins

```bash
# Promote admins
python scripts/manage_users.py set-admin teacher01 teacher02

# Revoke admin
python scripts/manage_users.py set-admin --revoke student01
```

### Manage Passwords

```bash
# Set passwords from file
python scripts/manage_users.py set-passwords users.csv --generate -o passwords_output.csv

# Use one shared password
python scripts/manage_users.py set-passwords users.csv --generate --default-password "Welcome123"

# Skip force-change behavior
python scripts/manage_users.py set-passwords users.csv --no-force-change
```

### Manage Quota From CLI

Quota commands remain available too:

```bash
python scripts/manage_users.py set-quota user1 user2 --amount 1000
python scripts/manage_users.py add-quota user1 user2 --amount 100
python scripts/manage_users.py list-quota
```

These commands use `kubectl exec` into `deployment/hub`, so they depend on a healthy Kubernetes context and namespace.

## Common Workflows

### Onboard A Class

```bash
python scripts/generate_users_template.py --prefix student --count 50 --output users.csv
python scripts/manage_users.py create users.csv
python scripts/manage_users.py set-passwords users.csv --generate -o passwords_output.csv
```

Then distribute credentials and optionally set initial quota from the web admin console or CLI.

### Promote Teaching Staff

```bash
python scripts/manage_users.py set-admin teacher01 teacher02
```

### Back Up Current User State

```bash
python scripts/manage_users.py export backup.xlsx
```

## Recommended Operational Flow

### Single-Node

After config changes:

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

### Script Cannot Connect To The Hub

Check:

- `JUPYTERHUB_URL`
- `JUPYTERHUB_TOKEN`
- that the Hub is reachable at `/hub/api/`

### Password Reset Fails

This usually means one of:

- the target user is a GitHub user
- the password does not satisfy the native password policy
- the current admin session lacks the expected permissions

### Batch Quota Or Password Operations Fail

For CLI commands that depend on `kubectl exec`, verify:

- current kube context
- namespace
- `deployment/hub` health

## Related Pages

- [Authentication Guide](authentication-guide.md)
- [User Quota System](quota-system.md)
- [Configuration Reference](configuration-reference.md)
