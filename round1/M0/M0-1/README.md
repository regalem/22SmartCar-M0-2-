# M0-1｜从零搭建开发环境

> - **难度**：★
> - **主环境**：VMware Workstation + Ubuntu 22.04.5 LTS
> - **验收结果**：`PASS=30`、`FAIL=0`、`WARN=2`
> - **当前状态**：环境验收已通过，README 已上传 GitHub；真实远程登录待完成

## 1. 任务概述

M0-1 要求在三选一环境中完成 Ubuntu、ROS2、Python 虚拟环境、C/C++、VS Code 和 Git 的安装，并提交一份以“本机踩坑实录”为重点的 README。

本项目最终选择 **VMware Workstation 中的 Ubuntu 22.04.5 LTS** 作为主开发环境。此前也实际搭建并验证过 WSL2 Ubuntu 22.04：

- VMware 环境用于后续 conda、VS Code、C/C++ 调试和 M0-2 开发。
- WSL2 环境完成了 ROS2 Humble 安装，并通过 273 个软件包检查和 `talker/listener` 通信测试。
- 曾准备过双系统所需的磁盘空间和启动 U 盘，但在确认 WSL2 与该虚拟机满足学习需求后，没有继续安装双系统。

选择 VMware 作为主环境，是因为它与普通 Ubuntu 桌面更接近，网络、桌面程序、VS Code 和调试工具的行为更直观。WSL2 启动更轻量，适合快速验证 ROS2，但 Windows/WSL 两套环境容易在 Python、代理和路径问题上产生混淆。

## 2. 最终环境

| 项目 | 配置或状态 |
| :--- | :--- |
| 宿主机 | Windows 11 家庭版，AMD Ryzen 9 9955HX，16 GB 内存，RTX 5060 Laptop 8 GB |
| 虚拟化 | VMware Workstation，Ubuntu 22.04 虚拟机 |
| 虚拟机配置 | 8 vCPU、4 GB 内存、NAT 网络模式 |
| 系统 | Ubuntu 22.04.5 LTS，x86_64 |
| ROS2 | ROS2 Humble，官方 `check_env.sh` 验证通过 |
| Python 环境 | conda 已安装；各项目使用独立 venv/conda 环境管理依赖 |
| C/C++ | `gcc`、`g++`、`make`、`cmake` 已安装并通过检查 |
| 编辑器 | VS Code 官方版，已安装 Python、C/C++、Remote 开发插件 |
| 版本控制 | Git 已配置身份；个人仓库已有 6 次有意义的 M0-2 提交 |
| 远程登录工具 | `ssh`、`scp`、`ssh-keygen`、`rsync` 已安装；SSH 公钥已生成 |
| 网络代理 | VMware 通过宿主机 `192.168.17.1:7897` 访问外网 |
| WSL2 备选环境 | Ubuntu 22.04.5 LTS，ROS2 Humble，实测 273 个 ROS2 包 |

> 注意：上述 `PASS=30 FAIL=0 WARN=2` 是 VMware 主环境在 2026-10-02 运行官方 `check_env.sh --fix` 的实际结果，不代表 Windows、WSL2 和 VMware 三套环境完全等价。

## 3. 四项任务完成情况

| 官方任务 | 状态 | 实际结果 |
| :--- | :---: | :--- |
| 1. 安装 Ubuntu、ROS2、Python 虚拟环境、C/C++、VS Code、Git | 已完成 | VMware 环境运行官方检查脚本后 `FAIL=0` |
| 2. 编写 README 和本机踩坑实录 | 已完成 | 本文档 |
| 3. 创建本地和云端 Git 仓库，并按模块、题目组织 | 已完成 | 本地仓库与 GitHub `origin/main` 已同步，目录包含 `M0/M0-1` 和 `M0/M0-2` |
| 4. 学会 SSH、SCP/rsync 和 SSH Key 远程操作 | 工具已准备，实操待完成 | 公钥已生成，但 `known_hosts` 为空，尚未真实登录开发板或服务器 |

## 4. 验收证据

### 4.1 官方环境检查

将官方 `check_env.sh` 临时放入 `M0/M0-1/` 后，在个人仓库根目录运行：

```bash
bash M0/M0-1/check_env.sh --fix
```

实际摘要：

```text
汇总: PASS=30  FAIL=0  WARN=2
环境验收: 通过（WARN 项请现场向考官说明）
下一步: 登录开发板完成 M0-2
```

两个 WARN 均已保留，没有通过伪造文件消除：

1. `known_hosts` 为空：工具和公钥已经准备好，但尚未连接真实开发板或服务器。
2. 官方仓库使用 `round1/M0/...`，而检查脚本期望个人仓库根目录直接使用 `M0/...`。本 README 已推送到个人仓库的 `M0/M0-1/`；重新运行检查脚本后可验证该结构警告是否消失。

