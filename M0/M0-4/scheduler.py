#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M0-4 TaskScheduler

命令行任务调度模拟器：读取 tasks.yaml / tasks.json，按依赖顺序（拓扑排序）
模拟执行任务，支持失败重试、依赖失败传播、超时中断、彩色实时日志，
并在运行结束后输出结构化报告 report.json。

纯终端运行，不依赖 ROS 或 GUI。

YAML 支持：
  - 装有 PyYAML 时使用 PyYAML（功能最全，推荐）；
  - 没有 PyYAML 时自动启用内置后备解析器，仍可解析本任务用到的 YAML 子集；
  - JSON 配置任何时候都不需要额外依赖。
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from typing import Any, Dict, List, Optional

try:
    import yaml  # type: ignore
    _HAS_YAML = True
except ImportError:  # pragma: no cover - 取决于是否装了依赖
    yaml = None
    _HAS_YAML = False


# ------------------------------ 常量 ------------------------------

MAX_ATTEMPTS = 3            # 1 次首发 + 最多 2 次重试
MAX_RETRIES = MAX_ATTEMPTS - 1
DEFAULT_REPORT = "report.json"

SUCCESS = "SUCCESS"
FAILED = "FAILED"
SKIPPED = "SKIPPED"
TIMEOUT = "TIMEOUT"
RETRY = "RETRY"

VALID_STATUS = (SUCCESS, FAILED, SKIPPED, TIMEOUT)

# ANSI 颜色：SUCCESS 绿 / FAILED 红 / RETRY 黄 / SKIPPED 蓝
ANSI_COLORS = {
    SUCCESS: "\033[32m",
    FAILED: "\033[31m",
    RETRY: "\033[33m",
    SKIPPED: "\033[34m",
    TIMEOUT: "\033[31m",
}
ANSI_RESET = "\033[0m"


class SchedulerError(Exception):
    """用于向用户展示的可读错误，保证不打印栈回溯。"""


def make_colorizer(enabled: bool):
    """返回一个把状态名染色的函数；enabled 为 False 时原样返回。"""

    def colorize(text: str, status: str) -> str:
        if not enabled:
            return text
        return "{}{}{}".format(ANSI_COLORS.get(status, ""), text, ANSI_RESET)

    return colorize


# ---------------------- 内置 YAML 后备解析器 ----------------------
# 只有在没有安装 PyYAML 时才会用到。支持本任务配置所需的最小 YAML 子集：
#   * 注释(#)与空行、文档分隔符 --- / ...
#   * key: value（int/float/bool/null/带引号或不带引号的字符串）
#   * 行内列表 [a, b, c]
#   * 缩进映射 与 "- key: value" 形式的映射列表
# 遇到不支持的写法会抛出可读的 SchedulerError，提示安装 PyYAML。

def _yaml_strip_comment(line: str) -> str:
    out = []
    quote = None
    for ch in line:
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
            out.append(ch)
        elif ch == "#":
            break
        else:
            out.append(ch)
    return "".join(out).rstrip()


def _yaml_split_list(text: str) -> List[str]:
    parts: List[str] = []
    cur: List[str] = []
    quote = None
    for ch in text:
        if quote:
            cur.append(ch)
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
            cur.append(ch)
        elif ch == ",":
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return [p.strip() for p in parts if p.strip() != ""]


def _yaml_scalar(token: str) -> Any:
    tok = token.strip()
    if tok == "":
        return None
    if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in ("'", '"'):
        return tok[1:-1]
    low = tok.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    if low in ("null", "~", "none"):
        return None
    if tok.startswith("[") and tok.endswith("]"):
        return [_yaml_scalar(p) for p in _yaml_split_list(tok[1:-1])]
    try:
        return int(tok)
    except ValueError:
        pass
    try:
        return float(tok)
    except ValueError:
        pass
    return tok


def _yaml_split_key(content: str):
    quote = None
    for idx, ch in enumerate(content):
        if quote:
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
        elif ch == ":":
            return content[:idx].strip(), content[idx + 1:]
    return content, None


