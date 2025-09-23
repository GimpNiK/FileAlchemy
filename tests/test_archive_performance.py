import sys
import os
import time
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from FileAlchemy.structures.archive import Archive


@pytest.mark.parametrize("fmt", ["zip", "7z", "tar", "tar.gz", "tar.bz2"])
def test_archive_creation_performance(tmp_path: Path, fmt: str):
    """Тест производительности создания архивов"""
    # Создаем тестовые файлы
    files = []
    for i in range(50):
        file_path = tmp_path / f"perf_file_{i:03d}.txt"
        content = f"Performance test content {i} " * 100  # ~2KB per file
        file_path.write_text(content, encoding="utf-8")
        files.append(file_path)
    
    arc_path = tmp_path / f"performance.{fmt}"
    arc = Archive(arc_path, fmt)
    
    # Измеряем время создания
    start_time = time.time()
    for file_path in files:
        arc.add(file_path)
    creation_time = time.time() - start_time
    
    # Проверяем, что архив создан
    assert arc_path.exists()
    # Фильтруем только файлы (не директории)
    archive_files = arc.list_files()
    file_count = len([f for f in archive_files if not f.endswith('/') and f != '.'])
    assert file_count == 50, f"Ожидалось 50 файлов, получено {file_count} для {fmt}"
    
    # Логируем время (для отладки)
    print(f"Создание архива {fmt}: {creation_time:.2f} секунд")


@pytest.mark.parametrize("fmt", ["zip", "7z", "tar", "tar.gz", "tar.bz2"])
def test_archive_extraction_performance(tmp_path: Path, fmt: str):
    """Тест производительности извлечения архивов"""
    # Создаем архив с файлами
    files = []
    for i in range(30):
        file_path = tmp_path / f"extract_file_{i:03d}.txt"
        content = f"Extraction test content {i} " * 200  # ~4KB per file
        file_path.write_text(content, encoding="utf-8")
        files.append(file_path)
    
    arc_path = tmp_path / f"extraction_perf.{fmt}"
    arc = Archive(arc_path, fmt)
    
    for file_path in files:
        arc.add(file_path)
    
    # Измеряем время извлечения
    extract_dir = tmp_path / f"extract_perf_{fmt}"
    extract_dir.mkdir(exist_ok=True)
    
    start_time = time.time()
    arc.extract(path=extract_dir)
    extraction_time = time.time() - start_time
    
    # Проверяем извлечение
    for i in range(30):
        assert (extract_dir / f"extract_file_{i:03d}.txt").exists()
    
    print(f"Извлечение архива {fmt}: {extraction_time:.2f} секунд")


def test_archive_compression_ratios(tmp_path: Path):
    """Тест коэффициентов сжатия разных форматов"""
    # Создаем файлы с разным типом контента
    test_files = {
        "text_repetitive.txt": "Hello World " * 1000,  # Повторяющийся текст
        "text_random.txt": "".join(chr(ord('a') + i % 26) for i in range(1000)),  # Случайный текст
        "numbers.txt": "1234567890" * 100,  # Числа
        "mixed.txt": "Text with numbers 123 and symbols !@#$%^&*() " * 50,  # Смешанный контент
    }
    
    for name, content in test_files.items():
        (tmp_path / name).write_text(content, encoding="utf-8")
    
    original_size = sum((tmp_path / name).stat().st_size for name in test_files)
    
    compression_ratios = {}
    
    for fmt in ["zip", "7z", "tar", "tar.gz", "tar.bz2"]:
        arc_path = tmp_path / f"compression.{fmt}"
        arc = Archive(arc_path, fmt)
        
        for name in test_files:
            arc.add(tmp_path / name)
        
        compressed_size = arc_path.stat().st_size
        ratio = (1 - compressed_size / original_size) * 100
        compression_ratios[fmt] = ratio
        
        print(f"Сжатие {fmt}: {ratio:.1f}% (размер: {compressed_size} байт)")
    
        # Проверяем, что сжатие работает (tar без сжатия может быть больше оригинала)
        compressed_formats = ["zip", "7z", "tar.gz", "tar.bz2"]
        for fmt in compressed_formats:
            if fmt in compression_ratios:  # Проверяем, что формат был протестирован
                assert compression_ratios[fmt] > 0, f"Формат {fmt} не сжимает данные"


