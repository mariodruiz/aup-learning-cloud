# Quick Start

This is the shortest path to a local single-node AUP Learning Cloud deployment using **`auplc-installer`**, the Python-based installer for this repository.

The installer can run as a regular user. When a step needs elevated privileges (for example K3s installation), it prompts for your password once and keeps the sudo credential cache fresh—you do not need to prefix every command with `sudo`. Running with `sudo ./auplc-installer ...` is still supported and skips the password prompt.

## Prerequisites

- Ubuntu 24.04
- sudo access
- Supported **Ryzen AI 300 series and above** APUs or **Radeon 9000 series** PCIe GPUs (ROCm)
- Docker available for the default install path

Install basic host dependencies:

```bash
sudo apt install build-essential
```

If Docker is not installed yet:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
docker --version
```

### TUI dependencies (required for interactive install)

The recommended `./auplc-installer` wizard requires **`questionary`** and **`prompt_toolkit`**.

**System Python users (apt):**

```bash
sudo apt install python3-questionary python3-prompt-toolkit
```

**Conda or virtualenv users:** install with pip inside your active environment instead of the apt packages:

```bash
pip install questionary prompt_toolkit
```

Non-interactive `./auplc-installer install` does not need these packages.

## Recommended: Interactive Install

Clone the repository and launch the wizard from the repo root:

```bash
git clone https://github.com/AMDResearch/aup-learning-cloud.git
cd aup-learning-cloud
./auplc-installer
```

In a real terminal, invoking the installer with **no subcommand** also opens the TUI automatically (same as `tui`).

For a first-time install, pick **Install** and press **Enter** at each prompt to accept the defaults. Before installation starts, you should see a summary like this:

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

The installer requests your sudo password once, then runs eight stages: GPU detection, initial values overlay, helm + k9s install, K3s install, image pull (or build), ROCm device plugin + node labeller, values overlay refresh, and JupyterHub runtime deploy. When it finishes, open <http://localhost:30890>.

For a prompt-by-prompt explanation of every TUI choice, see [Interactive TUI reference](single-node.md#interactive-tui-reference) in the single-node guide.

## Command-Line Install

Non-interactive install with the same defaults as the TUI (`pull`, `latest` tag, Docker runtime, all courses):

```bash
git clone https://github.com/AMDResearch/aup-learning-cloud.git
cd aup-learning-cloud
./auplc-installer install
```

Preview the plan without installing:

```bash
./auplc-installer install --dry-run
```

To override GPU detection, pick your GPU below—the install command updates to match your selection:

```{eval-rst}
.. include:: includes/selector-quickstart-gpu.rst
```

After installation completes, open <http://localhost:30890>.

The checked-in default values in this repository use:

- `custom.authMode: auto-login`
- `proxy.service.type: NodePort`
- `proxy.service.nodePorts.http: 30890`
- `local-path` storage

So the default local experience is a simple HTTP NodePort deployment.

## Common Variants

```bash
# Default non-interactive path (pull from registry, latest tag)
./auplc-installer install

# Preview configuration without sudo or system changes
./auplc-installer install --dry-run

# Use a different image tag prefix (GPU suffix appended automatically)
./auplc-installer install --image-tag=develop

# Build images locally instead of pull
./auplc-installer install --image-source=build

# Override GPU detection
./auplc-installer install --gpu=strix-halo

# Install only Hub plus CPU/GPU base environments
./auplc-installer install --courses=basic

# Use containerd mode for more portable/offline-oriented operation
./auplc-installer install --runtime=containerd

# Use registry and package mirrors
./auplc-installer install \
  --mirror=mirror.example.com \
  --mirror-pip=https://pypi.tuna.tsinghua.edu.cn/simple
```

## Uninstall

```bash
./auplc-installer uninstall
```

## Next Steps

- For all installer subcommands, TUI prompts, and runtime workflows, see [Single-Node Deployment](single-node.md)
- For auth and resource configuration, see [JupyterHub Configuration](../jupyterhub/index.md)
