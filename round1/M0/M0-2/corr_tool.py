#!/usr/bin/env python3
"""M0-2 最小可验收版本：读 YAML 配置，算两列数据的 Pearson 相关系数。"""

import argparse
import csv
import math
import sys
from pathlib import Path

import yaml


def pearson(xs, ys):
    """手写 Pearson 相关系数（不调用 numpy），返回 [-1, 1]。"""
    n = len(xs)
    if n != len(ys) or n < 2:
        raise ValueError("数据点数量不足，或 x/y 长度不一致")

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    ss_x = ss_y = sp = 0.0
    for x, y in zip(xs, ys):
        dx = x - mean_x
        dy = y - mean_y
        ss_x += dx * dx          # Σ(x - x̄)²
        ss_y += dy * dy          # Σ(y - ȳ)²
        sp += dx * dy            # Σ(x - x̄)(y - ȳ)

    if ss_x == 0.0 or ss_y == 0.0:
        raise ValueError("某一列取值恒定，方差为 0，相关系数无定义")

    r = sp / math.sqrt(ss_x * ss_y)      # 关键修复：分母要开方
    return max(-1.0, min(1.0, r))        # 浮点误差钳位到 [-1, 1]


def read_config(path):
    """读 YAML，返回 (csv_path, x 列名, y 列名)。"""
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(cfg, dict):
        raise ValueError("配置文件顶层必须是 YAML 映射")

    csv_name = cfg.get("input_csv")
    cols = cfg.get("columns")
    if not isinstance(csv_name, str) or not isinstance(cols, dict):
        raise ValueError("配置缺少 input_csv 或 columns 字段")

    x_name, y_name = cols.get("x"), cols.get("y")
    if not isinstance(x_name, str) or not isinstance(y_name, str):
        raise ValueError("配置 columns 必须包含字符串 x 和 y")

    csv_path = Path(csv_name)
    if not csv_path.is_absolute():
        # 相对路径：优先相对配置文件所在目录，其次相对当前工作目录
        near_config = path.parent / csv_path
        near_cwd = Path.cwd() / csv_path
        if near_config.exists():
            csv_path = near_config
        elif near_cwd.exists():
            csv_path = near_cwd
        else:
            csv_path = near_config
    return csv_path, x_name, y_name


def read_xy(csv_path, x_name, y_name):
    """读 CSV 指定两列，转成两个 float 列表。"""
    if not csv_path.is_file():
        raise ValueError(f"输入 CSV 不存在：{csv_path}")

    xs, ys = [], []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV 为空或缺少表头")
        for col in (x_name, y_name):
            if col not in reader.fieldnames:
                raise ValueError(f"CSV 缺少列：{col}")
        for line_no, row in enumerate(reader, start=2):
            try:
                xs.append(float(row[x_name]))
                ys.append(float(row[y_name]))
            except (TypeError, ValueError):
                raise ValueError(f"CSV 第 {line_no} 行不是有效数值")

    if len(xs) < 2:
        raise ValueError("有效数据点少于 2 个")
    return xs, ys


def main(argv=None):
    parser = argparse.ArgumentParser(description="计算两列数据的 Pearson 相关系数")
    parser.add_argument("config_pos", nargs="?", help="YAML 配置文件路径")
    parser.add_argument("--config", dest="config_opt", help="YAML 配置文件路径")
    args = parser.parse_args(argv)

    config_name = args.config_opt or args.config_pos
    if not config_name:
        parser.error("请通过 --config 或位置参数提供配置文件")

    try:
        cfg_path = Path(config_name).expanduser()
        if not cfg_path.is_file():
            raise ValueError(f"配置文件不存在：{cfg_path}")
        csv_path, x_name, y_name = read_config(cfg_path)
        xs, ys = read_xy(csv_path, x_name, y_name)
        n, mean_x = len(xs), sum(xs) / len(xs)
        mean_y = sum(ys) / len(ys)
        r = pearson(xs, ys)
    except Exception as exc:                    # 统一收口，绝不抛 Traceback
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    print(f"n = {n}")
    print(f"mean_x = {mean_x}")
    print(f"mean_y = {mean_y}")
    print(f"r = {r}")                           # 验收契约行
    return 0


if __name__ == "__main__":
    sys.exit(main())
