# M0-4 ｜ Mini 项目实战：TaskScheduler

> **难度**：★★★★
> **综合考察**：结构化项目管理、依赖调度（拓扑排序）、日志工程、CLI 设计、文档写作
> **本题分值权重**：40（M0 总分 100 分中的 40 分）
> **运行环境**：纯终端，不依赖 ROS / GUI

---

## 1. 任务概述

比赛时小车要按顺序做多个任务（先巡线、再避障、最后停车）。
M0-4 要求用 Python 写一个**命令行任务调度模拟器** `TaskScheduler`，
把“任务状态管理”和“时间监控”抽象成代码。

### 1.1 官方要求逐条对照表

| # | 官方要求 | 实现位置 | 状态 |
| :-: | :-- | :-- | :-: |
| 1 | 读取 `tasks.yaml` / `tasks.json`，含 5~8 个任务 | `load_config()` / `parse_tasks()` | ✅ |
| 1.1 | 每个任务含 `name` / `duration` / `success_rate` / `dependencies` | `parse_tasks()` | ✅ |
| 1.2 | 可选全局 `timeout` | `parse_timeout()` | ✅ |
| 2.1 | 按依赖顺序执行（拓扑排序） | `topological_order()`（Kahn 算法） | ✅ |
| 2.2 | 正确处理**分叉 / 汇合** | 邻接表 + 入度表，稳定出队 | ✅ |
| 2.3 | 检测**依赖环**并报错 | `topological_order()` 尾部校验 | ✅ |
| 2.4 | 按 `success_rate` 随机判定成败 | `random.Random(seed).random()` | ✅ |
| 2.5 | 失败**最多重试 2 次**（≤3 次尝试） | `MAX_ATTEMPTS = 3` | ✅ |
| 2.6 | 仍失败记为 `SKIPPED` | `run_scheduler()` 的 else 分支 | ✅ |
| 2.7 | 继续执行**不依赖它**的任务 | 依赖检查只查前置，不影响无关分支 | ✅ |
| 2.8 | 下游任务标记为 `SKIPPED`（非成功） | `bad_deps` 检查 | ✅ |
| 2.9 | 开始时记真实时间，逐任务 `sleep(duration)` 并累加 | `time.monotonic()` + `time.sleep()` | ✅ |
| 2.10 | 超时**立即终止**并输出 `TIMEOUT` | 执行前 + 每次 sleep 后两次判定 | ✅ |
| 3.1 | 控制台实时彩色输出（4 种颜色） | `ANSI_COLORS` + `log()`（`flush=True`） | ✅ |
| 3.2 | 生成 `report.json`：状态 / 总耗时 / 是否超时 | `write_report()` | ✅ |
| 4.1 | **必须使用虚拟环境** | 见第 3 节（venv 用法） | ✅ |
| 4.2 | 提供 `requirements.txt` | `requirements.txt`（PyYAML） | ✅ |
| 4.3 | README：参数说明 + **≥3 个运行示例** | 第 5、6 节（5 个示例） | ✅ |
| 5 | 交付 `scheduler.py` / `*.py` / `requirements.txt` / `README.md` / `report.json` | 见第 2 节目录树 | ✅ |
| 6.1 | CLI：`--config`（必填）/ `--timeout` / `--report` / `--seed` | `build_parser()` | ✅ |
| 6.2 | `report.json` 结构（`timeout`/`total_duration`/`tasks[]`） | `run_scheduler()` 返回值 | ✅ |
| 6.3 | `status` 取值 ∈ {SUCCESS, FAILED, SKIPPED, TIMEOUT} | `VALID_STATUS` | ✅ |
| 6.4 | `attempts` 为整数且**不超过 3** | 单测 `test_failure_retries_then_skipped` | ✅ |
| 6.5 | `tasks` 含**每一个**任务（含跳过与超时未执行） | 超时后统一补记 | ✅ |
| 7 | 异常输入可读报错 + 非 0 退出 + **无栈回溯** | 全部经 `SchedulerError` 捕获 | ✅ |
| 7.1 | 依赖成环 / 依赖不存在 / 空任务列表 / `success_rate` 越界 | 见第 10 节异常表 | ✅ |
| 7.2 | YAML/JSON 语法错误 / 文件不存在 | `load_config()` | ✅ |
| 8 | 彩色输出在**非 TTY 降级** | `resolve_color()` | ✅ |

---

## 2. 项目结构（交付物）

