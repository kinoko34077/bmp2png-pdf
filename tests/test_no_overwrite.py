"""PNG/PDF最終公開の非上書き契約: 実ファイル・競合・失敗時cleanup。"""

import errno
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from pypdf import PdfReader

import image_processing
import pdf_export


class NoOverwritePublicationTests(unittest.TestCase):
    def setUp(self):
        self.workdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.workdir.cleanup)
        self.root = Path(self.workdir.name)
        self.input_path = self.root / "source.png"
        Image.new("RGBA", (6, 4), (10, 20, 30, 200)).save(self.input_path)
        self.png_path = self.root / "result.png"
        self.pdf_path = self.root / "result.pdf"

    def assert_no_temporary_files(self):
        self.assertEqual(
            [p.name for p in self.root.iterdir() if p.name.endswith((".tmp.png", ".tmp.pdf"))],
            [],
        )

    def test_png_and_pdf_no_overwrite_can_create_new_outputs(self):
        image_processing.convert_image_to_png(
            self.input_path, self.png_path, overwrite=False
        )
        with Image.open(self.png_path) as image:
            self.assertEqual(image.getpixel((0, 0)), (10, 20, 30, 200))
        pdf_export.create_combined_pdf(
            [self.png_path], self.pdf_path, overwrite=False
        )
        self.assertEqual(len(PdfReader(self.pdf_path).pages), 1)
        self.assert_no_temporary_files()

    def test_existing_png_and_pdf_are_never_replaced(self):
        for output, convert in (
            (self.png_path, lambda: image_processing.convert_image_to_png(
                self.input_path, self.png_path, overwrite=False
            )),
            (self.pdf_path, lambda: pdf_export.create_combined_pdf(
                [self.input_path], self.pdf_path, overwrite=False
            )),
        ):
            with self.subTest(output=output.name):
                output.write_bytes(b"existing-bytes")
                with self.assertRaises(FileExistsError):
                    convert()
                self.assertEqual(output.read_bytes(), b"existing-bytes")
                self.assert_no_temporary_files()

    def test_late_png_collision_keeps_competing_output(self):
        original = image_processing.publish_no_overwrite

        def competitor(temp, output):
            output.write_bytes(b"created-during-conversion")
            return original(temp, output)

        with patch("image_processing.publish_no_overwrite", side_effect=competitor):
            with self.assertRaises(FileExistsError):
                image_processing.convert_image_to_png(
                    self.input_path, self.png_path, overwrite=False
                )
        self.assertEqual(self.png_path.read_bytes(), b"created-during-conversion")
        self.assert_no_temporary_files()

    def test_late_pdf_collision_keeps_competing_output(self):
        original = image_processing.publish_no_overwrite

        def competitor(temp, output):
            output.write_bytes(b"created-during-pdf-generation")
            return original(temp, output)

        with patch("pdf_export.publish_no_overwrite", side_effect=competitor):
            with self.assertRaises(FileExistsError):
                pdf_export.create_combined_pdf(
                    [self.input_path], self.pdf_path, overwrite=False
                )
        self.assertEqual(self.pdf_path.read_bytes(), b"created-during-pdf-generation")
        self.assert_no_temporary_files()

    def test_explicit_overwrite_replaces_png_and_pdf(self):
        self.png_path.write_bytes(b"old-png")
        self.pdf_path.write_bytes(b"old-pdf")
        image_processing.convert_image_to_png(
            self.input_path, self.png_path, overwrite=True
        )
        pdf_export.create_combined_pdf(
            [self.png_path], self.pdf_path, overwrite=True
        )
        self.assertTrue(self.png_path.read_bytes().startswith(b"\x89PNG"))
        self.assertTrue(self.pdf_path.read_bytes().startswith(b"%PDF"))
        self.assert_no_temporary_files()

    @unittest.skipUnless(os.name == "posix", "POSIX hard-link path only")
    def test_unsupported_hardlink_keeps_destination_absent_and_cleans_temp(self):
        for output, convert in (
            (self.png_path, lambda: image_processing.convert_image_to_png(
                self.input_path, self.png_path, overwrite=False
            )),
            (self.pdf_path, lambda: pdf_export.create_combined_pdf(
                [self.input_path], self.pdf_path, overwrite=False
            )),
        ):
            with self.subTest(output=output.name):
                with patch(
                    "image_processing.os.link",
                    side_effect=OSError(errno.EOPNOTSUPP, "hardlink unsupported"),
                ):
                    with self.assertRaises(OSError) as error:
                        convert()
                self.assertIn("安全な非上書き", str(error.exception))
                self.assertFalse(output.exists())
                self.assert_no_temporary_files()

    @unittest.skipUnless(os.name == "posix", "POSIX symbolic-link path only")
    def test_dangling_destination_symlink_is_not_replaced(self):
        self.png_path.symlink_to(self.root / "nonexistent")
        with self.assertRaises(FileExistsError):
            image_processing.convert_image_to_png(
                self.input_path, self.png_path, overwrite=False
            )
        self.assertTrue(self.png_path.is_symlink())
        self.assert_no_temporary_files()

    def test_windows_publication_branch_uses_rename_not_hardlink(self):
        # Windows host CI separately exercises native rename against real files.
        temporary = self.root / "stage.tmp"
        temporary.write_bytes(b"done")
        with patch.object(image_processing.os, "name", "nt"), patch(
            "image_processing.os.rename"
        ) as rename, patch("image_processing.os.link") as link:
            image_processing.publish_no_overwrite(temporary, self.png_path)
        rename.assert_called_once_with(temporary, self.png_path)
        link.assert_not_called()


if __name__ == "__main__":
    unittest.main()
