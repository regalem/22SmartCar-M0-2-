import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from corr_tool import CorrelationError, load_config, load_xy, main, pearson_correlation


class CorrelationTests(unittest.TestCase):
    def test_perfect_positive_correlation(self):
        self.assertAlmostEqual(pearson_correlation([1, 2, 3], [2, 4, 6]), 1.0)

    def test_perfect_negative_correlation(self):
        self.assertAlmostEqual(pearson_correlation([1, 2, 3], [6, 4, 2]), -1.0)

    def test_zero_variance_is_rejected(self):
        with self.assertRaises(CorrelationError):
            pearson_correlation([1, 1, 1], [2, 3, 4])


class LoadingTests(unittest.TestCase):
    def test_config_resolves_csv_relative_to_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "data.csv"
            csv_path.write_text("x,y\n1,2\n2,4\n", encoding="utf-8")
            config_path = root / "config.yaml"
            config_path.write_text(
                yaml.safe_dump({"input_csv": "data.csv", "columns": {"x": "x", "y": "y"}}),
                encoding="utf-8",
            )

            resolved_csv, col_x, col_y = load_config(config_path)

            self.assertEqual(resolved_csv, csv_path)
            self.assertEqual((col_x, col_y), ("x", "y"))

    def test_missing_column_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "data.csv"
            csv_path.write_text("x,other\n1,2\n2,4\n", encoding="utf-8")

            with self.assertRaises(CorrelationError):
                load_xy(csv_path, "x", "y")

    def test_cli_prints_r_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "data.csv"
            csv_path.write_text("x,y\n1,2\n2,4\n3,6\n", encoding="utf-8")
            config_path = root / "config.yaml"
            config_path.write_text(
                yaml.safe_dump({"input_csv": "data.csv", "columns": {"x": "x", "y": "y"}}),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(["--config", str(config_path)])

            self.assertEqual(exit_code, 0)
            self.assertIn("r = 1.0", stdout.getvalue())
            self.assertEqual(stderr.getvalue(), "")


if __name__ == "__main__":
    unittest.main()