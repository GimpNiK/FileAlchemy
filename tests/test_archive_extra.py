import sys
import os
import gzip
import bz2
import tempfile
import shutil
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from FileAlchemy.structures.archive import Archive


def _prep_content(tmp_path: Path):
    files = [
        ("a.txt", "A"),
        ("кириллица.txt", "Привет"),
        ("emoji😊.txt", "Содержимое с эмодзи 😊"),
        ("日本語.txt", "日本語の内容"),
    ]
    for n, c in files:
        (tmp_path / n).write_text(c, encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.txt").write_text("B", encoding="utf-8")
    (sub / "nested").mkdir()
    (sub / "nested" / "deep.txt").write_text("deep content", encoding="utf-8")
    return files, sub


@pytest.mark.parametrize("fmt", ["zip", "7z", "tar", "tar.gz", "tar.bz2"])
def test_iter_equals_list_files(tmp_path: Path, fmt: str):
    files, sub = _prep_content(tmp_path)
    arc = Archive(tmp_path / f"arch.{fmt}", fmt)
    for n, _ in files:
        arc.add(tmp_path / n)
    arc.add(sub)
    assert set(iter(arc)) == set(arc.list_files())


def test_extract_member_not_found_raises(tmp_path: Path):
    arc = Archive(tmp_path / "a.zip", "zip").create()
    with pytest.raises(ValueError):
        arc.extract(member="nope", path=tmp_path / "out")


def test_create_from_validates_format(tmp_path: Path):
    with pytest.raises(NotImplementedError):
        Archive.create_from(tmp_path / "x.xyz", "xyz", files=[])


def test_gz_bz2_support(tmp_path: Path):
    src = tmp_path / "file.bin"
    src.write_bytes(b"data")
    gz = tmp_path / "file.gz"
    with gzip.open(gz, "wb") as f:
        f.write(src.read_bytes())
    bz = tmp_path / "file.bz2"
    with bz2.open(bz, "wb") as f:
        f.write(src.read_bytes())

    for p in [gz, bz]:
        arc = Archive(p)
        out = tmp_path / (p.stem + "_out")
        out.mkdir(exist_ok=True)
        arc.extract(path=out)
        assert (out / "file").exists()


@pytest.mark.parametrize("fmt", ["zip", "7z", "tar", "tar.gz", "tar.bz2"])
def test_archive_roundtrip_with_special_chars(tmp_path: Path, fmt: str):
    """Тест полного цикла: создание → добавление → извлечение с особыми символами"""
    files, sub = _prep_content(tmp_path)
    arc_path = tmp_path / f"special.{fmt}"
    arc = Archive(arc_path, fmt)
    
    # Добавляем все файлы и папку
    for name, _ in files:
        arc.add(tmp_path / name)
    arc.add(sub)
    
    # Извлекаем
    extract_dir = tmp_path / f"extract_{fmt}"
    extract_dir.mkdir(exist_ok=True)
    arc.extract(path=extract_dir)
    
    # Проверяем все файлы
    for name, content in files:
        extracted_file = extract_dir / name
        assert extracted_file.exists(), f"Файл {name} не извлечен из {fmt}"
        assert extracted_file.read_text(encoding="utf-8") == content
    
    # Проверяем вложенную структуру
    assert (extract_dir / "sub" / "b.txt").exists()
    assert (extract_dir / "sub" / "nested" / "deep.txt").exists()


@pytest.mark.parametrize("fmt", ["zip", "7z"])
def test_password_protection_detailed(tmp_path: Path, fmt: str):
    """Детальный тест защиты паролем"""
    password = "секрет-пароль😊"
    files, _ = _prep_content(tmp_path)
    
    # Создаем защищенный архив
    arc_path = tmp_path / f"protected.{fmt}"
    arc = Archive(arc_path, fmt, password=password)
    
    for name, _ in files:
        arc.add(tmp_path / name)
    
    # Извлекаем с правильным паролем
    extract_dir = tmp_path / f"extract_correct_{fmt}"
    extract_dir.mkdir(exist_ok=True)
    arc_correct = Archive(arc_path, password=password)
    arc_correct.extract(path=extract_dir)
    
    # Проверяем извлечение
    for name, content in files:
        extracted_file = extract_dir / name
        assert extracted_file.exists()
        assert extracted_file.read_text(encoding="utf-8") == content
    
    # Пытаемся извлечь без пароля
    with pytest.raises(Exception):
        extract_wrong_dir = tmp_path / f"extract_wrong_{fmt}"
        extract_wrong_dir.mkdir(exist_ok=True)
        arc_no_pass = Archive(arc_path)
        arc_no_pass.extract(path=extract_wrong_dir)
    
    # Пытаемся извлечь с неправильным паролем
    with pytest.raises(Exception):
        extract_wrong_dir = tmp_path / f"extract_bad_pass_{fmt}"
        extract_wrong_dir.mkdir(exist_ok=True)
        arc_bad_pass = Archive(arc_path, password="неправильный")
        arc_bad_pass.extract(path=extract_wrong_dir)


@pytest.mark.parametrize("fmt", ["zip", "7z", "tar", "tar.gz", "tar.bz2"])
def test_large_file_handling(tmp_path: Path, fmt: str):
    """Тест работы с большими файлами"""
    # Создаем файл размером 1MB
    large_file = tmp_path / "large.bin"
    with open(large_file, "wb") as f:
        f.write(os.urandom(1024 * 1024))
    
    arc_path = tmp_path / f"large.{fmt}"
    arc = Archive(arc_path, fmt)
    arc.add(large_file)
    
    # Извлекаем
    extract_dir = tmp_path / f"extract_large_{fmt}"
    extract_dir.mkdir(exist_ok=True)
    arc.extract(path=extract_dir)
    
    # Проверяем размер
    extracted_file = extract_dir / "large.bin"
    assert extracted_file.exists()
    assert extracted_file.stat().st_size == large_file.stat().st_size


@pytest.mark.parametrize("fmt", ["zip", "7z", "tar", "tar.gz", "tar.bz2"])
def test_deep_directory_structure(tmp_path: Path, fmt: str):
    """Тест глубокой вложенности директорий"""
    # Создаем глубокую структуру
    deep_path = tmp_path / "level1" / "level2" / "level3" / "level4"
    deep_path.mkdir(parents=True, exist_ok=True)
    
    # Добавляем файлы на разных уровнях
    (tmp_path / "level1" / "file1.txt").write_text("level1", encoding="utf-8")
    (tmp_path / "level1" / "level2" / "file2.txt").write_text("level2", encoding="utf-8")
    (deep_path / "file4.txt").write_text("level4", encoding="utf-8")
    
    arc_path = tmp_path / f"deep.{fmt}"
    arc = Archive(arc_path, fmt)
    arc.add(tmp_path / "level1")
    
    # Извлекаем
    extract_dir = tmp_path / f"extract_deep_{fmt}"
    extract_dir.mkdir(exist_ok=True)
    arc.extract(path=extract_dir)
    
    # Проверяем структуру
    assert (extract_dir / "level1" / "file1.txt").exists()
    assert (extract_dir / "level1" / "level2" / "file2.txt").exists()
    assert (extract_dir / "level1" / "level2" / "level3" / "level4" / "file4.txt").exists()


@pytest.mark.parametrize("fmt", ["zip", "7z", "tar", "tar.gz", "tar.bz2"])
def test_add_with_custom_arcname(tmp_path: Path, fmt: str):
    """Тест добавления файлов с кастомными именами в архиве"""
    files, _ = _prep_content(tmp_path)
    arc_path = tmp_path / f"custom.{fmt}"
    arc = Archive(arc_path, fmt)
    
    # Добавляем файлы с кастомными именами
    for i, (name, _) in enumerate(files):
        arc.add(tmp_path / name, arcname=f"custom_{i}_{name}")
    
    # Проверяем имена в архиве
    archive_files = arc.list_files()
    for i, (name, _) in enumerate(files):
        expected_name = f"custom_{i}_{name}"
        assert expected_name in archive_files
    
    # Извлекаем и проверяем
    extract_dir = tmp_path / f"extract_custom_{fmt}"
    extract_dir.mkdir(exist_ok=True)
    arc.extract(path=extract_dir)
    
    for i, (name, content) in enumerate(files):
        extracted_file = extract_dir / f"custom_{i}_{name}"
        assert extracted_file.exists()
        assert extracted_file.read_text(encoding="utf-8") == content


@pytest.mark.parametrize("fmt", ["zip", "7z", "tar", "tar.gz", "tar.bz2"])
def test_extract_specific_members(tmp_path: Path, fmt: str):
    """Тест извлечения конкретных файлов"""
    files, sub = _prep_content(tmp_path)
    arc_path = tmp_path / f"selective.{fmt}"
    arc = Archive(arc_path, fmt)
    
    # Добавляем файлы и папку
    for name, _ in files:
        arc.add(tmp_path / name)
    arc.add(sub, arcname="custom_sub")
    
    # Извлекаем только один файл
    extract_dir = tmp_path / f"extract_selective_{fmt}"
    extract_dir.mkdir(exist_ok=True)
    arc.extract(member=files[0][0], path=extract_dir)
    
    # Проверяем, что извлечен только нужный файл
    assert (extract_dir / files[0][0]).exists()
    for name, _ in files[1:]:
        assert not (extract_dir / name).exists()
    
    # Извлекаем папку
    extract_dir2 = tmp_path / f"extract_folder_{fmt}"
    extract_dir2.mkdir(exist_ok=True)
    arc.extract(member="custom_sub", path=extract_dir2)
    
    assert (extract_dir2 / "custom_sub" / "b.txt").exists()


def test_archive_cleanup_after_operations(tmp_path: Path):
    """Тест очистки временных файлов после операций"""
    files, _ = _prep_content(tmp_path)
    
    # Тестируем на tar архивах, которые используют временные директории
    for fmt in ["tar", "tar.gz", "tar.bz2"]:
        arc_path = tmp_path / f"cleanup.{fmt}"
        arc = Archive(arc_path, fmt)
        
        # Добавляем файлы (создает временные директории)
        for name, _ in files:
            arc.add(tmp_path / name)
        
        # Проверяем, что временные директории очищены
        temp_dirs = list(tmp_path.glob("~temp_*"))
        assert len(temp_dirs) == 0, f"Временные директории не очищены для {fmt}"


@pytest.mark.parametrize("fmt", ["zip", "7z", "tar", "tar.gz", "tar.bz2"])
def test_empty_archive_operations(tmp_path: Path, fmt: str):
    """Тест операций с пустыми архивами"""
    arc_path = tmp_path / f"empty.{fmt}"
    arc = Archive(arc_path, fmt)
    
    # Создаем пустой архив
    arc.create()
    assert arc_path.exists()
    assert len(arc.list_files()) == 0
    
    # Пытаемся извлечь из пустого архива
    extract_dir = tmp_path / f"extract_empty_{fmt}"
    extract_dir.mkdir(exist_ok=True)
    arc.extract(path=extract_dir)
    
    # Директория должна остаться пустой
    assert len(list(extract_dir.iterdir())) == 0


def test_archive_format_detection():
    """Тест автоматического определения формата архива"""
    test_cases = [
        ("test.zip", "zip"),
        ("test.7z", "7z"),
        ("test.tar", "tar"),
        ("test.tar.gz", "tar.gz"),
        ("test.tgz", "tar.gz"),
        ("test.tar.bz2", "tar.bz2"),
        ("test.tbz2", "tar.bz2"),
        ("test.gz", "gz"),
        ("test.bz2", "bz2"),
        ("test.rar", "rar"),
    ]
    
    for filename, expected_format in test_cases:
        arc = Archive(filename)
        assert arc.format == expected_format, f"Неправильный формат для {filename}"


def test_archive_with_mixed_content_types(tmp_path: Path):
    """Тест архива с разными типами контента"""
    # Создаем файлы разных типов
    (tmp_path / "text.txt").write_text("Текст", encoding="utf-8")
    (tmp_path / "binary.bin").write_bytes(b"\x00\x01\x02\x03")
    (tmp_path / "empty.txt").write_text("", encoding="utf-8")
    
    # Создаем папку с файлами
    subdir = tmp_path / "mixed"
    subdir.mkdir()
    (subdir / "nested.txt").write_text("Вложенный", encoding="utf-8")
    (subdir / "nested.bin").write_bytes(b"\xFF\xFE")
    
    for fmt in ["zip", "7z", "tar", "tar.gz", "tar.bz2"]:
        arc_path = tmp_path / f"mixed.{fmt}"
        arc = Archive(arc_path, fmt)
        
        # Добавляем все
        arc.add(tmp_path / "text.txt")
        arc.add(tmp_path / "binary.bin")
        arc.add(tmp_path / "empty.txt")
        arc.add(subdir)
        
        # Извлекаем
        extract_dir = tmp_path / f"extract_mixed_{fmt}"
        extract_dir.mkdir(exist_ok=True)
        arc.extract(path=extract_dir)
        
        # Проверяем все файлы
        assert (extract_dir / "text.txt").read_text(encoding="utf-8") == "Текст"
        assert (extract_dir / "binary.bin").read_bytes() == b"\x00\x01\x02\x03"
        assert (extract_dir / "empty.txt").read_text(encoding="utf-8") == ""
        assert (extract_dir / "mixed" / "nested.txt").read_text(encoding="utf-8") == "Вложенный"
        assert (extract_dir / "mixed" / "nested.bin").read_bytes() == b"\xFF\xFE"


