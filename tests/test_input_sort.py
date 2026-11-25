"""入力ファイル名の自然順とUnicode数字の回帰。"""
import tempfile
import unittest
from pathlib import Path

from conversion_service import sort_input_paths


class InputSortTests(unittest.TestCase):
    def test_non_decimal_digits_are_text_and_decimal_digits_sort_naturally(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            names = ["img10.png", "img2.png", "img1²2.png", "other١٠.png", "other٣.png"]
            paths = [root / name for name in names]
            for path in paths:
                path.touch()
            result = sort_input_paths([*paths, paths[1]])
            self.assertEqual(
                [path.name for path in result],
                ["img1²2.png", "img2.png", "img10.png", "other٣.png", "other١٠.png"],
            )


if __name__ == "__main__":
    unittest.main()
