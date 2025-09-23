import os
import platform
import stat
from pathlib import Path

import pytest

from FileAlchemy import file_utils as fu


def test_mkdir_and_ls(tmp_path: Path):
    d = tmp_path / "a" / "b"
    fu.mkdir(d, parents=True, exist_ok=True)
    # create files
    (d / "x.txt").write_text("x")
    (d / "y.txt").write_text("y")
    names = fu.ls(d).split(" ")
    assert set(names) >= {"x.txt", "y.txt"}


def test_mkfile_copy_remove(tmp_path: Path):
    src = tmp_path / "src.txt"
    fu.mkfile(src)
    assert src.exists()
    (tmp_path / "sub").mkdir()
    dst = tmp_path / "sub" / "dst.txt"
    fu.copy(src, dst)
    assert dst.exists()
    fu.rmfile(dst)
    assert not dst.exists()


def test_copy_directory_recursive(tmp_path: Path):
    src_dir = tmp_path / "src"
    fu.mkdir(src_dir)
    (src_dir / "a.txt").write_text("1")
    (src_dir / "b.txt").write_text("2")
    dst_dir = tmp_path / "dst"
    fu.copy(src_dir, dst_dir)
    assert (dst_dir / "a.txt").exists()
    assert (dst_dir / "b.txt").exists()


def test_make_archive_and_extract(tmp_path: Path):
    src_dir = tmp_path / "data"
    fu.mkdir(src_dir)
    (src_dir / "f.txt").write_text("hi")
    archive = tmp_path / "data.zip"
    fu.make_archive(src_dir, archive, format="zip")
    out = tmp_path / "out"
    fu.extract_archive(archive, out)
    assert (out / "data" / "f.txt").exists()


def test_chmod_changes_mode(tmp_path: Path):
    p = tmp_path / "f.txt"
    p.write_text("x")
    new_mode = 0o644
    fu.chmod(p, new_mode)
    mode = stat.S_IMODE(p.stat().st_mode)
    # На Windows chmod ограничен, но как минимум не должен падать
    if platform.system() != "Windows":
        assert mode == new_mode


def test_make_creates_parents_and_file(tmp_path: Path):
    p = tmp_path / "a" / "b" / "c.txt"
    fu.make(p)
    assert p.exists()
    d = tmp_path / "x" / "y"
    fu.make(d, is_file=False)
    assert d.exists() and d.is_dir()


def test_remove_file_and_dir(tmp_path: Path):
    f = tmp_path / "f.txt"
    f.write_text("x")
    fu.remove(f)
    assert not f.exists()
    d = tmp_path / "d"
    fu.mkdir(d)
    (d / "a.txt").write_text("1")
    fu.remove(d)
    assert not d.exists()


def test_ls_details(tmp_path: Path):
    (tmp_path / "a.txt").write_text("1")
    details = fu.ls(tmp_path, details=True)
    # строка вида: -rw-r--r-- 1 user group size Mon DD  YYYY a.txt
    assert "a.txt" in details


