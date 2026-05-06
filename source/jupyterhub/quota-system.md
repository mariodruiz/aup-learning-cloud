# User Quota System

The quota system tracks usage sessions and can block new spawns when a user lacks enough balance.

## What Quota Controls

When quota is enabled, the current flow is:

1. a user chooses a resource and runtime on the spawn page
2. the Hub computes the estimated cost from the selected accelerator rate and runtime
3. the Hub blocks the spawn if the user cannot afford it
4. a usage session is recorded while the server runs
5. quota is deducted when the session ends

## Configuration

Quota is configured under `custom.quota`.

```yaml
custom:
  quota:
    enabled: null
    cpuRate: 1
    minimumToStart: 10
    defaultQuota: 0
    refreshRules: {}
```

### Field Meanings

| Field | Meaning |
|------|---------|
| `enabled` | Explicit on/off. When `null`, quota auto-disables for `auto-login` and `dummy` |
| `cpuRate` | Per-minute cost for CPU-only sessions |
| `minimumToStart` | Minimum balance required before any spawn can start |
| `defaultQuota` | Initial balance granted to new users when their quota record is created |
| `refreshRules` | Scheduled balance refresh rules implemented as CronJobs |

## Accelerator Rates

Accelerator-specific rates come from `custom.accelerators.*.quotaRate`.

```yaml
custom:
  accelerators:
    strix-halo:
      quotaRate: 3
    r9700:
      quotaRate: 4
```

The effective estimated cost is:

```text
quota cost = runtime_minutes × selected accelerator rate
```

If no accelerator is selected, the CPU rate is used.

## Auto-Enable Behavior

When `custom.quota.enabled` is left as `null`:

- `auto-login` and `dummy` default to quota disabled
- `github` and `multi` default to quota enabled

## Default Quota For New Users

`defaultQuota` is applied when a user first gets a quota record.

Operationally this means:

- `0` keeps new users at zero until an admin grants balance
- a positive value gives them an initial starting balance automatically

## Unlimited Quota

The platform supports unlimited users.

In the current admin UI, unlimited quota can be set by entering:

- `-1`
- `∞`
- `unlimited`

## Web Admin Operations

The current `/hub/admin/users` page supports:

- inline per-user quota editing
- batch quota updates for selected users
- toggling unlimited quota
- viewing current balances alongside server status

The admin UI also includes a **Refresh Quota** action that can apply a global add-or-set operation to all users.

## Admin API Endpoints

The current quota handlers expose:

- `GET /admin/api/quota/`
- `POST /admin/api/quota/<username>`
- `POST /admin/api/quota/batch`
- `POST /admin/api/quota/refresh`
- `GET /api/quota/rates`
- `GET /api/quota/me`

These endpoints are used by the admin UI and user-facing spawn experience.

## Scheduled Quota Refresh Rules

`refreshRules` allow periodic top-ups or resets.

Example:

```yaml
custom:
  quota:
    refreshRules:
      daily-topup:
        enabled: true
        schedule: "0 0 * * *"
        action: add
        amount: 100
        maxBalance: 500
        targets:
          includeUnlimited: false
          balanceBelow: 400
```

Supported rule concepts include:

- `action: add` or `set`
- `amount`
- `maxBalance`
- `minBalance`
- filters such as `includeUnlimited`, `balanceBelow`, `balanceAbove`, `includeUsers`, `excludeUsers`, and `usernamePattern`

These rules create Kubernetes CronJobs during deployment.

Useful verification commands:

```bash
kubectl -n jupyterhub get cronjobs -l app.kubernetes.io/component=quota-refresh
kubectl -n jupyterhub get jobs -l app.kubernetes.io/component=quota-refresh
kubectl -n jupyterhub logs -l app.kubernetes.io/component=quota-refresh --tail=50
```

## CLI Operations

The repository still includes quota commands in `scripts/manage_users.py`.

Examples:

```bash
python scripts/manage_users.py set-quota user1 user2 --amount 1000
python scripts/manage_users.py add-quota user1 user2 --amount 100
python scripts/manage_users.py list-quota
```

These commands currently work by `kubectl exec` into `deployment/hub` and calling the in-pod quota manager.

## Runtime Behavior Details

Current implementation details worth knowing:

- new users get a quota record on first use
- `defaultQuota` is applied at record creation time
- usage sessions are tracked even when quota deduction is disabled
- unlimited users skip balance deduction
- insufficient balance blocks spawn before the server starts

## User-Facing APIs

Authenticated users can inspect current quota behavior through:

- `GET /api/quota/me`
- `GET /api/quota/rates`

Those responses are used to show balance, enabled state, rates, and `minimumToStart` in the current UI flows.

## Recommended Deployment Flow

After changing quota configuration:

**Single-node:**

```bash
sudo ./auplc-installer rt upgrade
```

**Manual / multi-node Helm:**

```bash
cd runtime
helm upgrade --install jupyterhub ./chart \
  -n jupyterhub --create-namespace \
  -f values-multi-nodes.yaml
```

## Troubleshooting

### User Cannot Start A Server

Check:

- the user's current balance
- the selected accelerator's `quotaRate`
- `minimumToStart`
- whether the user is marked unlimited

### Refresh Rules Did Not Run

```bash
kubectl -n jupyterhub get cronjobs -l app.kubernetes.io/component=quota-refresh
kubectl -n jupyterhub get jobs -l app.kubernetes.io/component=quota-refresh
```

If no CronJobs exist, verify that the rule is enabled and present in the values file used for the last deployment.

### CLI Quota Command Fails

Because the CLI commands use `kubectl exec`, verify:

- you are targeting the correct namespace
- `deployment/hub` exists and is healthy
- your `kubectl` context points at the correct cluster

## Related Pages

- [User Management Guide](user-management.md)
- [Configuration Reference](configuration-reference.md)
