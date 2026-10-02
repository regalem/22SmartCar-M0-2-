#!/usr/bin/env python3
"""Compute a Pearson correlation coefficient from a YAML configuration."""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path
from typing import Any, Sequence

import yaml


class CorrelationError(Exception):
    """Raised when the configuration or input data is invalid."""


def load_config(config_path: Path) -> tuple[Path, str, str]:
    """Load and validate the YAML configuration."""
    config_path = config_path.expanduser()

    if not config_path.exists():
        raise CorrelationError(f"配置文件不存在：{config_path}")
    if not config_path.is_file():
        raise CorrelationError(f"配置路径不是文件：{config_path}")

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise CorrelationError(f"无法读取配置文件：{config_path}") from exc
    except yaml.YAMLError as exc:
        raise CorrelationError(f"配置文件 YAML 格式错误：{exc}") from exc

    if not isinstance(raw, dict):
        raise CorrelationError("配置文件顶层必须是 YAML 映射")

    input_csv = raw.get("input_csv")
    columns = raw.get("columns")

    if not isinstance(input_csv, str) or not input_csv.strip():
        raise CorrelationError("配置项 input_csv 必须是非空字符串")
    if not isinstance(columns, dict):
        raise CorrelationError("配置项 columns 必须是映射")

    col_x = columns.get("x")
    col_y = columns.get("y")
    if not isinstance(col_x, str) or not col_x.strip():
        raise CorrelationError("配置项 columns.x 必须是非空字符串")
    if not isinstance(col_y, str) or not col_y.strip():
        raise CorrelationError("配置项 columns.y 必须是非空字符串")

    csv_path = Path(input_csv)
    if not csv_path.is_absolute():
        config_relative = config_path.parent / csv_path
        cwd_relative = Path.cwd() / csv_path
        if config_relative.exists():
            csv_path = config_relative
        elif cwd_relative.exists():
            csv_path = cwd_relative
        else:
            csv_path = config_relative

    return csv_path, col_x, col_y


def load_xy(csv_path: Path, col_x: str, col_y: str) -> tuple[list[float], list[float]]:
    """Read two numeric columns from a CSV file."""
    csv_path = csv_path.expanduser()

    if not csv_path.exists():
        raise CorrelationError(f"输入 CSV 不存在：{csv_path}")
    if not csv_path.is_file():
        raise CorrelationError(f"输入路径不是文件：{csv_path}")

    xs: list[float] = []
    ys: list[float] = []

    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames is None:
                raise CorrelationError("输入 CSV 为空，缺少表头")

            missing = [name for name in (col_x, col_y) if name not in reader.fieldnames]
            if missing:
                raise CorrelationError(
                    "输入 CSV 缺少列：" + ", ".join(missing)
                )

            for line_number, row in enumerate(reader, start=2):
                if row.get(col_x) is None or row.get(col_y) is None:
                    raise CorrelationError(f"CSV 第 {line_number} 行缺少数据")
                try:
                    xs.append(float(row[col_x]))
                    ys.append(float(row[col_y]))
                except (TypeError, ValueError) as exc:
                    raise CorrelationError(
                        f"CSV 第 {line_number} 行包含非数值数据"
                    ) from exc
    except csv.Error as exc:
        raise CorrelationError(f"CSV 格式错误：{exc}") from exc
    except OSError as exc:
        raise CorrelationError(f"无法读取 CSV：{csv_path}") from exc

    if len(xs) < 2:
        raise CorrelationError("至少需要两个有效数据点才能计算相关系数")

    return xs, ys


def pearson_correlation(xs: Sequence[float], ys: Sequence[float]) -> float:
    """Calculate Pearson's r using the covariance/variance definition."""
    if len(xs) != len(ys):
        raise CorrelationError("x 和 y 的数据数量不一致")
    if len(xs) < 2:
        raise CorrelationError("至少需要两个数据点")

    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    ss_x = 0.0
    ss_y = 0.0
    covariance = 0.0

    for x, y in zip(xs, ys):
        dx = x - mean_x
        dy = y - mean_y
        ss_x += dx * dx
        ss_y += dy * dy
        covariance += dx * dy

    if ss_x == 0.0 or ss_y == 0.0:
        raise CorrelationError("某一列方差为 0，相关系数没有定义")

    result = covariance / math.sqrt(ss_x * ss_y)
    return max(-1.0, min(1.0, result))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read a YAML config and calculate Pearson's r for two CSV columns."
    )
    parser.add_argument("config_pos", nargs="?", help="YAML 配置文件路径")
    parser.add_argument("--config", dest="config_opt", help="YAML 配置文件路径")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config_name = args.config_opt or args.config_pos
    if not config_name:
        parser.error("请通过 --config 或位置参数提供配置文件")

    try:
        csv_path, col_x, col_y = load_config(Path(config_name))
        xs, ys = load_xy(csv_path, col_x, col_y)
        n = len(xs)
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        r = pearson_correlation(xs, ys)
    except CorrelationError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"错误：文件操作失败：{exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"错误：未预期的失败：{exc}", file=sys.stderr)
        return 2

    print(f"n = {n}")
    print(f"mean_x = {mean_x}")
    print(f"mean_y = {mean_y}")
    print(f"r = {r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())