def _yaml_is_list_item(content: str) -> bool:
    return content == "-" or content.startswith("- ")


def _yaml_parse_map(lines, i: int, indent: int):
    mapping: Dict[str, Any] = {}
    while i < len(lines):
        ind, content, lineno = lines[i]
        if ind < indent:
            break
        if ind > indent:
            raise SchedulerError(
                "YAML 缩进不一致（第 {} 行）: {}".format(lineno, content)
            )
        if _yaml_is_list_item(content):
            break
        key, rest = _yaml_split_key(content)
        if rest is None:
            raise SchedulerError(
                "后备 YAML 解析器无法解析第 {} 行（应为 key: value）: {}".format(lineno, content)
            )
        i += 1
        rest = rest.strip()
        if rest == "":
            if i < len(lines) and lines[i][0] > indent:
                value, i = _yaml_parse_node(lines, i, lines[i][0])
            elif i < len(lines) and lines[i][0] == indent and _yaml_is_list_item(lines[i][1]):
                value, i = _yaml_parse_list(lines, i, indent)
            else:
                value = None
        else:
            value = _yaml_scalar(rest)
        mapping[key] = value
    return mapping, i


def _yaml_parse_list(lines, i: int, indent: int):
    items: List[Any] = []
    while i < len(lines):
        ind, content, lineno = lines[i]
        if ind < indent:
            break
        if ind > indent:
            raise SchedulerError(
                "YAML 缩进不一致（第 {} 行）: {}".format(lineno, content)
            )
        if not _yaml_is_list_item(content):
            break
        rest = content[1:].strip()
        if rest == "":
            i += 1
            if i < len(lines) and lines[i][0] > indent:
                value, i = _yaml_parse_node(lines, i, lines[i][0])
            else:
                value = None
            items.append(value)
            continue
        key, sep_rest = _yaml_split_key(rest)
        if sep_rest is not None and rest[0] not in ("'", '"'):
            # 列表项本身是一个映射：把 "- " 换成两个空格，再按映射解析
            lines[i] = (indent + 2, rest, lineno)
            value, i = _yaml_parse_map(lines, i, indent + 2)
            items.append(value)
        else:
            items.append(_yaml_scalar(rest))
            i += 1
    return items, i


def _yaml_parse_node(lines, i: int, indent: int):
    if i >= len(lines):
        return None, i
    if _yaml_is_list_item(lines[i][1]):
        return _yaml_parse_list(lines, i, indent)
    return _yaml_parse_map(lines, i, indent)


def mini_yaml_load(text: str) -> Any:
    """PyYAML 缺失时的后备解析器（仅支持本任务用到的 YAML 子集）。"""
    raw = []
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = _yaml_strip_comment(line)
        if stripped.strip() == "":
            continue
        bare = stripped.strip()
        if bare in ("---", "..."):
            continue
        leading = stripped[: len(stripped) - len(stripped.lstrip())]
        if "\t" in leading:
            raise SchedulerError(
                "后备 YAML 解析器不支持 Tab 缩进（第 {} 行）。"
                "请改用空格，或安装 PyYAML: pip install -r requirements.txt".format(lineno)
            )
        raw.append((len(leading), bare, lineno))
    if not raw:
        raise SchedulerError("配置文件为空或只有注释")
    value, idx = _yaml_parse_node(raw, 0, raw[0][0])
    if idx != len(raw):
        raise SchedulerError(
            "后备 YAML 解析器无法解析第 {} 行: {}（若 YAML 较复杂，请安装 PyYAML）".format(
                raw[idx][2], raw[idx][1]
            )
        )
    return value


def _load_yaml_text(text: str) -> Any:
    """优先用 PyYAML；没装则退回内置后备解析器。"""
    if _HAS_YAML:
        try:
            return yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise SchedulerError("YAML 语法错误: {}".format(exc)) from exc
    return mini_yaml_load(text)


# --------------------------- 配置加载与校验 ---------------------------

