# -*- coding: utf-8 -*-
"""内置 YAML 后备解析器（无 PyYAML 时使用）的单元测试。

运行：  python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

import scheduler  # noqa: E402


class TestMiniYaml(unittest.TestCase):
    def test_parses_demo_yaml_like_json(self):
        yaml_path = os.path.join(PARENT, "tasks_demo.yaml")
        json_path = os.path.join(PARENT, "tasks_demo.json")
        with open(yaml_path, encoding="utf-8") as fh:
            raw = fh.read()
        tasks_fallback = scheduler.parse_tasks(scheduler.mini_yaml_load(raw))
        tasks_json = scheduler.parse_tasks(scheduler.load_config(json_path))
        self.assertEqual(tasks_fallback, tasks_json)

    def test_timeout_and_types(self):
        cfg = scheduler.mini_yaml_load("timeout: 15\ntasks: []\n")
        self.assertEqual(cfg["timeout"], 15)
        self.assertEqual(cfg["tasks"], [])

    def test_scalars(self):
        cfg = scheduler.mini_yaml_load(
            "a: 1\nb: 2.5\nc: true\nd: false\ne: null\nf: \"hi\"\ng: 'x y'\n"
        )
        self.assertEqual(cfg["a"], 1)
        self.assertEqual(cfg["b"], 2.5)
        self.assertIs(cfg["c"], True)
        self.assertIs(cfg["d"], False)
        self.assertIsNone(cfg["e"])
        self.assertEqual(cfg["f"], "hi")
        self.assertEqual(cfg["g"], "x y")

    def test_inline_list_and_comments(self):
        cfg = scheduler.mini_yaml_load(
            "# 顶部注释\n"
            "tasks:\n"
            "  - name: A          # 行尾注释\n"
            "    duration: 1\n"
            "    success_rate: 1\n"
            "    dependencies: []\n"
            "  - name: B\n"
            "    duration: 1\n"
            "    success_rate: 1\n"
            "    dependencies: [\"A\"]\n"
        )
        tasks = scheduler.parse_tasks(cfg)
        self.assertEqual([t["name"] for t in tasks], ["A", "B"])
        self.assertEqual(tasks[0]["dependencies"], [])
        self.assertEqual(tasks[1]["dependencies"], ["A"])

    def test_block_style_dependencies(self):
        # dependencies 写成换行列表（不是行内 []）也应支持
        cfg = scheduler.mini_yaml_load(
            "tasks:\n"
            "  - name: A\n"
            "    duration: 1\n"
            "    success_rate: 1\n"
            "    dependencies: []\n"
            "  - name: B\n"
            "    duration: 1\n"
            "    success_rate: 1\n"
            "    dependencies:\n"
            "      - \"A\"\n"
        )
        tasks = scheduler.parse_tasks(cfg)
        self.assertEqual(tasks[1]["dependencies"], ["A"])

    def test_quoted_string_with_colon(self):
        cfg = scheduler.mini_yaml_load(
            "tasks:\n"
            "  - name: \"A:B\"\n"
            "    duration: 1\n"
            "    success_rate: 1\n"
            "    dependencies: []\n"
        )
        self.assertEqual(cfg["tasks"][0]["name"], "A:B")

    def test_document_markers_ignored(self):
        cfg = scheduler.mini_yaml_load("---\ntimeout: 5\ntasks: []\n...\n")
        self.assertEqual(cfg["timeout"], 5)

    def test_tab_indent_rejected_with_readable_error(self):
        with self.assertRaises(scheduler.SchedulerError):
            scheduler.mini_yaml_load("tasks:\n\t- name: A\n")

    def test_empty_text_rejected(self):
        with self.assertRaises(scheduler.SchedulerError):
            scheduler.mini_yaml_load("# 只有注释\n\n")


class TestLoadConfigUsesFallback(unittest.TestCase):
    def test_yaml_file_parsed_without_pyyaml(self):
        """直接调用 _load_yaml_text 走后备分支时，结果应与 PyYAML 一致。"""
        yaml_path = os.path.join(PARENT, "tasks_demo.yaml")
        with open(yaml_path, encoding="utf-8") as fh:
            raw = fh.read()
        fallback = scheduler.parse_tasks(scheduler.mini_yaml_load(raw))
        normal = scheduler.parse_tasks(scheduler.load_config(yaml_path))
        self.assertEqual(fallback, normal)


if __name__ == "__main__":
    unittest.main()