#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sensor_analyzer.py —— 传感器数据清洗与统计工具

用途：
    读取 CSV（列：time, value），计算 value 的均值与标准差，
    按 |value - mean| > 2 * std 剔除离群值（同时剔除偏大和偏小），
    把清洗后的数据写出为 cleaned_data.csv，并打印统计摘要。

用法：
    python3 sensor_analyzer.py --input sensor_data.csv --output cleaned_data.csv
    python3 sensor_analyzer.py   # 默认读写当前目录下的 sensor_data.csv / cleaned_data.csv
"""

import argparse
import csv
import math
import os
import sys

TIME_COL = "time"
VALUE_COL = "value"


def load_data(path, time_col=TIME_COL, value_col=VALUE_COL):
    """读取 CSV，返回 (times, values) 两个等长列表。

    文件不存在、为空、缺少列、行内有非数值内容时，抛带说明的 ValueError，
    由 main 统一捕获转成可读错误，不向用户抛栈回溯。
    """
    if not os.path.exists(path):
        raise ValueError("输入文件不存在: %s" % path)

    times = []
    values = []
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("输入文件为空: %s" % path)
        missing = [c for c in (time_col, value_col) if c not in reader.fieldnames]
        if missing:
            raise ValueError(
                "输入文件缺少列 %s（实际表头: %s）"
                % (", ".join(missing), ",".join(reader.fieldnames))
            )
        for lineno, row in enumerate(reader, start=2):
            try:
                t = float(row[time_col])
                v = float(row[value_col])
            except (TypeError, ValueError):
                raise ValueError("第 %d 行存在非数值内容: %r" % (lineno, row))
            times.append(t)
            values.append(v)

    if not values:
        raise ValueError("输入文件没有数据行: %s" % path)
    return times, values


def mean_and_std(values):
    """返回 (mean, std)，std 为总体标准差（除以 n）。"""
    n = len(values)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    return mean, math.sqrt(variance)


def remove_outliers(times, values, mean, std, k=2.0):
    """按 |value - mean| > k*std 剔除离群值，返回 (times, values, n_removed)。"""
    kept_times = []
    kept_values = []
    for t, v in zip(times, values):
        if abs(v - mean) <= k * std:
            kept_times.append(t)
            kept_values.append(v)
    return kept_times, kept_values, len(values) - len(kept_values)


def write_cleaned(path, times, values):
    """把清洗后的 (time, value) 写出为 CSV。"""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([TIME_COL, VALUE_COL])
        for t, v in zip(times, values):
            writer.writerow([t, v])


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="传感器数据清洗与统计（M0-3）")
    parser.add_argument(
        "--input",
        default="sensor_data.csv",
        help="输入 CSV 路径（默认：当前目录 sensor_data.csv）",
    )
    parser.add_argument(
        "--output",
        default="cleaned_data.csv",
        help="输出 CSV 路径（默认：当前目录 cleaned_data.csv）",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    print("=== 传感器数据分析 ===")
    try:
        times, values = load_data(args.input)
        mean, std = mean_and_std(values)
        kept_times, kept_values, n_removed = remove_outliers(times, values, mean, std)
        write_cleaned(args.output, kept_times, kept_values)
    except (ValueError, OSError) as exc:
        print("错误: %s" % exc, file=sys.stderr)
        return 2

    print("共读取 %d 条数据" % len(values))
    print("均值 mean = %.4f" % mean)
    print("标准差 std = %.4f" % std)
    print("剔除离群值 %d 条" % n_removed)
    print("清洗后剩余 %d 条" % len(kept_values))
    print("已保存到 %s" % os.path.abspath(args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())