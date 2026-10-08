"""M0-2 单元测试：已知数据 + 异常输入。"""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from corr_tool import pearson, read_xy


class TestPearson(unittest.TestCase):
    def test_perfect_positive(self):
        self.assertAlmostEqual(pearson([1, 2, 3], [2, 4, 6]), 1.0)

    def test_perfect_negative(self):
        self.assertAlmostEqual(pearson([1, 2, 3], [6, 4, 2]), -1.0)

    def test_zero_variance(self):
        with self.assertRaises(ValueError):
            pearson([1, 1, 1], [2, 3, 4])

    def test_length_mismatch(self):
        with self.assertRaises(ValueError):
            pearson([1, 2], [1, 2, 3])


class TestReadCsv(unittest.TestCase):
    def _write(self, text):
        tmp = Path(tempfile.mkdtemp()) / "data.csv"
        tmp.write_text(text, encoding="utf-8")
        return tmp

    def test_missing_column(self):
        path = self._write("x,other\n1,2\n2,4\n")
        with self.assertRaises(ValueError):
            read_xy(path, "x", "y")

    def test_empty_file(self):
        path = self._write("")
        with self.assertRaises(ValueError):
            read_xy(path, "x", "y")

    def test_non_numeric(self):
        path = self._write("x,y\n1,2\nabc,4\n")
        with self.assertRaises(ValueError):
            read_xy(path, "x", "y")


if __name__ == "__main__":
    unittest.main()
