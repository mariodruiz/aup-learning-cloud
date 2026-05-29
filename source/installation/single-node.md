# Single-Node Deployment

This guide covers the current single-node workflow driven by `./auplc-installer`.

:::{seealso}
For the shortest path, see [Quick Start](quick-start.md).
:::

## What The Installer Does

`./auplc-installer install` is the canonical workstation deployment path. It can:

- detect supported AMD GPU families and SKUs
- install K3s and supporting tools
- deploy the ROCm GPU device plugin and node labeller
- generate a local values overlay
- pull or build required images (default: **pull** from `--image-registry`)
- deploy the Hub runtime from `runtime/chart`

The installer can run as a regular user. Commands that need root (install, uninstall, install-tools) prompt for your password once and keep the sudo credential cache fresh. Prefixing with `sudo` is optional and skips the prompt.

## Prerequisites

- Ubuntu 24.04
- sudo access
- Supported **Ryzen AI 300 series and above** APUs or **Radeon 9000 series** PCIe GPUs (ROCm)
- Docker installed if you are using the default Docker-backed runtime path
- `build-essential`
- `python3-questionary` and `python3-prompt-toolkit` (apt), or `pip install questionary prompt_toolkit` (conda/venv), for the interactive TUI

```bash
sudo apt install build-essential
sudo apt install python3-questionary python3-prompt-toolkit
```

Optional Docker installation:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
docker --version
```

## Standard Install

**Interactive (recommended):**

```bash
git clone https://github.com/AMDResearch/aup-learning-cloud.git
cd aup-learning-cloud
./auplc-installer
```

**Non-interactive:**

```bash
git clone https://github.com/AMDResearch/aup-learning-cloud.git
cd aup-learning-cloud
./auplc-installer install
```

After installation, access the Hub at <http://localhost:30890>.

## Interactive TUI Reference

Launch the wizard with `./auplc-installer` (or `./auplc-installer tui`). The main menu offers Install, Uninstall, Pack offline, Dev mode, Runtime-only, Image management, Install helm + k9s, and Detect GPU.

For a first-time **Install**, the recommended choices are:

| Prompt | Recommended choice | Notes |
|--------|-------------------|-------|
| **Pick an action** | `Install` | Full deploy: K3s + images + Hub |
| **GPU selection** | `Auto-detect` | Uses `rocminfo` or KFD topology on the host. Override only if detection is wrong or you are preparing an offline bundle for a different GPU. |
| **K3s container runtime** | `Docker` | Default for local/dev installs. Choose `containerd` only for offline/portable workflows. |
| **Image source** | `pull` | Fetches pre-built images from `--image-registry` (default: `ghcr.io/amdresearch`). Choose `build` to compile from `dockerfiles/` via Makefile. |
| **Image registry prefix** | `ghcr.io/amdresearch` | Leave as-is unless you pull from a fork or private registry. |
| **Image tag** | `latest` | Tag prefix only—a GPU suffix (for example `-gfx1150`) is appended automatically. |
| **Registry mirror prefix** | *(leave blank)* | Only needed behind a registry mirror. |
| **PyPI mirror URL** | *(leave blank)* | Only needed behind a PyPI mirror. |
| **npm mirror URL** | *(leave blank)* | Only needed behind an npm mirror. |
| **Course selection** | `all` | Installs every course environment. Choose `basic` for Hub + CPU/GPU bases only, or `custom` to pick individual courses. |
| **Proceed with installation?** | `Yes` | Review the configuration summary, then confirm. |

The resulting **Configuration summary** should look like:

```text
Configuration summary
  GPU              : auto-detect
  K3s runtime      : Docker
  Image source     : pull
  Image registry   : ghcr.io/amdresearch
  Image tag        : latest
  Registry mirror  : (none)
  PyPI mirror      : (default)
  npm mirror       : (default)
  Courses          : cpu, gpu, Course-CV, Course-DL, Course-LLM, Course-PhySim
```

## Important Defaults In This Repository

The current checked-in `runtime/values.yaml` is oriented to simple local deployment:

- `custom.authMode: auto-login`
- `custom.adminUser.enabled: false`
- `hub.db.pvc.storageClassName: local-path`
- `singleuser.storage.dynamic.storageClass: local-path`
- `proxy.service.type: NodePort`
- `proxy.service.nodePorts.http: 30890`
- `ingress.enabled: false`
- `prePuller.hook.enabled: false`
- `prePuller.continuous.enabled: false`

That means NFS, ingress, TLS, and auto-created admin credentials are optional configuration choices, not default behavior.

## Installer Command Matrix

### Core Lifecycle

```bash
./auplc-installer install
./auplc-installer install --dry-run
./auplc-installer uninstall
./auplc-installer detect-gpu
./auplc-installer install-tools
./auplc-installer help
```

### Runtime Lifecycle

```bash
./auplc-installer rt install
./auplc-installer rt upgrade
./auplc-installer rt remove
./auplc-installer rt reinstall
```

### Image Lifecycle

```bash
./auplc-installer img build
./auplc-installer img build hub cv
./auplc-installer img build base-rocm --gpu=strix
./auplc-installer img pull
```

### Development Workflow

```bash
./auplc-installer dev
./auplc-installer dev deploy
./auplc-installer dev upgrade
./auplc-installer dev reinstall
```

## Common Install Flags

```bash
# Default: pull pre-built images from the configured registry
./auplc-installer install

