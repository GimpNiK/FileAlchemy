import sys
import os
import tempfile
import shutil
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from FileAlchemy.structures.archive import Archive
from FileAlchemy.structures.file import File
from FileAlchemy.structures.dir import Dir
from FileAlchemy import file_utils as fu
from FileAlchemy.encoding_utils import detect_encoding, determine_minimal_encoding


def test_full_workflow_with_encoding_detection(tmp_path: Path):
    """Полный рабочий процесс с определением кодировки"""
    # Создаем файлы с разными кодировками
    files_content = {
        "ascii.txt": "ASCII content",
        "cyrillic.txt": "Содержимое на русском",
        "japanese.txt": "日本語の内容",
        "emoji.txt": "Содержимое с эмодзи 😊",
    }
    
    # Создаем файлы
    for name, content in files_content.items():
        file_path = tmp_path / name
        # Определяем минимальную кодировку
        encoding = determine_minimal_encoding(content)
        file_path.write_text(content, encoding=encoding)
    
    # Создаем архив
    arc_path = tmp_path / "encoding_test.zip"
    arc = Archive(arc_path, "zip")
    
    for name in files_content:
        arc.add(tmp_path / name)
    
    # Извлекаем архив
    extract_dir = tmp_path / "extract_encoding"
    extract_dir.mkdir(exist_ok=True)
    arc.extract(path=extract_dir)
    
    # Проверяем извлеченные файлы
    for name, original_content in files_content.items():
        extracted_file = extract_dir / name
        assert extracted_file.exists()
        
        # Определяем кодировку извлеченного файла
        detected_encoding = detect_encoding(extracted_file)
        extracted_content = extracted_file.read_text(encoding=detected_encoding)
        
        assert extracted_content == original_content


def test_file_alchemy_objects_integration(tmp_path: Path):
    """Интеграция объектов FileAlchemy"""
    # Создаем структуру с помощью FileAlchemy объектов
    root_dir = Dir(tmp_path / "project")
    root_dir.create()
    
    # Создаем файлы через File объекты
    main_file = File(root_dir.path / "main.py")
    main_file.content = "print('Hello, FileAlchemy!')"
    
    config_file = File(root_dir.path / "config.json")
    config_file.content = '{"encoding": "utf-8", "version": "1.0"}'
    
    # Создаем подпапку
    src_dir = Dir(root_dir.path / "src")
    src_dir.create()
    
    # Создаем файл в подпапке
    module_file = File(src_dir.path / "module.py")
    module_file.content = "def hello():\n    return 'Hello from module'"
    
    # Создаем архив из структуры
    arc_path = tmp_path / "project.zip"
    arc = Archive(arc_path, "zip")
    arc.add(root_dir.path)
    
    # Извлекаем в новое место
    extract_dir = tmp_path / "extracted_project"
    extract_dir.mkdir(exist_ok=True)
    arc.extract(path=extract_dir)
    
    # Проверяем структуру
    assert (extract_dir / "project" / "main.py").exists()
    assert (extract_dir / "project" / "config.json").exists()
    assert (extract_dir / "project" / "src" / "module.py").exists()
    
    # Проверяем содержимое
    main_content = (extract_dir / "project" / "main.py").read_text(encoding="utf-8")
    assert "Hello, FileAlchemy!" in main_content


def test_file_utils_integration(tmp_path: Path):
    """Интеграция с file_utils"""
    # Создаем структуру с помощью file_utils
    project_dir = tmp_path / "utils_project"
    fu.mkdir(project_dir, parents=True)
    
    # Создаем файлы
    fu.mkfile(project_dir / "readme.txt")
    (project_dir / "readme.txt").write_text("Project documentation", encoding="utf-8")
    
    # Создаем подпапки
    fu.mkdir(project_dir / "docs")
    fu.mkdir(project_dir / "src")
    
    # Создаем файлы в подпапках
    (project_dir / "docs" / "guide.txt").write_text("User guide", encoding="utf-8")
    (project_dir / "src" / "main.py").write_text("Main code", encoding="utf-8")
    
    # Создаем архив
    arc_path = tmp_path / "utils_project.zip"
    arc = Archive(arc_path, "zip")
    arc.add(project_dir)
    
    # Извлекаем
    extract_dir = tmp_path / "extracted_utils"
    extract_dir.mkdir(exist_ok=True)
    arc.extract(path=extract_dir)
    
    # Проверяем структуру
    assert (extract_dir / "utils_project" / "readme.txt").exists()
    assert (extract_dir / "utils_project" / "docs" / "guide.txt").exists()
    assert (extract_dir / "utils_project" / "src" / "main.py").exists()


