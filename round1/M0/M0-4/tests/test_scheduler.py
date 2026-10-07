# -*- coding: utf-8 -*-
"""M0-4 TaskScheduler 单元测试。

运行：  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from unittest import mock

# 让测试能 import 上一级目录的 scheduler.py
HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

import scheduler  # noqa: E402


class FakeClock:
    """可控时钟，避免测试真的 sleep。"""

    def __init__(self, start=1000.0):
        self.t = start

    def monotonic(self):
        return self.t

    def sleep(self, seconds):
        self.t += seconds

    def time(self):
        return 1700000000.0 + (self.t - 1000.0)


def run(tasks, timeout=None, seed=42, clock=None):
    clock = clock or FakeClock()
    colorize = scheduler.make_colorizer(False)
    buf = io.StringIO()
    with mock.patch.object(scheduler, "time", clock):
        with redirect_stdout(buf):
            report = scheduler.run_scheduler(tasks, timeout, seed, colorize)
    return report, buf.getvalue()


def task(name, duration=1.0, rate=1.0, deps=None):
    return {
        "name": name,
        "duration": duration,
        "success_rate": rate,
        "dependencies": deps or [],
    }


class TestValidation(unittest.TestCase):
    def test_empty_task_list(self):
        with self.assertRaises(scheduler.SchedulerError):
            scheduler.parse_tasks({"tasks": []})

    def test_missing_tasks_key(self):
        with self.assertRaises(scheduler.SchedulerError):
            scheduler.parse_tasks({})

    def test_duplicate_names(self):
        with self.assertRaises(scheduler.SchedulerError):
            scheduler.parse_tasks({"tasks": [task("A"), task("A")]})

    def test_success_rate_out_of_range(self):
        for bad in (-0.1, 1.1):
            with self.assertRaises(scheduler.SchedulerError):
                scheduler.parse_tasks({"tasks": [task("A", rate=bad)]})

    def test_missing_dependency_detected(self):
        with self.assertRaises(scheduler.SchedulerError):
            scheduler.topological_order([task("A", deps=["Ghost"])])

    def test_cycle_detected(self):
        tasks = [task("A", deps=["B"]), task("B", deps=["A"])]
        with self.assertRaises(scheduler.SchedulerError):
            scheduler.topological_order(tasks)


class TestTopology(unittest.TestCase):
    def test_fork_join_order(self):
        tasks = [
            task("Init"),
            task("Navigate", deps=["Init"]),
            task("DetectQR", deps=["Navigate"]),
            task("AvoidObstacle", deps=["Navigate"]),
            task("Place", deps=["DetectQR", "AvoidObstacle"]),
        ]
        order = scheduler.topological_order(tasks)
        pos = {n: i for i, n in enumerate(order)}
        self.assertLess(pos["Init"], pos["Navigate"])
        self.assertLess(pos["Navigate"], pos["DetectQR"])
        self.assertLess(pos["Navigate"], pos["AvoidObstacle"])
        self.assertLess(pos["DetectQR"], pos["Place"])
        self.assertLess(pos["AvoidObstacle"], pos["Place"])
        self.assertEqual(len(order), len(tasks))

    def test_stable_order_follows_config(self):
        tasks = [task("B"), task("A")]
        self.assertEqual(scheduler.topological_order(tasks), ["B", "A"])


class TestScheduling(unittest.TestCase):
    def test_all_success(self):
        tasks = [task("Init", 0.5), task("Run", 1.0, deps=["Init"])]
        report, _ = run(tasks, seed=1)
        self.assertFalse(report["timeout"])
        self.assertEqual([t["status"] for t in report["tasks"]], ["SUCCESS", "SUCCESS"])
        self.assertEqual(report["tasks"][1]["attempts"], 1)

    def test_failure_retries_then_skipped(self):
        # rate=0.0 -> 每次都失败，3 次尝试后记为 SKIPPED
        report, _ = run([task("Init", 0.5, rate=0.0)], seed=1)
        rec = report["tasks"][0]
        self.assertEqual(rec["status"], "SKIPPED")
        self.assertEqual(rec["attempts"], 3)  # 1 首发 + 2 重试，不超过 3
        self.assertLessEqual(rec["attempts"], 3)

    def test_skipped_propagates_to_downstream(self):
        tasks = [
            task("Init", 0.1, rate=0.0),
            task("Navigate", 0.1, deps=["Init"]),
            task("DetectQR", 0.1, deps=["Navigate"]),
        ]
        report, _ = run(tasks, seed=1)
        statuses = {t["name"]: t["status"] for t in report["tasks"]}
        self.assertEqual(statuses["Init"], "SKIPPED")
        self.assertEqual(statuses["Navigate"], "SKIPPED")
        self.assertEqual(statuses["DetectQR"], "SKIPPED")

    def test_independent_branch_still_runs(self):
        # Init 失败被跳过，但独立分支 Cleanup 不应受影响
        tasks = [task("Init", 0.1, rate=0.0), task("Cleanup", 0.1, rate=1.0)]
        report, _ = run(tasks, seed=1)
        statuses = {t["name"]: t["status"] for t in report["tasks"]}
        self.assertEqual(statuses["Cleanup"], "SUCCESS")

    def test_timeout_aborts_and_marks_rest(self):
        # timeout 很小，第一个任务 sleep 后就应触发超时
        tasks = [task("Slow", 2.0), task("Next", 1.0, deps=["Slow"])]
        report, _ = run(tasks, timeout=1.0, seed=1)
        self.assertTrue(report["timeout"])
        statuses = {t["name"]: t["status"] for t in report["tasks"]}
        self.assertEqual(statuses["Slow"], "TIMEOUT")
        self.assertEqual(statuses["Next"], "TIMEOUT")

    def test_report_contains_every_task(self):
        tasks = [task("A", 0.1), task("B", 0.1, deps=["A"]), task("C", 0.1)]
        report, _ = run(tasks, seed=3)
        self.assertEqual([t["name"] for t in report["tasks"]], ["A", "B", "C"])
        for rec in report["tasks"]:
            self.assertIn(rec["status"], {"SUCCESS", "FAILED", "SKIPPED", "TIMEOUT"})
            self.assertLessEqual(rec["attempts"], 3)

    def test_seed_reproducible(self):
        tasks = [task("A", 0.1, rate=0.5), task("B", 0.1, rate=0.5)]
        r1, _ = run(tasks, seed=7)
        r2, _ = run(tasks, seed=7)
        self.assertEqual(
            [t["status"] for t in r1["tasks"]],
            [t["status"] for t in r2["tasks"]],
        )


class TestConfigFiles(unittest.TestCase):
    def test_yaml_and_json_demo_equivalent(self):
        yaml_path = os.path.join(PARENT, "tasks_demo.yaml")
        json_path = os.path.join(PARENT, "tasks_demo.json")
        if not (os.path.exists(yaml_path) and os.path.exists(json_path)):
            self.skipTest("demo 配置不存在")
        tasks_yaml = scheduler.parse_tasks(scheduler.load_config(yaml_path))
        tasks_json = scheduler.parse_tasks(scheduler.load_config(json_path))
        self.assertEqual(tasks_yaml, tasks_json)

    def test_missing_file(self):
        with self.assertRaises(scheduler.SchedulerError):
            scheduler.load_config(os.path.join(PARENT, "no_such_file.yaml"))


if __name__ == "__main__":
    unittest.main()