```text
M0/M0-4/
├── scheduler.py                  # 主程序（唯一入口，python3 scheduler.py 运行）
├── requirements.txt              # 依赖清单（PyYAML>=6.0，可选：没它也能用 YAML）
├── README.md                     # 本文档：参数说明 + 5 个运行示例
├── tasks_demo.yaml               # 示例配置（YAML）
├── tasks_demo.json               # 示例配置（JSON，与 YAML 等价）
├── report.json                   # 一次真实运行产生的报告样例（seed=0，全部成功）
└── tests/
    ├── test_scheduler.py         # 调度逻辑单元测试（17 个用例）
    └── test_yaml_fallback.py     # 内置 YAML 后备解析器测试（10 个用例）
```

---

## 3. 环境准备：虚拟环境（venv）的用法【重点】

M0-4 明确要求**必须使用虚拟环境**，用来证明你会用 M0-1 里装好的环境。
虚拟环境把本项目依赖装在一个独立目录里，不污染系统 Python，
也不会和 ROS2 / conda 环境互相打架。

> M0-1 的主环境是 VMware 里的 Ubuntu 22.04，本节以 **Linux/Ubuntu** 为准；
> 3.8 附 Windows PowerShell 的等价写法。

### 3.1 创建虚拟环境

```bash
cd ~/桌面/M0-4             # 进入本项目目录（换成你的实际路径）
python3 -m venv .venv      # 用系统 Python 在 .venv/ 下创建独立环境
```

- `python3 -m venv` 是标准库自带命令，**不需要额外安装**。
- `.venv` 是约定俗成的目录名（`.gitignore` 已忽略，不会被提交）。
- 创建后目录里有独立的 `python`、`pip`，与系统 Python 隔离。

### 3.2 激活虚拟环境

```bash
source .venv/bin/activate
```

激活成功后提示符前会出现 `(.venv)`。确认“现在用的是谁”：

```bash
which python        # 应指向 .../M0-4/.venv/bin/python
python -V
```

### 3.3 安装依赖

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

- 用 `python -m pip` 而不是裸 `pip`，确保装进**当前虚拟环境**。
- 国内网络慢或超时（`Connection timed out`），换清华源：

```bash
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
pip install -r requirements.txt
```

- 验证：

```bash
python -c "import yaml; print('PyYAML', yaml.__version__)"
```

### 3.4 运行程序

```bash
python scheduler.py --config tasks_demo.yaml --timeout 15 --report report.json --seed 42
```

### 3.5 退出虚拟环境

```bash
deactivate
```

提示符前的 `(.venv)` 消失，表示已回到系统 Python。

### 3.6 删除 / 重建（可选）

```bash
rm -rf .venv               # 删掉整个环境
python3 -m venv .venv      # 需要时再重建
```

虚拟环境“用完即弃”，删掉不影响代码，重建后重新 `pip install -r requirements.txt` 即可。

### 3.7 不激活也能运行（CI / 脚本里常用）

```bash
.venv/bin/python scheduler.py --config tasks_demo.yaml --seed 42
```

直接调用环境里的解释器，效果与“激活后再 `python`”完全一致。

### 3.8 Windows PowerShell 等价写法（本机备选）

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1     # 若报执行策略错误：Set-ExecutionPolicy -Scope Process RemoteSigned
pip install -r requirements.txt
python scheduler.py --config tasks_demo.yaml --seed 42
deactivate
```

### 3.9 常见坑

| 现象 | 原因 / 解决 |
| :-- | :-- |
| `ModuleNotFoundError: No module named 'yaml'` | 见 3.10：换 JSON 配置，或用 `--system-site-packages` 重建 venv |
| `pip` 装到了系统里 | 用了裸 `pip`：改成 `python -m pip install -r requirements.txt` |
| `.venv/bin/activate: No such file` | 环境建在别的目录：确认 `cd` 到了 `M0-4`，或路径不叫 `.venv` |
| Windows 下 `Activate.ps1` 被拒绝 | 执行策略限制，见 3.8 |
| 和 ROS2 混用 | ROS2 用 overlay（`source /opt/ros/humble/setup.bash`），普通 Python 项目用它自己的 venv，两者不要互相 `source` |

### 3.10 装不上 PyYAML 怎么办（内网 / 无代理时）

本程序对 PyYAML 是**可选依赖**，有三条退路，任选其一即可跑通全部要求：

**退路 1（最省事）：用 JSON 配置，完全不需要 PyYAML**

```bash
python scheduler.py --config tasks_demo.json --timeout 15 --report report.json --seed 42
```

**退路 2：直接跑 YAML——没装 PyYAML 时自动启用内置后备解析器**

`scheduler.py` 里内置了一个最小 YAML 解析器，支持本任务配置用到的语法
（`key: value`、行内列表 `[a, b]`、`- key: value` 形式的映射列表、`#` 注释、
`---` 文档分隔符）。所以下面这条命令在**没装 PyYAML** 的机器上也能跑：