def test_mixed_archive_formats_workflow(tmp_path: Path):
    """Рабочий процесс с разными форматами архивов"""
    # Создаем исходные данные
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    
    files = {
        "text.txt": "Text content",
        "data.json": '{"key": "value"}',
        "script.py": "print('Hello')",
    }
    
    for name, content in files.items():
        (data_dir / name).write_text(content, encoding="utf-8")
    
    # Создаем архивы разных форматов
    formats = ["zip", "7z", "tar", "tar.gz", "tar.bz2"]
    archives = {}
    
    for fmt in formats:
        arc_path = tmp_path / f"data.{fmt}"
        arc = Archive(arc_path, fmt)
        arc.add(data_dir)
        archives[fmt] = arc
    
    # Извлекаем все архивы
    for fmt, arc in archives.items():
        extract_dir = tmp_path / f"extract_{fmt}"
        extract_dir.mkdir(exist_ok=True)
        arc.extract(path=extract_dir)
        
        # Проверяем извлечение
        for name, content in files.items():
            extracted_file = extract_dir / "data" / name
            assert extracted_file.exists()
            assert extracted_file.read_text(encoding="utf-8") == content


def test_password_protected_workflow(tmp_path: Path):
    """Рабочий процесс с защищенными паролем архивами"""
    password = "secure-password-123"
    
    # Создаем конфиденциальные данные
    secret_dir = tmp_path / "secrets"
    secret_dir.mkdir()
    
    secret_files = {
        "credentials.txt": "username: admin\npassword: secret123",
        "config.ini": "[database]\nhost=localhost\nport=5432",
        "private.key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...",
    }
    
    for name, content in secret_files.items():
        (secret_dir / name).write_text(content, encoding="utf-8")
    
    # Создаем защищенный архив
    protected_arc_path = tmp_path / "secrets.zip"
    protected_arc = Archive(protected_arc_path, "zip", password=password)
    protected_arc.add(secret_dir)
    
    # Извлекаем с правильным паролем
    extract_dir = tmp_path / "extract_secrets"
    extract_dir.mkdir(exist_ok=True)
    
    # Пересоздаем объект архива с паролем
    extract_arc = Archive(protected_arc_path, password=password)
    extract_arc.extract(path=extract_dir)
    
    # Проверяем извлечение
    for name, content in secret_files.items():
        extracted_file = extract_dir / "secrets" / name
        assert extracted_file.exists()
        assert extracted_file.read_text(encoding="utf-8") == content


def test_large_project_structure(tmp_path: Path):
    """Тест с большой структурой проекта"""
    # Создаем структуру большого проекта
    project_structure = {
        "README.md": "# Project\nThis is a test project",
        "requirements.txt": "pytest\nrequests\nnumpy",
        "setup.py": "from setuptools import setup\nsetup(name='test')",
        "src/": None,  # Директория
        "src/main.py": "def main():\n    print('Hello')",
        "src/utils.py": "def helper():\n    return True",
        "tests/": None,  # Директория
        "tests/test_main.py": "def test_main():\n    assert True",
        "docs/": None,  # Директория
        "docs/guide.md": "# Guide\nUser guide here",
        "data/": None,  # Директория
        "data/sample.json": '{"test": "data"}',
    }
    
    # Создаем структуру
    for path_str, content in project_structure.items():
        full_path = tmp_path / "large_project" / path_str
        
        if content is None:  # Директория
            full_path.mkdir(parents=True, exist_ok=True)
        else:  # Файл
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
    
    # Создаем архив
    arc_path = tmp_path / "large_project.zip"
    arc = Archive(arc_path, "zip")
    arc.add(tmp_path / "large_project")
    
    # Извлекаем
    extract_dir = tmp_path / "extracted_large"
    extract_dir.mkdir(exist_ok=True)
    arc.extract(path=extract_dir)
    
    # Проверяем структуру
    for path_str, content in project_structure.items():
        if content is not None:  # Файл
            extracted_file = extract_dir / "large_project" / path_str
            assert extracted_file.exists()
            assert extracted_file.read_text(encoding="utf-8") == content


