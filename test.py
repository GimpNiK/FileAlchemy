import os
import shutil
import tempfile
import unittest
from pathlib import Path

from FileAlchemy.structures.archive import Archive


class TestArchiveAPI(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        # sample files with diverse content
        self.files = [
            ("file_ascii.txt", "ASCII content"),
            ("file_кириллица.txt", "Содержимое на русском"),
            ("file_日本語.txt", "日本語の内容"),
            ("file_emoji😊.txt", "Содержимое с эмодзи 😊"),
        ]
        for name, content in self.files:
            (self.tmp_dir / name).write_text(content, encoding="utf-8")

        # nested directory with duplicates
        self.subdir = self.tmp_dir / "nested"
        self.subdir.mkdir(parents=True, exist_ok=True)
        for name, content in self.files:
            (self.subdir / name).write_text(f"nested/{content}", encoding="utf-8")

        # deep structure
        self.deep_dir = self.tmp_dir / "deep" / "a" / "b" / "c"
        self.deep_dir.mkdir(parents=True, exist_ok=True)
        (self.deep_dir / "deep.txt").write_text("deep", encoding="utf-8")

        # a binary file for size checks
        self.bin_file = self.tmp_dir / "bin.dat"
        self.bin_file.write_bytes(os.urandom(256 * 1024))

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_create_empty_archives(self):
        formats = ["zip", "7z", "tar", "tar.gz", "tar.bz2"]
        for fmt in formats:
            path = self.tmp_dir / f"empty.{fmt}"
            arc = Archive(path, fmt)
            arc.create()
            self.assertTrue(path.exists(), f"archive not created: {fmt}")
            self.assertEqual(arc.list_files(), [], f"new archive is not empty: {fmt}")

    def test_add_and_list(self):
        formats = ["zip", "7z", "tar", "tar.gz", "tar.bz2"]
        for fmt in formats:
            path = self.tmp_dir / f"test_add.{fmt}"
            arc = Archive(path, fmt)
            # add files and a directory
            for name, _ in self.files:
                arc.add(self.tmp_dir / name)
            arc.add(self.subdir)

            names = set(arc.list_files())
            # basic expectations
            for name, _ in self.files:
                self.assertIn(name, names, f"missing top-level file in {fmt}: {name}")
            # nested entries should include directory prefix
            expected_nested = {f"nested/{name}" for name, _ in self.files}
            # tar based formats may store exactly these names as well
            self.assertTrue(expected_nested.issubset(names), f"nested files missing in {fmt}")

    def test_add_directory_and_arcname(self):
        formats = ["zip", "7z", "tar", "tar.gz", "tar.bz2"]
        for fmt in formats:
            path = self.tmp_dir / f"test_add_dir_arcname.{fmt}"
            arc = Archive(path, fmt)
            arc.add(self.subdir, arcname="root")
            names = set(arc.list_files())
            expected = {f"root/{name}" for name, _ in self.files}
            self.assertTrue(expected.issubset(names), f"arcname not respected for {fmt}")

    def test_extract_roundtrip(self):
        formats = ["zip", "7z", "tar", "tar.gz", "tar.bz2"]
        for fmt in formats:
            path = self.tmp_dir / f"test_extract.{fmt}"
            arc = Archive(path, fmt)

            # add a single and a directory
            arc.add(self.tmp_dir / self.files[0][0])
            arc.add(self.subdir)

            out_dir = self.tmp_dir / f"out_{fmt}"
            out_dir.mkdir(exist_ok=True)
            arc.extract(path=out_dir)

            # check files
            self.assertTrue((out_dir / self.files[0][0]).exists(), f"single file not extracted: {fmt}")
            for name, content in self.files:
                p = out_dir / "nested" / name
                self.assertTrue(p.exists(), f"nested {name} not extracted: {fmt}")
                self.assertEqual(p.read_text(encoding="utf-8"), f"nested/{content}")

    def test_extract_specific_member(self):
        formats = ["zip", "7z", "tar", "tar.gz", "tar.bz2"]
        for fmt in formats:
            path = self.tmp_dir / f"test_extract_member.{fmt}"
            arc = Archive(path, fmt)
            # add nested directory under custom root to have prefix
            arc.add(self.subdir, arcname="root")
            out_dir = self.tmp_dir / f"out_member_{fmt}"
            out_dir.mkdir(exist_ok=True)
            # choose one member
            member_name = "root/" + self.files[0][0]
            arc.extract(member=member_name, path=out_dir)
            self.assertTrue((out_dir / member_name).exists(), f"member not extracted: {fmt}")

    def test_iteration_and_list_files(self):
        formats = ["zip", "7z", "tar", "tar.gz", "tar.bz2"]
        for fmt in formats:
            path = self.tmp_dir / f"test_iter.{fmt}"
            arc = Archive(path, fmt)
            arc.add(self.tmp_dir / self.files[0][0])
            arc.add(self.subdir)
            listed = set(arc.list_files())
            iterated = set(iter(arc))
            self.assertSetEqual(listed, iterated, f"__iter__ differs from list_files for {fmt}")

    def test_gz_bz2_extract_single(self):
        # create gz and bz2 from a single file path
        # The Archive expects the archive file path in constructor
        for fmt in ["gz", "bz2"]:
            src = self.tmp_dir / "single.txt"
            src.write_text("one", encoding="utf-8")
            # create archive using standard libs directly
            if fmt == "gz":
                import gzip as _gzip
                with _gzip.open(self.tmp_dir / "single.gz", "wb") as f:
                    f.write(src.read_bytes())
                archive_path = self.tmp_dir / "single.gz"
            else:
                import bz2 as _bz2
                with _bz2.open(self.tmp_dir / "single.bz2", "wb") as f:
                    f.write(src.read_bytes())
                archive_path = self.tmp_dir / "single.bz2"

            arc = Archive(archive_path)
            out_dir = self.tmp_dir / f"out_{fmt}"
            out_dir.mkdir(exist_ok=True)
            arc.extract(path=out_dir)
            self.assertTrue((out_dir / "single").exists(), f"{fmt} single file not extracted")

    def test_create_from_without_files(self):
        formats = ["zip", "7z", "tar", "tar.gz", "tar.bz2"]
        for fmt in formats:
            path = self.tmp_dir / f"created_empty.{fmt}"
            arc = Archive.create_from(path, fmt, files=[])
            self.assertTrue(path.exists())
            self.assertEqual(arc.list_files(), [])

    def test_create_from_with_files(self):
        formats = ["zip", "7z", "tar", "tar.gz", "tar.bz2"]
        for fmt in formats:
            path = self.tmp_dir / f"created_from.{fmt}"
            arc = Archive.create_from(
                path,
                fmt,
                files=[self.tmp_dir / self.files[0][0], self.subdir],
            )
            names = set(arc.list_files())
            self.assertIn(self.files[0][0], names)
            expected_nested = {f"nested/{name}" for name, _ in self.files}
            self.assertTrue(expected_nested.issubset(names))

    def test_large_binary_roundtrip(self):
        formats = ["zip", "7z", "tar", "tar.gz", "tar.bz2"]
        for fmt in formats:
            path = self.tmp_dir / f"bin_{fmt}.{fmt}"
            arc = Archive(path, fmt)
            arc.add(self.bin_file)
            out_dir = self.tmp_dir / f"out_bin_{fmt}"
            out_dir.mkdir(exist_ok=True)
            arc.extract(path=out_dir)
            self.assertTrue((out_dir / self.bin_file.name).exists())
            self.assertEqual((out_dir / self.bin_file.name).stat().st_size, self.bin_file.stat().st_size)

    def test_password_zip_and_7z(self):
        password = "s3cr3t-Пароль😊"
        for fmt in ["zip", "7z"]:
            path = self.tmp_dir / f"protected.{fmt}"
            arc = Archive(path, fmt, password=password)
            arc.add(self.tmp_dir / self.files[0][0])

            out_dir = self.tmp_dir / f"out_protected_{fmt}"
            out_dir.mkdir(exist_ok=True)
            # Reopen with password and extract
            arc2 = Archive(path, password=password)
            arc2.extract(path=out_dir)
            self.assertTrue((out_dir / self.files[0][0]).exists())

            # Attempt extraction with wrong password should raise in both formats
            with self.assertRaises(Exception):
                wrong = Archive(path, password="wrong")
                wrong.extract(path=out_dir / "wrong")


if __name__ == "__main__":
    unittest.main()