```bash
python scheduler.py --config tasks_demo.yaml --timeout 15 --report report.json --seed 42
```

**退路 3：借用系统 / conda 里已有的 PyYAML**

有些 Anaconda 发行版自带 PyYAML。用 `--system-site-packages` 建 venv 就能继承：

```bash
python -c "import yaml; print(yaml.__version__)"     # 先确认系统/base 里有
rm -rf .venv
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -c "import yaml; print('PyYAML', yaml.__version__)"
python scheduler.py --config tasks_demo.yaml --seed 42
```

> 需要的 Linux 网络代理通常要设：
> `export http_proxy=http://<宿主机网关>:7897` 和 `export https_proxy=http://<宿主机网关>:7897`
> （VMware NAT 的网关可用 `ip route | grep default` 查到）。

---

## 4. 快速开始

### 4.1 在 VMware 的 Ubuntu 里从零跑通（复制粘贴即可）

```bash
# 1) 进入项目目录
cd ~/桌面/M0-4

# 2) 建并激活虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 3) 装依赖（装不上就跳过；见 3.10，YAML 有内置后备解析器）
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 4) 跑！
python scheduler.py --config tasks_demo.yaml --timeout 15 --report report.json --seed 42

# 5) 跑测试
python -m unittest discover -s tests -v
```

期望输出（结尾）：

```text
[ 11.00s] SUCCESS ReturnHome (attempts=1, 2.50s)
报告已写入: /home/.../M0-4/report.json
```

### 4.2 三行版

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scheduler.py --config tasks_demo.yaml --timeout 15 --report report.json --seed 42
```

---

## 5. 参数说明

| 参数 | 必填 | 默认 | 说明 |
| :-- | :--: | :-- | :-- |
| `--config <path>` | **是** | — | 任务配置文件，支持 `.yaml` / `.yml` / `.json` |
| `--timeout <float>` | 否 | 配置文件里的 `timeout` | **覆盖**配置文件中的全局超时（秒）；两者都没有则不超时 |
| `--report <path>` | 否 | `report.json` | 报告输出路径（会自动创建父目录） |
| `--seed <int>` | 否 | 无（真随机） | 随机种子，便于**复现**同一结果 |
| `--no-color` | 否 | 关 | 关闭彩色输出 |
| `--color` | 否 | 关 | 强制彩色（即使输出不是 TTY） |

**退出码**：`0` = 正常运行结束（含“因超时终止”，此时报告 `timeout=true`）；
`2` = 配置 / 数据 / 文件错误。

---

## 6. 运行示例（5 个，均实测）

### 示例 1：标准运行（YAML + 种子，可复现）

```bash
python scheduler.py --config tasks_demo.yaml --timeout 15 --report report.json --seed 0
```

实测输出（`report.json` 即由这条命令产生）：

```text
[  0.50s] SUCCESS Init (attempts=1, 0.50s)
[  3.00s] SUCCESS Navigate (attempts=1, 2.50s)
[  4.50s] SUCCESS DetectQR (attempts=1, 1.50s)
[  5.50s] SUCCESS Grasp (attempts=1, 1.00s)
[  7.50s] SUCCESS AvoidObstacle (attempts=1, 2.00s)
[  8.50s] SUCCESS Place (attempts=1, 1.00s)
[ 11.00s] SUCCESS ReturnHome (attempts=1, 2.50s)
报告已写入: /.../M0/M0-4/report.json
```

### 示例 2：JSON 配置 + 自定义报告路径

```bash
python scheduler.py --config tasks_demo.json --report out/report.json --seed 1
```

`tasks_demo.json` 与 `tasks_demo.yaml` **内容等价**（有单测保证），
报告写到 `out/report.json`，父目录会自动创建。

### 示例 3：超时中断（`--timeout 5`）

```bash
python scheduler.py --config tasks_demo.yaml --timeout 5 --report report_timeout.json --seed 0
```

实测输出：

```text
[  0.50s] SUCCESS Init (attempts=1, 0.50s)
[  3.00s] SUCCESS Navigate (attempts=1, 2.50s)
[  4.50s] SUCCESS DetectQR (attempts=1, 1.50s)
[  5.50s] TIMEOUT Grasp (执行 1.00s 后超时)
[  5.50s] TIMEOUT 总耗时超时，已终止后续任务
报告已写入: report_timeout.json
```

`Grasp` 睡满 1.0s 后累计 5.5s > 5s，**sleep 之后立即检查**触发超时；
尚未执行的 `AvoidObstacle` / `Place` / `ReturnHome` 在报告里也被记为 `TIMEOUT`。

### 示例 4：失败重试 + 下游跳过（`--seed 42`）

```bash
python scheduler.py --config tasks_demo.yaml --seed 42
```

实测输出（彩色环境下 `FAILED` 红、`RETRY` 黄、`SKIPPED` 蓝）：

```text
[  7.50s] FAILED AvoidObstacle (第 1 次尝试失败)
[  7.50s] RETRY AvoidObstacle (重试 1/2)
[  9.50s] FAILED AvoidObstacle (第 2 次尝试失败)
[  9.50s] RETRY AvoidObstacle (重试 2/2)
[ 11.51s] FAILED AvoidObstacle (第 3 次尝试失败，重试用尽)
[ 11.51s] SKIPPED AvoidObstacle (attempts=3 均失败，跳过)
[ 11.51s] SKIPPED Place (依赖未成功: AvoidObstacle)
[ 11.51s] SKIPPED ReturnHome (依赖未成功: Place)
```

`AvoidObstacle` 3 次全失败 → `SKIPPED`；依赖它的 `Place` → `SKIPPED`；
`ReturnHome` 又依赖 `Place` → 继续 `SKIPPED`（**失败沿依赖链传播**）。
与失败分支**无关**的任务仍会照常执行。

### 示例 5：命令行覆盖配置里的 timeout

```bash
python scheduler.py --config tasks_demo.yaml --timeout 30 --seed 0
```

命令行 `--timeout` 优先于配置文件的 `timeout: 15`。

---

## 7. 配置文件格式

```yaml
timeout: 15                  # 可选：全局超时（秒）