### 4.2 系统和工具链

```bash
lsb_release -a
```

预期能看到：

```text
Distributor ID: Ubuntu
Release:        22.04
```

逐项检查：

```bash
for tool in bash git gcc g++ make cmake python3 pip3 code ssh scp ssh-keygen rsync; do
  command -v "$tool"
done

gcc --version | head -n 1
g++ --version | head -n 1
cmake --version | head -n 1
python3 --version
python3 -m pip --version
```

验收时以上基础工具均由 `check_env.sh` 判定为可用。

### 4.3 C/C++ 编译验证

```bash
cat > /tmp/m0-1-hello.cpp <<'CPP'
#include <iostream>

int main() {
    std::cout << "M0-1 C++ environment OK" << std::endl;
    return 0;
}
CPP

g++ /tmp/m0-1-hello.cpp -o /tmp/m0-1-hello
/tmp/m0-1-hello
```

预期输出：

```text
M0-1 C++ environment OK
```

### 4.4 ROS2 Humble

VMware 主环境：

```bash
source /opt/ros/humble/setup.bash
ros2 --version
ros2 pkg list | head
```

WSL2 备选环境另做过完整验证：

```text
ros2 pkg list | wc -l  ->  273

talker   -> Publishing: 'Hello World: 1' ... 'Hello World: 10'
listener -> I heard: [Hello World: 5] ... [Hello World: 10]
```

这说明 ROS2 本身、Python/C++ 示例节点和节点间通信均可运行。

### 4.5 VS Code 和插件

```bash
code --version
code --list-extensions --show-versions
```

在 VMware Ubuntu 22.04.5（主机名 `regalem`）实测：

```text
$ code --version
1.139.1

# 必需插件检测结果
OK    ms-python.python
OK    ms-vscode.cpptools
OK    ms-vscode-remote.remote-wsl
OK    ms-vscode-remote.remote-ssh
结果：4 个必需插件全部已安装
```

四个必要插件全部存在：

| 插件 ID | 作用 | 状态 |
| :-- | :-- | :--: |
| `ms-python.python` | Python 语言支持 | ✅ |
| `ms-vscode.cpptools` | C/C++ 语言支持与调试 | ✅ |
| `ms-vscode-remote.remote-wsl` | Remote - WSL | ✅ |
| `ms-vscode-remote.remote-ssh` | Remote - SSH | ✅ |

必要插件包括：

```bash
code --install-extension ms-python.python
code --install-extension ms-vscode.cpptools
code --install-extension ms-vscode-remote.remote-wsl
code --install-extension ms-vscode-remote.remote-ssh
```

VMware 验收时相关插件检查通过。VS Code 在 Ubuntu 虚拟机中使用的是官方 Linux 构建。

### 4.6 Git 和 Python 环境

```bash
git --version
git config --global user.name
git config --global user.email
git log --oneline --decorate
```

个人仓库最初有 6 次 M0-2 提交：

```text
6ef5d62 docs: document usage input format and output meaning
86a6403 test: cover correlation and invalid input cases
c19fd00 feat: add CLI validation and readable error handling
1578f39 fix: correct Pearson coefficient and reject zero variance
fbe0e6d refactor: extract config and CSV loading into functions
a40a81b chore: import M0-2 starter files
```

Python 依赖不写入系统环境，项目内按需创建隔离环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

ROS2 的 Python 包与 Ubuntu 系统 Python 版本绑定。学习 ROS2 节点时不把 ROS2 安装进普通 venv；需要独立依赖时，使用 `/usr/bin/python3` 创建虚拟环境，并按任务需要选择 `--system-site-packages`。

## 5. 本机踩坑实录

### 5.1 GitHub 直连失败、网页只有文字

- **现象**：`github.com`、`raw.githubusercontent.com` 和部分 GitHub CDN 请求超时或被 SSL 重置；浏览器打开后只有文字，CSS 和头像没有加载。
- **定位**：同一网络下清华 TUNA、Gitee、微软商店可访问，只有 GitHub 相关域名失败。
- **解决**：使用本地 Clash 代理，并给 Git 单独配置 GitHub 代理；软件源改用 TUNA，ROS2 公钥改用 Gitee，`rosdep` 使用国内的 `rosdepc`。
- **验证**：`git ls-remote` 能取得 GitHub 引用，国内镜像的软件包索引可以正常下载。

GitHub 专项代理配置：

```bash
git config --global http.https://github.com/.proxy http://127.0.0.1:7897
git config --global https.https://github.com/.proxy http://127.0.0.1:7897
```