def load_config(path: str) -> Dict[str, Any]:
    """读取 YAML/JSON 配置，返回解析后的字典。出错抛 SchedulerError。"""
    if not os.path.exists(path):
        raise SchedulerError("配置文件不存在: {}".format(path))
    if os.path.isdir(path):
        raise SchedulerError("配置路径是目录而不是文件: {}".format(path))

    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        raise SchedulerError("无法读取配置文件 {}: {}".format(path, exc)) from exc
    except UnicodeDecodeError as exc:
        raise SchedulerError("配置文件不是 UTF-8 编码: {}".format(path)) from exc

    if not text.strip():
        raise SchedulerError("配置文件为空: {}".format(path))

    ext = os.path.splitext(path)[1].lower()
    data: Any = None

    if ext in (".yaml", ".yml"):
        data = _load_yaml_text(text)
    elif ext == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise SchedulerError("JSON 语法错误: {}".format(exc)) from exc
    else:
        # 扩展名未知：先按 JSON 解析，失败再按 YAML 解析
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = _load_yaml_text(text)

    if data is None:
        raise SchedulerError("配置文件为空或只有注释: {}".format(path))
    if not isinstance(data, dict):
        raise SchedulerError("配置根节点必须是映射（包含 timeout / tasks 字段）")
    return data


def parse_tasks(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """校验 tasks 字段，返回规范化后的任务列表。"""
    raw_tasks = config.get("tasks")
    if raw_tasks is None:
        raise SchedulerError("配置缺少 'tasks' 字段")
    if not isinstance(raw_tasks, list):
        raise SchedulerError("'tasks' 必须是列表")
    if len(raw_tasks) == 0:
        raise SchedulerError("任务列表为空：至少需要 1 个任务")

    tasks: List[Dict[str, Any]] = []
    seen = set()

    for idx, item in enumerate(raw_tasks):
        where = "第 {} 个任务".format(idx + 1)
        if not isinstance(item, dict):
            raise SchedulerError("{} 必须是映射（name/duration/success_rate）".format(where))

        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            raise SchedulerError("{} 缺少合法的 'name'".format(where))
        name = name.strip()
        if name in seen:
            raise SchedulerError("任务名重复: {}".format(name))
        seen.add(name)

        if "duration" not in item:
            raise SchedulerError("任务 {} 缺少 'duration'".format(name))
        duration = item["duration"]
        if isinstance(duration, bool) or not isinstance(duration, (int, float)):
            raise SchedulerError("任务 {} 的 'duration' 必须是数字".format(name))
        if duration < 0:
            raise SchedulerError("任务 {} 的 'duration' 不能为负数".format(name))
        duration = float(duration)

        if "success_rate" not in item:
            raise SchedulerError("任务 {} 缺少 'success_rate'".format(name))
        rate = item["success_rate"]
        if isinstance(rate, bool) or not isinstance(rate, (int, float)):
            raise SchedulerError("任务 {} 的 'success_rate' 必须是数字".format(name))
        rate = float(rate)
        if not 0.0 <= rate <= 1.0:
            raise SchedulerError(
                "任务 {} 的 'success_rate' 越界（应在 0.0~1.0 之间）: {}".format(name, rate)
            )

        deps = item.get("dependencies", [])
        if deps is None:
            deps = []
        if not isinstance(deps, list):
            raise SchedulerError("任务 {} 的 'dependencies' 必须是列表".format(name))
        clean_deps: List[str] = []
        for dep in deps:
            if not isinstance(dep, str) or not dep.strip():
                raise SchedulerError("任务 {} 的依赖项必须是非空字符串".format(name))
            clean_deps.append(dep.strip())
        clean_deps = list(dict.fromkeys(clean_deps))  # 去重且保持顺序
        if name in clean_deps:
            raise SchedulerError("任务 {} 依赖了自己（自环）".format(name))

        tasks.append(
            {
                "name": name,
                "duration": duration,
                "success_rate": rate,
                "dependencies": clean_deps,
            }
        )

    return tasks


def parse_timeout(config: Dict[str, Any], cli_timeout: Optional[float]) -> Optional[float]:
    """命令行 --timeout 优先于配置文件 timeout；都没有则返回 None（不超时）。"""
    if cli_timeout is not None:
        if cli_timeout <= 0:
            raise SchedulerError("--timeout 必须大于 0")
        return float(cli_timeout)

    raw = config.get("timeout")
    if raw is None:
        return None
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise SchedulerError("配置中的 'timeout' 必须是数字")
    if raw <= 0:
        raise SchedulerError("配置中的 'timeout' 必须大于 0")
    return float(raw)


def topological_order(tasks: List[Dict[str, Any]]) -> List[str]:
    """Kahn 拓扑排序，正确处理分叉/汇合，并检测依赖环与缺失依赖。

    同层节点按“配置文件中出现的顺序”稳定出队，保证结果可复现。
    """
    names = [t["name"] for t in tasks]
    name_set = set(names)

    for task in tasks:
        for dep in task["dependencies"]:
            if dep not in name_set:
                raise SchedulerError(
                    "任务 {} 依赖了不存在的任务: {}".format(task["name"], dep)
                )

    indegree = {n: 0 for n in names}
    children: Dict[str, List[str]] = {n: [] for n in names}
    for task in tasks:
        for dep in task["dependencies"]:
            children[dep].append(task["name"])
            indegree[task["name"]] += 1

    ready = [n for n in names if indegree[n] == 0]
    order: List[str] = []
    while ready:
        ready.sort(key=names.index)  # 稳定：取配置顺序最靠前的就绪节点
        node = ready.pop(0)
        order.append(node)
        for child in children[node]:
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)

    if len(order) != len(names):
        remaining = [n for n in names if n not in order]
        raise SchedulerError("检测到依赖环，无法调度。涉及任务: " + ", ".join(remaining))
    return order