tasks:
  - name: "Navigate"         # 必填：任务名（唯一）
    duration: 2.5            # 必填：预期耗时（秒，程序 sleep 这么久）
    success_rate: 0.8        # 必填：模拟成功率，0.0 ~ 1.0
    dependencies: ["Init"]   # 可选：前置任务名列表（默认 []）
```

- `dependencies` 出现不存在的任务名 → 报错退出（见第 10 节）。
- 依赖构成环 → 报错退出（拓扑排序时检测）。
- 同名任务 → 报错退出。

---

## 8. 报告 `report.json` 结构

```json
{
  "timeout": false,
  "total_duration": 11.003,
  "tasks": [
    {
      "name": "Init",
      "status": "SUCCESS",
      "attempts": 1,
      "duration": 0.5,
      "started_at": 1791367103.01,
      "ended_at": 1791367103.51
    }
  ]
}
```

| 字段 | 含义 |
| :-- | :-- |
| `timeout` | 布尔值，本次运行是否发生超时中断 |
| `total_duration` | 程序实际总耗时（秒，`time.monotonic` 测量） |
| `tasks[].name` | 任务名 |
| `tasks[].status` | `SUCCESS` / `FAILED` / `SKIPPED` / `TIMEOUT` |
| `tasks[].attempts` | 实际尝试次数，整数，**不超过 3** |
| `tasks[].duration` | 该任务累计实际耗时（秒） |
| `tasks[].started_at` / `ended_at` | 开始 / 结束的绝对时间戳（epoch 秒）；未执行时为 `null` |

`tasks` **包含配置文件里的每一个任务**（含被跳过的、超时未执行的），
顺序与配置文件一致，不会漏项。

---

## 9. 调度语义（设计说明）

### 9.1 状态含义

| 状态 | 何时出现 |
| :-- | :-- |
| `SUCCESS` | 某次尝试随机判定成功，任务完成 |
| `FAILED` | **单次尝试**失败时的实时日志（红）；也是报告里的合法取值之一 |
| `RETRY` | 失败后还有重试机会时的实时日志（黄） |
| `SKIPPED` | ① 3 次尝试全部失败（题目要求“仍失败则记录为 SKIPPED”）；② 任一前置任务不是 `SUCCESS`，自身不再执行 |
| `TIMEOUT` | 总耗时超过上限时，正在执行的任务与**尚未执行**的任务 |

> 依题目原文“若仍失败则跳过该任务（记录为 `SKIPPED`）”，把重试用尽的最终状态
> 记为 `SKIPPED`，并**沿依赖链传播**给下游；`FAILED` 用于表示单次尝试的失败日志。

### 9.2 三条关键规则

1. **拓扑排序**：Kahn 算法，同层按配置顺序稳定出队（结果可复现）；
   正确处理“一个任务被多个任务依赖（分叉）”和“一个任务依赖多个前置（汇合）”。
2. **依赖传播**：只要有一个前置不是 `SUCCESS`，当前任务直接 `SKIPPED`（尝试 0 次），
   但**不影响无关分支**。
3. **超时判定点**：每个任务**执行前**检查一次，每次 `sleep` **结束之后**再检查一次。
   这样最后一个任务“睡过了头”也能被立刻发现并终止。

---

## 10. 异常输入处理（实测，均无栈回溯）

| 异常输入 | 输出 | 退出码 |
| :-- | :-- | :--: |
| 文件不存在 | `错误: 配置文件不存在: nope.yaml` | 2 |
| 配置文件为空 / 只有注释 | `错误: 配置文件为空...` | 2 |
| YAML 语法错误 | `错误: YAML 语法错误: ...` | 2 |
| JSON 语法错误 | `错误: JSON 语法错误: ...` | 2 |
| 缺 `tasks` 字段 | `错误: 配置缺少 'tasks' 字段` | 2 |
| 空任务列表 | `错误: 任务列表为空：至少需要 1 个任务` | 2 |
| 任务名重复 | `错误: 任务名重复: A` | 2 |
| 缺 `duration` / `success_rate` | `错误: 任务 X 缺少 'duration'` | 2 |
| `success_rate` 越界（如 1.5） | `错误: 任务 X 的 'success_rate' 越界（应在 0.0~1.0 之间）: 1.5` | 2 |
| 依赖不存在的任务 | `错误: 任务 A 依赖了不存在的任务: Ghost` | 2 |
| 依赖成环 | `错误: 检测到依赖环，无法调度。涉及任务: A, B` | 2 |
| 依赖自己 | `错误: 任务 A 依赖了自己（自环）` | 2 |

实测示例：

```text
$ python scheduler.py --config bad_cycle.yaml
错误: 检测到依赖环，无法调度。涉及任务: A, B
$ echo $?
2
```

---

## 11. 测试

```bash
python -m unittest discover -s tests -v
```

共 **27 个用例**：

- `test_scheduler.py`（17 个）：拓扑分叉/汇合、稳定顺序、依赖环、缺失依赖、
  空任务列表、重名、`success_rate` 越界、全成功、重试用尽→`SKIPPED`、
  跳过沿依赖传播、无关分支继续执行、超时中断、报告包含全部任务、
  `attempts<=3`、种子可复现、YAML/JSON 等价、文件不存在。
- `test_yaml_fallback.py`（10 个）：内置后备解析器与 PyYAML 结果一致、
  标量类型、行内列表、块状 `dependencies`、注释、`---` 分隔符、
  含冒号的引号字符串、Tab 缩进可读报错、空文本报错。

实测：

```text
Ran 27 tests in 0.005s