### 5.2 双系统、WSL2 和 VMware 的路线选择

- **初始方案**：准备 Ubuntu ISO、缩小 Windows 分区、制作启动 U 盘，准备安装双系统。
- **问题**：双系统需要重启切换，开发资料、浏览器和聊天环境不能同时使用；WSL2 又存在 NAT 代理和硬件接入限制。
- **最终选择**：保留已经验证过的 WSL2，同时搭建 VMware Ubuntu 22.04 作为主环境；不再继续双系统安装。
- **权衡**：WSL2 胜在轻量和快速；VMware 胜在完整桌面、网络和工具行为一致。若后续接 USB、雷达、串口或需要硬实时，再单独评估原生 Ubuntu 或设备直通。

### 5.3 WSL 安装后必须重启

- **现象**：启用 WSL 和虚拟机平台后，导入 Ubuntu 报 `HCS_E_SERVICE_NOT_AVAILABLE`。
- **原因**：Windows 功能修改需要重启后，底层 HCS 服务才会启动。
- **解决**：重启 Windows 后重新导入 Ubuntu 22.04。
- **验证**：`wsl -l -v` 显示 `Ubuntu-22.04`、`Running`、版本 `2`。

### 5.4 在 Linux 内再次执行 `wsl`

- **现象**：进入 Ubuntu 后执行 `wsl -d Ubuntu-22.04`，提示 `Command 'wsl' not found`。
- **原因**：提示符已经是 `root@Regalem:...#`，说明当前就在 WSL Linux 内；`wsl` 是 Windows 侧的启动命令。
- **解决**：从 Windows PowerShell 执行 `wsl -d Ubuntu-22.04`；在 Ubuntu 内执行 `exit` 返回 Windows。

### 5.5 WSL NAT 模式的 localhost 代理警告

- **现象**：

```text
wsl: 检测到 localhost 代理配置，但未镜像到 WSL。
NAT 模式下的 WSL 不支持 localhost 代理。
```

- **原因**：Windows 代理监听 `127.0.0.1`，WSL 的 NAT 网络看不到 Windows 的 loopback。
- **解决**：该警告不影响 ROS2。需要代理时可配置 WSL 镜像网络或 `autoProxy`；本项目后续主要使用 VMware，因此没有依赖这项配置。

### 5.6 VMware NAT、DNS 和 VS Code Marketplace 超时

- **现象**：Ubuntu 虚拟机中 `marketplace.visualstudio.com` 解析失败或连接超时，VS Code 安装插件一直停在 `begin POST`。
- **定位**：Windows 主机的 `VMware NAT Service` 停止运行，虚拟机没有可用的 NAT 网关；恢复网络后，VS Code 又受到遗留代理设置影响。
- **解决**：把 VMware NAT Service 启动并设为自动启动；Ubuntu 内使用宿主机 VMware NAT 地址 `192.168.17.1:7897`，不要填写 `127.0.0.1`；必要时先用 `code --no-proxy-server` 排除错误代理。
- **验证**：`getent`、`curl` 和 Marketplace 请求恢复成功，VS Code 插件可以正常安装。

代理环境变量示例：

```bash
export HOST_IP=192.168.17.1
export PORT=7897
export http_proxy="http://$HOST_IP:$PORT"
export https_proxy="http://$HOST_IP:$PORT"
export all_proxy="socks5://$HOST_IP:$PORT"
export no_proxy="localhost,127.0.0.1,::1"
```

### 5.7 ROS2 国内镜像和错误 GPG 文件

- **现象**：官方 ROS2 源和 GitHub 公钥下载不稳定；有一次下载到的 `ros.key` 实际是 HTML 页面。
- **定位**：直连 `packages.ros.org` 和 GitHub 受限。
- **解决**：Ubuntu apt 使用清华 TUNA，ROS2 apt 使用清华镜像，GPG 公钥使用鱼香 ROS 提供的 Gitee 地址，`rosdep` 使用 `rosdepc`。
- **验证**：ROS2 Humble 安装完成，`ros2` 命令可用，WSL2 上实测 273 个包和 talker/listener 通信通过。

### 5.8 apt 锁和 `sudo` 作用范围

- **错误命令**：

```bash
sudo apt update && apt upgrade -y
```

- **原因**：`sudo` 只作用于 `apt update`，后面的 `apt upgrade` 仍以普通用户执行，因此报：

```text
Could not open lock file /var/lib/dpkg/lock-frontend ... Permission denied
```

- **解决**：

```bash
sudo apt update
sudo apt upgrade -y
```

或写成：

```bash
sudo bash -c 'apt update && apt upgrade -y'
```

- **补充**：曾把 `python3` 拼成 `pyhton3`，apt 因此提示无法定位软件包。包名必须准确。

