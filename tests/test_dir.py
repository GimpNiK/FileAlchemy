import sys
import os
import platform
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from FileAlchemy.structures.dir import Dir


def test_dir_create_move_rename(tmp_path: Path):
    d = Dir(tmp_path / "root")
    d.create()
    assert (tmp_path / "root").exists()

    d2 = Dir(tmp_path / "dest")
    d.move_to(d2)
    assert (tmp_path / "dest" / "root").exists()

    d3 = Dir(tmp_path / "dest" / "root")
    d3.rename("ren")
    assert (tmp_path / "dest" / "ren").exists()


def test_dir_magic_div_and_iter(tmp_path: Path):
    d = Dir(tmp_path)
    (tmp_path / "a.txt").write_text("1")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("2")

    # __truediv__ возвращает File или Dir
    a = d / "a.txt"
    assert a.path.name == "a.txt"
    sub = d / "sub/"
    assert str(sub).endswith(os.path.sep)

    # __iter__ отдает File/Dir
    names = {x.path.name if hasattr(x, "path") else Path(x).name for x in d}
    assert names >= {"a.txt", "sub"}


def test_dir_metadata_and_sizes(tmp_path: Path):
    d = Dir(tmp_path / "m")
    d.create(parents=True, ignore_errors=True)
    for i in range(3):
        (d.path / f"f{i}.txt").write_text("abc")
    md = d.metadata()
    assert md["item_count"]["total"] >= 3
    assert md["sizeof"] >= 9


def test_dir_hidden_property(tmp_path: Path):
    d = Dir(tmp_path / ".hidden_dir")
    d.create(ignore_errors=True)
    if platform.system() == "Windows":
        # На Windows требуется pywin32 для изменения скрытости; проверяем доступность
        try:
            import win32api  # type: ignore
            import win32con  # type: ignore
        except Exception:
            pytest.skip("pywin32 не установлен")
        # чтение/запись hidden
        val = d.hidden
        d.hidden = not val
        assert isinstance(d.hidden, bool)
    else:
        # На Unix скрытость через точку в имени
        assert d.hidden is True


