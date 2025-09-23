import sys
import os
import platform
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from FileAlchemy.structures.stream import Stream
from FileAlchemy.structures.file import File


def test_stream_ops_with_file(tmp_path: Path):
    f1 = File(tmp_path / "a.txt")
    f2 = File(tmp_path / "b.txt")

    # запись и чтение через content property
    f1.content = "hello"
    assert f1.content == "hello"

    # оператор > (копия содержимого a -> b)
    f1 > f2
    assert f2.content == "hello"

    # оператор << (дополнение в конец)
    f2 << " world"
    assert f2.content.endswith(" world")

    # оператор < (перезапись b из a)
    f2 << "!"
    f2 > f1  # теперь a == b
    assert f1.content == f2.content


def test_file_props_and_metadata(tmp_path: Path):
    p = tmp_path / "meta.txt"
    f = File(p)
    f.content = "x"
    assert f.name == "meta.txt"
    assert f.extension == ".txt"
    assert f.sizeof() == 1
    md = f.metadata()
    assert md["name"] == "meta.txt"
    assert md["sizeof"] == 1
    assert isinstance(md["created_utc"].isoformat(), str)


def test_file_recode(tmp_path: Path):
    p = tmp_path / "enc.txt"
    f = File(p)
    f.content = "Привет"
    # Перекодировать в utf-8 (допустимо вызывать без from_encoding)
    f.recode(to_encoding="utf-8")
    assert "Привет" in f.content


def test_file_hidden_flag_unix_like(tmp_path: Path):
    p = tmp_path / ".hidden.txt"
    f = File(p)
    f.content = "x"
    # На Unix скрытые файлы начинаются с точки
    if os.name != "nt":
        assert f.metadata()["hidden"] is True
    else:
        # На Windows свойство hidden читается через st_file_attributes
        assert isinstance(f.metadata()["hidden"], bool)