# Preview the Configuration summary (no sudo, no system changes)
./auplc-installer install --dry-run

# Override image tag or registry
./auplc-installer install --image-tag=develop
./auplc-installer install --image-registry=ghcr.io/myfork

# Build locally instead of pull
./auplc-installer install --image-source=build

# Explicitly set GPU family / target
./auplc-installer install --gpu=strix-halo

# Restrict courses
./auplc-installer install --courses=basic

# Use containerd mode instead of Docker-backed mode
./auplc-installer install --runtime=containerd

# Use registry / package mirrors
./auplc-installer install \
  --mirror=mirror.example.com \
  --mirror-pip=https://pypi.example.com/simple \
  --mirror-npm=https://registry.npmmirror.com
```

Supported install-time flags map to these environment variables:

| Flag | Environment Variable | Meaning |
|------|----------------------|---------|
| `--gpu=TYPE` | `GPU_TYPE` | Force GPU type / family (`auto` clears override) |
| `--runtime=docker\|containerd` | `K3S_USE_DOCKER` | K3s container runtime (legacy: `--docker=0\|1`) |
| `--image-source=pull\|build` | — | Pull from registry (default) or build locally (legacy: `install --pull`, `ghcr` alias) |
| `--image-registry=PREFIX` | `IMAGE_REGISTRY` | Custom-image registry prefix |
| `--image-tag=TAG` | `IMAGE_TAG` | Custom-image tag prefix (GPU suffix appended automatically) |
| `--courses=SPEC` | `AUPLC_COURSES` | Course subset (`all`, `basic`, `none`, or comma-separated keys) |
| `--mirror=HOST` | `MIRROR_PREFIX` | Container registry mirror prefix |
| `--mirror-pip=URL` | `MIRROR_PIP` | Python package mirror |
| `--mirror-npm=URL` | `MIRROR_NPM` | npm registry mirror |
| `--dry-run` / `--try-run` | — | Print Configuration summary and exit (install only) |
| `-y` / `--yes` | `AUPLC_YES=1` | Assume yes to all prompts |
| `-v` / `--verbose` | `AUPLC_VERBOSE=1` | Stream every subprocess line live |

## Offline And Portable Workflows

### Containerd / Portable-Oriented Local Install

```bash
./auplc-installer install --runtime=containerd
```

This path exports images into K3s image storage and is better suited for portable or partially disconnected use than the default Docker-backed path.

### Offline Bundle Workflow

Create an offline bundle on a connected machine:

```bash
./auplc-installer pack

# Or build bundle from local images/artifacts
./auplc-installer pack --local
```

Transfer the bundle to the target machine, unpack it, then run:

```bash
./auplc-installer install
```

The installer auto-detects the bundle via `manifest.json` and switches into offline mode.

## Common Day-2 Operations

### Change Runtime Configuration

Edit `runtime/values.yaml` or the local overlay, then run:

```bash
./auplc-installer rt upgrade
```

### Rebuild Images After Code Or Dockerfile Changes

```bash
./auplc-installer img build
./auplc-installer rt reinstall
```

### Work On Selected Images Only

```bash
./auplc-installer img build hub cv
```

This is useful when you only changed the Hub or a specific course image.

## Local Configuration Files

- `runtime/values.yaml` - repository default deployment values
- `runtime/values.local.yaml` - installer-generated local overlay

The installer-generated overlay captures detected accelerator selectors and image tags for the local machine. Prefer editing `runtime/values.yaml` for intentional site configuration, then redeploy with:

```bash
./auplc-installer rt upgrade
```

## Verification

```bash
kubectl get pods -n jupyterhub
kubectl get svc -n jupyterhub
kubectl get pvc -n jupyterhub
```

You can also inspect the deployed route and logs:

```bash
kubectl logs -n jupyterhub deployment/hub --tail=100
kubectl get events -n jupyterhub --sort-by=.metadata.creationTimestamp
```

If you explicitly enabled admin bootstrap:

```bash
kubectl -n jupyterhub get secret jupyterhub-admin-credentials \
  -o jsonpath='{.data.admin-password}' | base64 -d && echo
```

## Troubleshooting Notes

- If you changed `runtime/values.yaml`, use `./auplc-installer rt upgrade`.
- If you changed container images or Dockerfiles, use `./auplc-installer img build` followed by `./auplc-installer rt reinstall`.
- If you need cluster-specific storage, ingress, or TLS behavior, those are configuration changes on top of the default single-node setup, not built-in assumptions.
