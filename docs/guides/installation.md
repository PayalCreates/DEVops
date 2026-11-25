# Installation guide (Windows 10/11, 8 GB RAM)

Everything here is free and open source (Docker Desktop is free for personal and educational use).

## 1. Check virtualization
Task Manager → Performance → CPU → **Virtualization: Enabled**. If it's disabled, enable Intel VT-x / AMD SVM in the BIOS.

## 2. Install tools (PowerShell **as Administrator**)
```powershell
winget install --id Microsoft.PowerShell -e          # PowerShell 7 (use it for everything below)
winget install --id Git.Git -e
winget install --id GitHub.cli -e
winget install --id Microsoft.VisualStudioCode -e
winget install --id Python.Python.3.12 -e
winget install --id OpenJS.NodeJS.LTS -e
winget install --id Docker.DockerDesktop -e
wsl --install                                         # WSL2 + Ubuntu, then REBOOT
```
For the Kubernetes part, add:
```powershell
winget install --id Kubernetes.kubectl -e
winget install --id Kubernetes.kind -e
winget install --id Helm.Helm -e
winget install --id Hashicorp.Terraform -e
```
Ansible runs inside WSL Ubuntu: `sudo apt update && sudo apt install -y ansible`, or let
`ansible/playbooks/provision-workstation.yml` install the rest of the toolchain there.

## 3. Cap WSL2 memory (important on 8 GB)
```powershell
@'
[wsl2]
memory=4GB
processors=2
swap=4GB
'@ | Set-Content "$env:USERPROFILE\.wslconfig" -Encoding utf8NoBOM
wsl --shutdown
```
Docker Desktop → Settings: **Use WSL 2 based engine** ✅. **Kubernetes** ❌ (we use kind). Resources → WSL integration → enable for Ubuntu.

## 4. Git configuration
```powershell
git config --global core.autocrlf false     # .gitattributes controls line endings (LF for Linux scripts)
git config --global init.defaultBranch main
git config --global pull.rebase true
```

## 5. Verify
```powershell
$PSVersionTable.PSVersion; git --version; python --version; node --version
docker version --format "Client {{.Client.Version}} / Server {{.Server.Version}}"
docker run --rm hello-world
wsl -l -v                                    # Ubuntu, VERSION 2
kubectl version --client; kind version; helm version; terraform version
```
Next: [local-setup.md](local-setup.md).