OK
```

测试用可控时钟替换 `time.sleep`，因此**不会真的等待 11 秒**。

---

## 12. 彩色输出与非 TTY 降级

- 终端（TTY）：`SUCCESS` 绿、`FAILED` 红、`RETRY` 黄、`SKIPPED` 蓝（ANSI）。
- 输出被重定向到文件 / 管道，或设置了环境变量 `NO_COLOR` 时：自动去掉 ANSI 转义，
  避免文件里出现乱码转义符。
- 强制彩色加 `--color`，强制关闭加 `--no-color`。

---

## 13. AI 使用说明（如实说明）

- **使用范围**：使用 Codex 协助阅读官方 M0-4 说明、设计状态机与超时判定点、
  起草 `scheduler.py`、测试与本文档。
- **本人核对**：每一步都实际运行验证——`report.json` 由 seed=0 的真实运行产生；
  第 6 节 5 个示例输出与第 10 节异常输出均为本机终端实测结果。
- **独立校验**：拓扑排序、重试次数上限、超时中断、依赖跳过传播、YAML 后备解析
  都各写了单元测试，并用可复现的 `--seed` 复核结果。

---

## 14. 参考

- [官方 M0-4 README](https://github.com/Blake-John/22SmartCar/blob/main/round1/M0/M0-4/README.md)
- [Python venv 官方文档](https://docs.python.org/3/library/venv.html)
- [Python argparse 官方文档](https://docs.python.org/3/library/argparse.html)
- [Python time 官方文档](https://docs.python.org/3/library/time.html)
- [PyYAML 文档](https://pyyaml.org/wiki/PyYAMLDocumentation)
- [Kahn 拓扑排序](https://en.wikipedia.org/wiki/Topological_sorting)