### 5.9 conda 配置错误

- **问题一**：把参数写成 `show_channel-urls`，报 `CondaKeyError`。正确键名是下划线：

```bash
conda config --set show_channel_urls true
conda config --show show_channel_urls
```

- **问题二**：镜像域名把 `mirrors` 写成了 `morrors`，导致索引请求失败。正确域名是：

```text
mirrors.tuna.tsinghua.edu.cn
```

- **问题三**：创建环境时漏掉 `-n/--name`，conda 把环境名当成普通参数。正确写法：

```bash
conda create -n py311 python=3.11 -y
conda activate py311
```

### 5.10 Python 虚拟环境和 ROS2 的边界

- Windows `.venv`、WSL2 和 VMware 是三个不同的运行环境，同名 `.venv` 不代表依赖互通。
- ROS2 Humble 在 Ubuntu 22.04 上使用系统 Python 3.10，`rclpy` 和 `cv_bridge` 等包与对应 Python 版本绑定。
- 普通 Python 项目使用项目内 venv；ROS2 工作空间使用 `source /opt/ros/humble/setup.bash` 的 overlay 机制。
- 如果独立 venv 必须同时看到 ROS2 或 apt 安装的 OpenCV，应明确使用系统 Python，并在必要时加 `--system-site-packages`。

## 6. 复现与复核清单

在虚拟机中按顺序执行：

```bash
# 1. 系统和工具链
lsb_release -a
git --version
gcc --version
g++ --version
make --version
cmake --version
python3 --version
python3 -m pip --version

# 2. conda 或 uv
conda --version
# 或
uv --version

# 3. ROS2
source /opt/ros/humble/setup.bash
ros2 --version

# 4. VS Code
code --version
code --list-extensions

# 5. 远程工具
ssh -V
command -v scp
command -v rsync

# 6. Git
git config --global user.name
git config --global user.email
git rev-parse --show-toplevel
git log --oneline
```

最后使用官方脚本验收，必须得到：

```text
FAIL=0
环境验收: 通过
```

## 7. Git 上传记录与待办

Git 上传已完成：

- GitHub 仓库：https://github.com/regalem/22SmartCar-M0-2-
- 远端：`origin` 指向该仓库
- 分支：`main` 跟踪 `origin/main`
- 远端文件：`M0/M0-1/README.md`

剩余待办：

1. 使用已经生成的 SSH 公钥登录真实开发板或服务器，完成 M0-1 第 4 项：

   ```bash
   ssh-keygen -t ed25519 -C "you@example.com"
   ssh <用户名>@<开发板或服务器IP>
   scp <本地文件> <用户名>@<主机>:<远端目录>
   rsync -av <本地目录>/ <用户名>@<主机>:<远端目录>/
   ```

   首次连接应核对主机指纹并输入 `yes`，成功后检查：

   ```bash
   test -s ~/.ssh/known_hosts && echo "remote login evidence OK"
   ```

2. 在个人仓库根目录再次运行官方 `check_env.sh --fix`。官方脚本不应提交到个人仓库时，可临时放入 `M0/M0-1/`，验收完成后删除：

   ```bash
   bash M0/M0-1/check_env.sh --fix
   ```

3. 将最终验收输出、实际登录的开发板类型和连接日期追加到本文档。没有真实连接前，不伪造 `known_hosts`，也不把远程登录标记为已完成。

## 8. AI 使用说明

本项目使用 Codex 协助梳理 M0-1 要求、排查系统与网络问题、整理命令和起草本 README。关键环境结果均来自本机终端或 VMware Ubuntu 内实际运行的命令；`PASS=30 FAIL=0 WARN=2` 来自真实 `check_env.sh --fix` 输出。远程登录尚未完成，因此明确保留为待办。

## 9. 参考资料

- [官方 M0-1 README](https://github.com/Blake-John/22SmartCar/blob/main/round1/M0/M0-1/README.md)
- [官方 check_env.sh](https://github.com/Blake-John/22SmartCar/blob/main/round1/M0/M0-1/check_env.sh)
- [ROS2 Humble 官方文档](https://docs.ros.org/en/humble/)
- [鱼香 ROS 社区](https://fishros.org.cn/forum/)
- [Ubuntu 22.04 LTS](https://releases.ubuntu.com/22.04/)
- [Git 官方文档](https://git-scm.com/book/zh/v2)
- [Conda 文档](https://docs.conda.io/)
- [uv 文档](https://docs.astral.sh/uv/)
- [VS Code 文档](https://code.visualstudio.com/docs)
- [清华 TUNA 镜像](https://mirrors.tuna.tsinghua.edu.cn/)