# ------------------------------ 调度执行 ------------------------------

def run_scheduler(
    tasks: List[Dict[str, Any]],
    timeout: Optional[float],
    seed: Optional[int],
    colorize,
    stream=None,
) -> Dict[str, Any]:
    """按依赖顺序执行任务，返回报告字典。"""
    stream = stream if stream is not None else sys.stdout
    order = topological_order(tasks)
    by_name = {t["name"]: t for t in tasks}
    names = [t["name"] for t in tasks]

    status: Dict[str, str] = {}
    records: Dict[str, Dict[str, Any]] = {
        n: {
            "name": n,
            "status": None,
            "attempts": 0,
            "duration": 0.0,
            "started_at": None,
            "ended_at": None,
        }
        for n in names
    }

    rng = random.Random(seed)
    start = time.monotonic()
    timed_out = False

    def elapsed() -> float:
        return time.monotonic() - start

    def log(status_name: str, name: str, detail: str = "") -> None:
        stamp = "[{:6.2f}s]".format(elapsed())
        line = "{} {} {}".format(stamp, colorize(status_name, status_name), name)
        if detail:
            line += " " + detail
        print(line, file=stream, flush=True)

    for name in order:
        task = by_name[name]

        # 依赖失败 / 被跳过 -> 自身 SKIPPED（不执行）
        bad_deps = [d for d in task["dependencies"] if status.get(d) != SUCCESS]
        if bad_deps:
            status[name] = SKIPPED
            records[name]["status"] = SKIPPED
            log(SKIPPED, name, "(依赖未成功: {})".format(", ".join(bad_deps)))
            continue

        # 执行前检查一次超时
        if timeout is not None and elapsed() > timeout:
            timed_out = True
            break

        record = records[name]
        record["started_at"] = round(time.time(), 3)
        task_start = time.monotonic()
        attempts = 0
        outcome: Optional[str] = None

        for attempt in range(1, MAX_ATTEMPTS + 1):
            attempts = attempt
            time.sleep(task["duration"])

            # 每次 sleep 之后必须再检查一次超时
            if timeout is not None and elapsed() > timeout:
                outcome = TIMEOUT
                break

            if rng.random() < task["success_rate"]:
                outcome = SUCCESS
                break

            if attempt < MAX_ATTEMPTS:
                log(FAILED, name, "(第 {} 次尝试失败)".format(attempt))
                log(RETRY, name, "(重试 {}/{})".format(attempt, MAX_RETRIES))
            else:
                log(FAILED, name, "(第 {} 次尝试失败，重试用尽)".format(attempt))

        record["attempts"] = attempts
        record["ended_at"] = round(time.time(), 3)
        record["duration"] = round(time.monotonic() - task_start, 3)

        if outcome == SUCCESS:
            status[name] = SUCCESS
            record["status"] = SUCCESS
            log(SUCCESS, name, "(attempts={}, {:.2f}s)".format(attempts, record["duration"]))
        elif outcome == TIMEOUT:
            timed_out = True
            status[name] = TIMEOUT
            record["status"] = TIMEOUT
            log(TIMEOUT, name, "(执行 {:.2f}s 后超时)".format(record["duration"]))
            break
        else:
            # 重试用尽仍失败 -> 记录为 SKIPPED，继续执行后续不依赖它的任务
            status[name] = SKIPPED
            record["status"] = SKIPPED
            log(SKIPPED, name, "(attempts={} 均失败，跳过)".format(attempts))

    total_duration = round(elapsed(), 3)

    # 因超时中断而从未执行的任务补记为 TIMEOUT，保证报告包含每个任务
    for name in names:
        if records[name]["status"] is None:
            records[name]["status"] = TIMEOUT

    if timed_out:
        print(
            "[{:6.2f}s] {} 总耗时超时，已终止后续任务".format(
                total_duration, colorize(TIMEOUT, TIMEOUT)
            ),
            file=stream,
            flush=True,
        )

    report = {
        "timeout": bool(timed_out),
        "total_duration": total_duration,
        "tasks": [records[n] for n in names],
    }
    return report