def test_archive_memory_efficiency(tmp_path: Path):
    """Тест эффективности использования памяти"""
    # Создаем большой файл
    large_file = tmp_path / "large_memory_test.bin"
    chunk_size = 1024 * 1024  # 1MB
    total_size = 5 * chunk_size  # 5MB
    
    with open(large_file, "wb") as f:
        for _ in range(5):
            f.write(os.urandom(chunk_size))
    
    for fmt in ["zip", "7z", "tar", "tar.gz", "tar.bz2"]:
        arc_path = tmp_path / f"memory_efficiency.{fmt}"
        arc = Archive(arc_path, fmt)
        
        # Добавляем большой файл
        start_time = time.time()
        arc.add(large_file)
        add_time = time.time() - start_time
        
        # Извлекаем
        extract_dir = tmp_path / f"extract_memory_{fmt}"
        extract_dir.mkdir(exist_ok=True)
        
        start_time = time.time()
        arc.extract(path=extract_dir)
        extract_time = time.time() - start_time
        
        # Проверяем целостность
        extracted_file = extract_dir / "large_memory_test.bin"
        assert extracted_file.exists()
        assert extracted_file.stat().st_size == total_size
        
        print(f"Память {fmt}: добавление {add_time:.2f}с, извлечение {extract_time:.2f}с")


def test_archive_streaming_large_content(tmp_path: Path):
    """Тест потоковой обработки большого контента"""
    # Создаем файл, который генерируется по частям
    streaming_file = tmp_path / "streaming.txt"
    
    # Генерируем контент по частям
    with open(streaming_file, "w", encoding="utf-8") as f:
        for i in range(1000):
            f.write(f"Line {i}: " + "x" * 100 + "\n")
    
    file_size = streaming_file.stat().st_size
    
    for fmt in ["zip", "7z", "tar", "tar.gz", "tar.bz2"]:
        arc_path = tmp_path / f"streaming.{fmt}"
        arc = Archive(arc_path, fmt)
        
        # Измеряем время добавления
        start_time = time.time()
        arc.add(streaming_file)
        add_time = time.time() - start_time
        
        # Измеряем время извлечения
        extract_dir = tmp_path / f"extract_streaming_{fmt}"
        extract_dir.mkdir(exist_ok=True)
        
        start_time = time.time()
        arc.extract(path=extract_dir)
        extract_time = time.time() - start_time
        
        # Проверяем целостность
        extracted_file = extract_dir / "streaming.txt"
        assert extracted_file.exists()
        assert extracted_file.stat().st_size == file_size
        
        print(f"Поток {fmt}: добавление {add_time:.2f}с, извлечение {extract_time:.2f}с")


def test_archive_batch_operations_performance(tmp_path: Path):
    """Тест производительности пакетных операций"""
    # Создаем много маленьких файлов
    batch_size = 100
    files = []
    
    for i in range(batch_size):
        file_path = tmp_path / f"batch_{i:03d}.txt"
        file_path.write_text(f"Batch content {i}", encoding="utf-8")
        files.append(file_path)
    
    for fmt in ["zip", "7z", "tar", "tar.gz", "tar.bz2"]:
        arc_path = tmp_path / f"batch.{fmt}"
        
        # Измеряем время создания архива из списка файлов
        start_time = time.time()
        arc = Archive.create_from(arc_path, fmt, files)
        creation_time = time.time() - start_time
        
        # Измеряем время извлечения всех файлов
        extract_dir = tmp_path / f"extract_batch_{fmt}"
        extract_dir.mkdir(exist_ok=True)
        
        start_time = time.time()
        arc.extract(path=extract_dir)
        extraction_time = time.time() - start_time
        
        # Проверяем результат (фильтруем только файлы)
        archive_files = arc.list_files()
        file_count = len([f for f in archive_files if not f.endswith('/') and f != '.'])
        assert file_count == batch_size, f"Ожидалось {batch_size} файлов, получено {file_count} для {fmt}"
        
        for i in range(batch_size):
            assert (extract_dir / f"batch_{i:03d}.txt").exists()
        
        print(f"Пакет {fmt}: создание {creation_time:.2f}с, извлечение {extraction_time:.2f}с")


def test_archive_concurrent_operations_simulation(tmp_path: Path):
    """Симуляция конкурентных операций с архивами"""
    # Создаем несколько архивов с одинаковыми файлами
    base_files = []
    for i in range(20):
        file_path = tmp_path / f"concurrent_{i:03d}.txt"
        file_path.write_text(f"Concurrent content {i}", encoding="utf-8")
        base_files.append(file_path)
    
    # Создаем несколько архивов "одновременно"
    archives = []
    for i in range(5):
        arc_path = tmp_path / f"concurrent_arc_{i}.zip"
        arc = Archive(arc_path, "zip")
        archives.append(arc)
        
        # Добавляем файлы
        for file_path in base_files:
            arc.add(file_path)
    
    # Извлекаем из всех архивов "одновременно"
    total_extract_time = 0
    for i, arc in enumerate(archives):
        extract_dir = tmp_path / f"extract_concurrent_{i}"
        extract_dir.mkdir(exist_ok=True)
        
        start_time = time.time()
        arc.extract(path=extract_dir)
        extract_time = time.time() - start_time
        total_extract_time += extract_time
        
        # Проверяем извлечение
        for j in range(20):
            assert (extract_dir / f"concurrent_{j:03d}.txt").exists()
    
    print(f"Конкурентное извлечение: {total_extract_time:.2f}с общее время")


