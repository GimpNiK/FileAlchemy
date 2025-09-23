import sys
from pathlib import Path

import pytest

from FileAlchemy.encoding_utils import check_bom, detect_encoding, determine_minimal_encoding


def test_check_bom_variants():
    assert check_bom(b"\xEF\xBB\xBFhello") == "utf-8-sig"
    assert check_bom(b"\xFF\xFEh\x00") == "utf-16"
    assert check_bom(b"\xFE\xFF\x00h") == "utf-16"
    assert check_bom(b"hello") is None


def test_detect_encoding_uses_bom(tmp_path: Path):
    p = tmp_path / "bom.txt"
    # write UTF-8 with BOM
    p.write_bytes("\ufeffПривет".encode("utf-8-sig"))
    assert detect_encoding(p).lower().startswith("utf-8")


def test_detect_encoding_without_bom(tmp_path: Path):
    p = tmp_path / "plain.txt"
    text = "ASCII only"
    p.write_text(text, encoding="utf-8")
    enc = detect_encoding(p)
    assert isinstance(enc, str)
    assert enc  # non-empty


@pytest.mark.parametrize(
    "content,expected",
    [
        ("abc123", "ascii"),
        ("Привет", "cp1251" if sys.platform.startswith("win") else "utf-8"),
        ("日本語", "utf-8"),
    ],
)
def test_determine_minimal_encoding(content: str, expected: str):
    enc = determine_minimal_encoding(content)
    # На не-Windows платформах cp1251 может не поддерживать японский и кириллицу корректно,
    # поэтому проверяем подсет.
    if expected == "cp1251" and not sys.platform.startswith("win"):
        assert enc in {"cp1251", "utf-8"}
    else:
        assert enc == expected


