# M0-2 ｜ 首个代码工具

本项目把官方提供的原始脚本 `legacy_corr.py` 重构为一个可维护的命令行工具。
现在入口文件是 `corr_tool.py`，它会读取 YAML 配置和 CSV 数据，计算两列数据的
Pearson 相关系数。

## 修复内容

- 将配置读取、CSV 读取、相关性计算拆分为独立函数。
- 修正 Pearson 相关系数公式，分母使用 `sqrt(sum_x2 * sum_y2)`。
- 检测空文件、缺少列、非数值、样本不足和零方差。
- 增加 `if __name__ == "__main__"` 保护。
- 增加 `--config` 参数和位置参数两种调用方式。
- 异常情况下输出可读错误并以非零状态码退出，不打印 Python traceback。
- 增加单元测试，覆盖正相关、负相关、零方差、缺列和 CLI 输出。

## 环境准备

建议使用虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 运行方式

显式指定配置文件：

```bash
python3 corr_tool.py --config config.yaml
```

使用位置参数：

```bash
python3 corr_tool.py config.yaml
```

示例输出：

```text
n = 40
mean_x = 49.515
mean_y = 43.201
r = 0.8321
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