def write_report(path: str, report: Dict[str, Any]) -> None:
    """把报告写成 JSON（UTF-8，缩进 2）。"""
    out_dir = os.path.dirname(os.path.abspath(path))
    os.makedirs(out_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


# -------------------------------- CLI --------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scheduler.py",
        description="M0-4 TaskScheduler：按依赖顺序模拟执行任务，输出彩色日志与 report.json",
    )
    parser.add_argument("--config", required=True, help="任务配置文件（.yaml/.yml/.json）")
    parser.add_argument("--timeout", type=float, default=None, help="覆盖配置文件中的全局超时（秒）")
    parser.add_argument("--report", default=DEFAULT_REPORT, help="报告输出路径（默认 report.json）")
    parser.add_argument("--seed", type=int, default=None, help="随机种子，便于复现同一结果")
    parser.add_argument("--no-color", action="store_true", help="禁用彩色输出")
    parser.add_argument("--color", action="store_true", help="强制彩色输出（即使不是 TTY）")
    return parser


def resolve_color(args, stream=None) -> bool:
    stream = stream if stream is not None else sys.stdout
    if args.no_color:
        return False
    if args.color:
        return True
    if os.environ.get("NO_COLOR"):
        return False
    return bool(getattr(stream, "isatty", lambda: False)())


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        tasks = parse_tasks(config)
        timeout = parse_timeout(config, args.timeout)
        topological_order(tasks)  # 提前校验依赖环/缺失依赖，避免跑一半才报错
    except SchedulerError as exc:
        print("错误: {}".format(exc), file=sys.stderr)
        return 2

    colorize = make_colorizer(resolve_color(args))

    try:
        report = run_scheduler(tasks, timeout, args.seed, colorize)
    except SchedulerError as exc:
        print("错误: {}".format(exc), file=sys.stderr)
        return 2

    try:
        write_report(args.report, report)
    except OSError as exc:
        print("错误: 无法写入报告 {}: {}".format(args.report, exc), file=sys.stderr)
        return 2

    print("报告已写入: {}".format(os.path.abspath(args.report)))
    return 0


if __name__ == "__main__":
    sys.exit(main())