def test_archive_error_recovery_performance(tmp_path: Path):
    """Тест производительности восстановления после ошибок"""
    # Создаем валидный архив
    valid_file = tmp_path / "valid.txt"
    valid_file.write_text("Valid content", encoding="utf-8")
    
    arc_path = tmp_path / "recovery.zip"
    arc = Archive(arc_path, "zip")
    arc.add(valid_file)
    
    # Измеряем время обработки ошибок
    error_times = []
    
    # Тест с несуществующим файлом
    start_time = time.time()
    try:
        arc.add(tmp_path / "nonexistent.txt")
    except FileNotFoundError:
        pass
    error_times.append(time.time() - start_time)
    
    # Тест с неправильным паролем
    start_time = time.time()
    try:
        wrong_arc = Archive(arc_path, password="wrong")
        wrong_arc.extract(path=tmp_path / "out")
    except Exception:
        pass
    error_times.append(time.time() - start_time)
    
    # Тест с несуществующим архивом
    start_time = time.time()
    try:
        Archive(tmp_path / "nonexistent.zip").extract(path=tmp_path / "out")
    except FileNotFoundError:
        pass
    error_times.append(time.time() - start_time)
    
    # Проверяем, что ошибки обрабатываются быстро
    for i, error_time in enumerate(error_times):
        assert error_time < 1.0, f"Ошибка {i} обрабатывается слишком медленно: {error_time:.2f}с"
    
    print(f"Время обработки ошибок: {[f'{t:.3f}с' for t in error_times]}")


def test_archive_format_comparison(tmp_path: Path):
    """Сравнение производительности разных форматов"""
    # Создаем тестовые данные
    test_data = {
        "small_files": [(tmp_path / f"small_{i}.txt").write_text(f"Small {i}", encoding="utf-8") 
                        for i in range(50)],
        "medium_files": [(tmp_path / f"medium_{i}.txt").write_text(f"Medium content {i} " * 100, encoding="utf-8") 
                         for i in range(20)],
        "large_file": (tmp_path / "large.txt").write_text("Large content " * 10000, encoding="utf-8"),
    }
    
    results = {}
    
    for fmt in ["zip", "7z", "tar", "tar.gz", "tar.bz2"]:
        arc_path = tmp_path / f"comparison.{fmt}"
        arc = Archive(arc_path, fmt)
        
        # Измеряем время создания
        start_time = time.time()
        
        # Добавляем все файлы
        for i in range(50):
            arc.add(tmp_path / f"small_{i}.txt")
        for i in range(20):
            arc.add(tmp_path / f"medium_{i}.txt")
        arc.add(tmp_path / "large.txt")
        
        creation_time = time.time() - start_time
        
        # Измеряем время извлечения
        extract_dir = tmp_path / f"extract_comparison_{fmt}"
        extract_dir.mkdir(exist_ok=True)
        
        start_time = time.time()
        arc.extract(path=extract_dir)
        extraction_time = time.time() - start_time
        
        # Размер архива
        archive_size = arc_path.stat().st_size
        
        results[fmt] = {
            "creation_time": creation_time,
            "extraction_time": extraction_time,
            "archive_size": archive_size,
        }
    
    # Выводим результаты
    print("\nСравнение форматов:")
    print("Формат | Создание | Извлечение | Размер")
    print("-" * 45)
    for fmt, data in results.items():
        print(f"{fmt:6} | {data['creation_time']:8.2f}с | {data['extraction_time']:9.2f}с | {data['archive_size']:6} байт")
    
    # Проверяем, что все форматы работают (7z может быть медленнее)
    for fmt, data in results.items():
        if fmt == "7z":
            assert data["creation_time"] < 20, f"7z слишком медленный: {data['creation_time']:.2f}с"
        else:
            assert data["creation_time"] < 15, f"{fmt} слишком медленный: {data['creation_time']:.2f}с"
    assert all(data["extraction_time"] < 10 for data in results.values())
