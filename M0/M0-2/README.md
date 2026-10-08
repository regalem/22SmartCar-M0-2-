# M0-2 ｜ 首个代码工具

把官方原始脚本 `legacy_corr.py` 重构为一个可维护的命令行工具。入口文件是
`corr_tool.py`：读取 YAML 配置和 CSV 数据，**手写**计算两列数据的 Pearson 相关系数。

## 修复内容

对照 `legacy_corr.py`，本版本做了以下修改：

- 将配置读取、CSV 读取、相关系数计算拆分为独立函数，核心计算封在 `pearson()`。
- 修正 Pearson 相关系数公式：原脚本分母写成 `dx * dy`，漏了开方，正确应为
  `sqrt(Σ(x-x̄)² × Σ(y-ȳ)²)`（也就是 `math.sqrt(ss_x * ss_y)`）。
- 补充异常处理：文件不存在、空文件、列名不匹配、非数值、样本不足、某一列方差为 0。
- 增加 `if __name__ == "__main__"` 保护，被 import 时不会执行主流程。
- 增加 `--config` 参数，同时保留位置参数写法。
- 异常时输出可读错误到 stderr 并以非 0 退出码结束，不打印 Python traceback。
- 增加单元测试，覆盖正相关、负相关、零方差、缺列、空文件、非数值。

## 环境准备

建议使用虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 运行方式

```bash
python3 corr_tool.py --config config.yaml   # 验收方式
python3 corr_tool.py config.yaml            # 位置参数（可选）
```

对示例数据 `sample_data.csv` 的实际输出：

```text
n = 40
mean_x = 49.437825
mean_y = 43.310725000000005
r = 0.563474725452484
```

程序保证 stdout 中包含一行：

```text
r = <数值>
```

## YAML 格式

```yaml
input_csv: "sample_data.csv"

columns:
  x: "sensor_a"
  y: "sensor_b"
```

字段说明：

- `input_csv`：CSV 文件路径。
- `columns.x`：第一列列名。
- `columns.y`：第二列列名。

`input_csv` 如果是相对路径，会优先相对于 YAML 文件所在目录解析；如果该位置不存在，再尝试相对于当前工作目录解析。

## CSV 格式

CSV 必须包含表头，并包含 YAML 中指定的两列：

```csv
timestamp,sensor_a,sensor_b,note
2025-09-20T10:00:00,61.327,54.853,
```

指定列中的数据必须是可转换为 `float` 的数值。

## 输出含义

- `n`：参与计算的数据点数量。
- `mean_x`：第一列平均值。
- `mean_y`：第二列平均值。
- `r`：Pearson 相关系数，范围为 `[-1, 1]`。
  - `1`：完全正相关。
  - `0`：没有线性相关。
  - `-1`：完全负相关。

## 测试

```bash
python3 -m unittest discover -s tests -v
```

## 退出码

- `0`：计算成功。
- `2`：配置、CSV 或数据错误。

## AI 使用说明

本题使用 AI（Codex）协助定位 `legacy_corr.py` 中"分母漏开方"的公式错误、整理函数结构、
起草测试与本文档。核心计算 `pearson()` 经逐行核对，并与标准库 `statistics.correlation`
对照，差值约 1.1e-16（远小于验收容差 1e-6）。