def test_error_recovery_workflow(tmp_path: Path):
    """Рабочий процесс с восстановлением после ошибок"""
    # Создаем валидные данные
    valid_dir = tmp_path / "valid_data"
    valid_dir.mkdir()
    (valid_dir / "file1.txt").write_text("Valid content 1", encoding="utf-8")
    (valid_dir / "file2.txt").write_text("Valid content 2", encoding="utf-8")
    
    # Создаем архив
    arc_path = tmp_path / "recovery_test.zip"
    arc = Archive(arc_path, "zip")
    arc.add(valid_dir)
    
    # Пытаемся извлечь несуществующий файл
    extract_dir = tmp_path / "extract_recovery"
    extract_dir.mkdir(exist_ok=True)
    
    with pytest.raises(ValueError):
        arc.extract(member="nonexistent.txt", path=extract_dir)
    
    # Извлекаем валидные данные
    arc.extract(path=extract_dir)
    
    # Проверяем успешное извлечение
    assert (extract_dir / "valid_data" / "file1.txt").exists()
    assert (extract_dir / "valid_data" / "file2.txt").exists()


def test_cross_platform_compatibility(tmp_path: Path):
    """Тест кроссплатформенной совместимости"""
    # Создаем файлы с именами, которые могут быть проблемными на разных ОС
    problematic_names = [
        "file with spaces.txt",
        "file-with-dashes.txt",
        "file_with_underscores.txt",
        "файл_на_русском.txt",
        "ファイル.txt",
    ]
    
    for name in problematic_names:
        file_path = tmp_path / name
        file_path.write_text(f"Content for {name}", encoding="utf-8")
    
    # Создаем архив
    arc_path = tmp_path / "cross_platform.zip"
    arc = Archive(arc_path, "zip")
    
    for name in problematic_names:
        arc.add(tmp_path / name)
    
    # Извлекаем
    extract_dir = tmp_path / "extract_cross_platform"
    extract_dir.mkdir(exist_ok=True)
    arc.extract(path=extract_dir)
    
    # Проверяем извлечение (имена могут быть нормализованы)
    archive_files = arc.list_files()
    assert len(archive_files) == len(problematic_names)
    
    # Проверяем, что все файлы извлечены
    extracted_files = list(extract_dir.iterdir())
    assert len(extracted_files) == len(problematic_names)


def test_memory_efficient_processing(tmp_path: Path):
    """Тест эффективной обработки памяти"""
    # Создаем много маленьких файлов
    num_files = 100
    files = []
    
    for i in range(num_files):
        file_path = tmp_path / f"small_file_{i:03d}.txt"
        file_path.write_text(f"Content {i}", encoding="utf-8")
        files.append(file_path)
    
    # Создаем архив
    arc_path = tmp_path / "memory_efficient.zip"
    arc = Archive(arc_path, "zip")
    
    # Добавляем файлы по одному (имитация потоковой обработки)
    for file_path in files:
        arc.add(file_path)
    
    # Извлекаем
    extract_dir = tmp_path / "extract_memory_efficient"
    extract_dir.mkdir(exist_ok=True)
    arc.extract(path=extract_dir)
    
    # Проверяем извлечение
    for i in range(num_files):
        assert (extract_dir / f"small_file_{i:03d}.txt").exists()
    
    # Проверяем, что архив содержит все файлы
    assert len(arc.list_files()) == num_files


def test_complex_nested_structure(tmp_path: Path):
    """Тест сложной вложенной структуры"""
    # Создаем глубоко вложенную структуру
    deep_structure = {
        "level1/": None,
        "level1/level2/": None,
        "level1/level2/level3/": None,
        "level1/level2/level3/level4/": None,
        "level1/level2/level3/level4/deep_file.txt": "Deep content",
        "level1/level2/mid_file.txt": "Mid content",
        "level1/top_file.txt": "Top content",
        "parallel/": None,
        "parallel/other_file.txt": "Parallel content",
    }
    
    # Создаем структуру
    for path_str, content in deep_structure.items():
        full_path = tmp_path / "complex" / path_str
        
        if content is None:  # Директория
            full_path.mkdir(parents=True, exist_ok=True)
        else:  # Файл
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
    
    # Создаем архив
    arc_path = tmp_path / "complex_structure.zip"
    arc = Archive(arc_path, "zip")
    arc.add(tmp_path / "complex")
    
    # Извлекаем
    extract_dir = tmp_path / "extract_complex"
    extract_dir.mkdir(exist_ok=True)
    arc.extract(path=extract_dir)
    
    # Проверяем структуру
    for path_str, content in deep_structure.items():
        if content is not None:  # Файл
            extracted_file = extract_dir / "complex" / path_str
            assert extracted_file.exists()
            assert extracted_file.read_text(encoding="utf-8") == content
