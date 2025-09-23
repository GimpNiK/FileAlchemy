import zipfile
import py7zr
import tarfile
import rarfile  # type: ignore[import-not-found]
import shutil
import os
import gzip
import bz2
import sys
from pathlib import Path
from typing import Union, Optional, List, Iterator, Any, cast

class Archive:
    """
    Унифицированный интерфейс для работы с различными архивными форматами.
    Поддерживаемые форматы и операции:
        - zip: создание, добавление, извлечение (с поддержкой паролей)
        - 7z: создание, добавление, извлечение (с поддержкой паролей)
        - tar: создание, добавление, извлечение
        - tar.gz/tgz: создание, добавление, извлечение
        - tar.bz2/tbz2: создание, добавление, извлечение
        - gz: только чтение и извлечение (один файл)
        - bz2: только чтение и извлечение (один файл)
        - rar: только чтение и извлечение (с поддержкой паролей)
    """

    def __init__(self, path: Union[Path, str], format: Optional[str] = None, password: Optional[str] = None):
        """
        Инициализирует объект архива.
        
        Параметры:
        path - путь к архиву
        format - явное указание формата (опционально)
        password - пароль для защищенных архивов (опционально)
        """
        self.path = Path(path)
        self.password = password  # Храним пароль как строку
        self.temp_dir = None  # Для временных операций с 7z

        # Автоматическое определение формата по расширению файла
        suffixes = self.path.suffixes
        if format is None:
            if not suffixes:
                raise ValueError(f"Формат архива для {self.path} не определен. Укажите формат или используйте стандартное расширение.")

            ext_map = {
                '.zip': 'zip',
                '.7z': '7z',
                '.tar': 'tar',
                '.gz': 'gz',
                '.bz2': 'bz2',
                '.rar': 'rar',
                '.tgz': 'tar.gz',
                '.tbz2': 'tar.bz2'
            }

            if len(suffixes) >= 2:
                compound_ext = ''.join(suffixes[-2:])
                if compound_ext in ('.tar.gz', '.tar.bz2'):
                    self.format = ext_map.get(compound_ext, compound_ext[1:])
                else:
                    self.format = ext_map.get(suffixes[-1], suffixes[-1][1:])
            else:
                self.format = ext_map.get(suffixes[-1], suffixes[-1][1:])
        else:
            self.format = format.lower()

    def cleanup(self):
        """Удаляет временные файлы, используемые при операциях с 7z архивами."""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None

    def __iter__(self) -> Iterator[str]:
        """
        Итератор по содержимому архива.
        Возвращает имена файлов/папок в архиве.
        """
        if self.format == 'zip':
            try:
                # Используем pyzipper для корректной поддержки паролей при чтении zip
                import pyzipper  # type: ignore[import-not-found]
                with pyzipper.AESZipFile(self.path, 'r') as zf:  # type: ignore[reportUnknownMemberType]
                    if self.password:
                        zf.pwd = self.password.encode('utf-8')
                    for name in zf.namelist():
                        yield name.replace('\\', '/')
            except Exception:
                # Fallback на стандартный zipfile
                with zipfile.ZipFile(self.path, 'r') as zf:
                    for name in zf.namelist():
                        yield name.replace('\\', '/')
        elif self.format == '7z':
            with py7zr.SevenZipFile(self.path, 'r', password=self.password) as zf:
                for name in zf.getnames():
                    yield name.replace('\\', '/')
        elif self.format in ('tar', 'tar.gz', 'tar.bz2'):
            mode = 'r:' + self.format.split('.')[-1] if '.' in self.format else 'r'
            with tarfile.open(self.path, mode) as tf:
                for from_path in tf.getmembers():
                    yield from_path.name.replace('\\', '/')
        elif self.format == 'rar':
            if rarfile is None:  # type: ignore[reportConstantCondition]
                raise ImportError("RAR support requires the 'rarfile' package")
            with rarfile.RarFile(self.path, 'r') as rf:  # type: ignore[reportUnknownMemberType]
                for name in rf.namelist():  # type: ignore[reportUnknownMemberType]
                    yield str(cast(Any, name)).replace('\\', '/')
        elif self.format in ('gz', 'bz2'):
            yield self.path.stem
        else:
            raise NotImplementedError(f"Итерация не поддерживается для {self.format}")

    def add(self, path: Union[Path, str], arcname: Optional[str] = None):
        """
        Добавляет файл или директорию в архив.
        
        Параметры:
        path - путь к добавляемому файлу/директории
        arcname - имя в архиве (опционально)
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Источник не найден: {path}")

        # Обработка директорий
        if path.is_dir():
            return self._add_directory(path, arcname)

        arcname = arcname or path.name

        if self.format == 'zip':
            if self.password:
                # Используем pyzipper для записи зашифрованных файлов
                try:
                    import pyzipper  # type: ignore[import-not-found]
                except Exception as e:
                    raise RuntimeError("Для записи zip с паролем требуется пакет 'pyzipper'") from e
                with pyzipper.AESZipFile(self.path, 'a', compression=zipfile.ZIP_DEFLATED) as zf:  # type: ignore[reportUnknownMemberType]
                    zf.setpassword(self.password.encode('utf-8'))
                    try:
                        zf.setencryption(pyzipper.WZ_AES, nbits=256)
                    except Exception:
                        pass
                    zf.writestr(arcname, Path(path).read_bytes())
            else:
                with zipfile.ZipFile(self.path, 'a', compression=zipfile.ZIP_DEFLATED) as zf:
                    zf.write(path, arcname)

        elif self.format == '7z':
            self._add_to_7z(path, arcname)

        elif self.format in ('tar', 'tar.gz', 'tar.bz2'):
            # Для сжатых tar используем режим записи вместо добавления
            if self.path.exists():
                self._add_to_tar(path, arcname)
            else:
                mode = 'w:' + self.format.split('.')[-1] if '.' in self.format else 'w'
                with tarfile.open(self.path, mode) as tf:
                    tf.add(path, arcname=arcname)

        else:
            raise NotImplementedError(f"Добавление не поддерживается для {self.format}")

    def _add_directory(self, path: Path, arcroot: Optional[str] = None):
        """
        Внутренний метод для добавления директории в архив.
        
        Параметры:
        path - путь к директории
        arcroot - корневое имя в архиве (опционально)
        """
        arcroot = arcroot or path.name

        if self.format == 'zip':
            if self.password:
                try:
                    import pyzipper  # type: ignore[import-not-found]
                except Exception as e:
                    raise RuntimeError("Для записи zip с паролем требуется пакет 'pyzipper'") from e
                with pyzipper.AESZipFile(self.path, 'a', compression=zipfile.ZIP_DEFLATED) as zf:  # type: ignore[reportUnknownMemberType]
                    zf.setpassword(self.password.encode('utf-8'))
                    try:
                        zf.setencryption(pyzipper.WZ_AES, nbits=256)
                    except Exception:
                        pass
                    for item in path.rglob('*'):
                        if item.is_file():
                            rel_path = item.relative_to(path)
                            arcname = str(Path(arcroot) / rel_path).replace(os.sep, '/')
                            zf.writestr(arcname, item.read_bytes())
            else:
                with zipfile.ZipFile(self.path, 'a', compression=zipfile.ZIP_DEFLATED) as zf:
                    for item in path.rglob('*'):
                        if item.is_file():
                            rel_path = item.relative_to(path)
                            arcname = str(Path(arcroot) / rel_path).replace(os.sep, '/')
                            zf.write(item, arcname)

        elif self.format == '7z':
            temp_dir = self._prepare_7z_temp()
            dest = temp_dir / arcroot
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(path, dest)
            self._recreate_7z(temp_dir)

        elif self.format in ('tar', 'tar.gz', 'tar.bz2'):
            # Для сжатых tar используем режим записи вместо добавления
            if self.path.exists():
                self._add_dir_to_tar(path, arcroot)
            else:
                mode = 'w:' + self.format.split('.')[-1] if '.' in self.format else 'w'
                with tarfile.open(self.path, mode) as tf:
                    tf.add(path, arcname=arcroot)

        else:
            raise NotImplementedError(f"Добавление директорий не поддерживается для {self.format}")

    def _add_to_tar(self, path: Path, arcname: str):
        """
        Добавляет файл в существующий tar-архив путем пересоздания.
        
        Параметры:
        path - путь к файлу
        arcname - имя в архиве
        """
        temp_dir = self._prepare_tar_temp()
        dest = temp_dir / arcname
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        self._recreate_tar(temp_dir)

    def _add_dir_to_tar(self, path: Path, arcroot: str):
        """
        Добавляет директорию в существующий tar-архив путем пересоздания.
        
        Параметры:
        path - путь к директории
        arcroot - корневое имя в архиве
        """
        temp_dir = self._prepare_tar_temp()
        dest = temp_dir / arcroot
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(path, dest)
        self._recreate_tar(temp_dir)

    def _prepare_tar_temp(self) -> Path:
        """
        Подготавливает временную директорию для операций с tar архивами.
        Возвращает путь к временной директории.
        """
        self.cleanup()
        self.temp_dir = self.path.parent / f"~temp_{self.path.stem}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        if self.path.exists():
            mode = 'r:' + self.format.split('.')[-1] if '.' in self.format else 'r'
            with tarfile.open(self.path, mode) as tf:
                # Для Python 3.12+ используем фильтр
                if sys.version_info >= (3, 12):
                    tf.extractall(path=self.temp_dir, filter='data')
                else:
                    tf.extractall(path=self.temp_dir)

        return self.temp_dir

    def _recreate_tar(self, temp_dir: Path):
        """
        Пересоздает tar-архив из временной директории.
        
        Параметры:
        temp_dir - путь к временной директории с содержимым
        """
        mode = 'w:' + self.format.split('.')[-1] if '.' in self.format else 'w'
        with tarfile.open(self.path, mode) as tf:
            for item in temp_dir.iterdir():
                tf.add(item, arcname=item.name)
        self.cleanup()

    def _add_to_7z(self, path: Path, arcname: str):
        """
        Добавляет файл в 7z архив через временную директорию.
        
        Параметры:
        path - путь к файлу
        arcname - имя в архиве
        """
        temp_dir = self._prepare_7z_temp()
        dest = temp_dir / arcname
        
        # Удаляем существующий файл/директорию
        if dest.exists():
            if dest.is_dir():
                shutil.rmtree(dest)
            else:
                dest.unlink()
                
        # Создаем родительскую директорию
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)

        self._recreate_7z(temp_dir)

    def _prepare_7z_temp(self) -> Path:
        """
        Подготавливает временную директорию для операций с 7z архивами.
        Возвращает путь к временной директории.
        """
        self.cleanup()
        self.temp_dir = self.path.parent / f"~temp_{self.path.stem}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        if self.path.exists():
            with py7zr.SevenZipFile(self.path, 'r', password=self.password) as zf:
                zf.extractall(path=self.temp_dir)

        return self.temp_dir

    def _recreate_7z(self, temp_dir: Path):
        """
        Пересоздает 7z архив из временной директории.
        
        Параметры:
        temp_dir - путь к временной директории с содержимым
        """
        with py7zr.SevenZipFile(self.path, 'w', password=self.password) as zf:
            zf.writeall(temp_dir, arcname='')
        self.cleanup()

    def extract(self, member: Optional[str] = None, path: Union[Path, str] = '.'):
        """
        Извлекает содержимое архива или конкретный элемент.
        
        Параметры:
        from_path - конкретный файл/директория для извлечения (опционально)
        to_path - целевая директория для извлечения (по умолчанию текущая)
        """
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        if self.format == 'zip':
            # Используем pyzipper для корректной поддержки паролей при извлечении
            try:
                import pyzipper  # type: ignore[import-not-found]
                with pyzipper.AESZipFile(self.path, 'r') as zf:  # type: ignore[reportUnknownMemberType]
                    if self.password:
                        zf.pwd = self.password.encode('utf-8')
                    if member:
                        all_files = zf.namelist()
                        targets = [f for f in all_files if f == member or f.startswith(member + '/')]
                        if not targets:
                            raise ValueError(f"Элемент '{member}' не найден в архиве")
                        for file in targets:
                            zf.extract(file, path)
                    else:
                        zf.extractall(path)
            except Exception:
                with zipfile.ZipFile(self.path, 'r') as zf:
                    if member:
                        all_files = zf.namelist()
                        targets = [f for f in all_files if f == member or f.startswith(member + '/')]
                        if not targets:
                            raise ValueError(f"Элемент '{member}' не найден в архиве")
                        for file in targets:
                            zf.extract(file, path)
                    else:
                        zf.extractall(path)

        elif self.format == '7z':
            with py7zr.SevenZipFile(self.path, 'r', password=self.password) as zf:
                if member:
                    all_files = zf.getnames()
                    targets = [f for f in all_files if f == member or f.startswith(member + '/')]
                    if not targets:
                        raise ValueError(f"Элемент '{member}' не найден в архиве")
                    zf.extract(targets=targets, path=path)
                else:
                    zf.extractall(path)

        elif self.format in ('tar', 'tar.gz', 'tar.bz2'):
            mode = 'r:' + self.format.split('.')[-1] if '.' in self.format else 'r'
            with tarfile.open(self.path, mode) as tf:
                if member:
                    members: List[tarfile.TarInfo] = []
                    for m in tf.getmembers():
                        if m.name == member or m.name.startswith(member + '/'):
                            members.append(m)
                    if not members:
                        raise ValueError(f"Элемент '{member}' не найден в архиве")
                    
                    # Обработка предупреждений в Python 3.12+
                    if sys.version_info >= (3, 12):
                        tf.extractall(path=path, members=members, filter='data')
                    else:
                        tf.extractall(path=path, members=members)
                else:
                    if sys.version_info >= (3, 12):
                        tf.extractall(path=path, filter='data')
                    else:
                        tf.extractall(path=path)

        elif self.format == 'rar':
            with rarfile.RarFile(self.path, 'r') as rf:  # type: ignore[reportUnknownMemberType]
                if member:
                    all_members: List[str] = list(rf.namelist())  # type: ignore[reportUnknownMemberType]
                    targets: List[str] = [m for m in all_members if m == member or m.startswith(member + '/')]
                    if not targets:
                        raise ValueError(f"Элемент '{member}' не найден в архиве")
                    cast(Any, rf).extractall(path=path, members=targets, pwd=self.password)  # type: ignore[no-any-return]
                else:
                    cast(Any, rf).extractall(path=path, pwd=self.password)  # type: ignore[no-any-return]

        elif self.format == 'gz':
            output_file = path / self.path.stem
            with gzip.open(self.path, 'rb') as f_in:
                with open(output_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

        elif self.format == 'bz2':
            output_file = path / self.path.stem
            with bz2.open(self.path, 'rb') as f_in:
                with open(output_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

        else:
            raise NotImplementedError(f"Извлечение не поддерживается для {self.format}")

    def list_files(self) -> List[str]:
        """Возвращает список файлов в архиве."""
        return list(self.__iter__())

    
    def create(self):
        """
        Создает пустой архив.
        """

        # Создаем пустой архив
        if self.format == 'zip':
            try:
                if self.password:
                    import pyzipper  # type: ignore[import-not-found]
                    with pyzipper.AESZipFile(self.path, 'w', compression=zipfile.ZIP_DEFLATED) as _:
                        _.setpassword(self.password.encode('utf-8'))
                        try:
                            _.setencryption(pyzipper.WZ_AES, nbits=256)
                        except Exception:
                            pass
                else:
                    with zipfile.ZipFile(self.path, 'w', compression=zipfile.ZIP_DEFLATED) as _:
                        pass
            except Exception:
                with zipfile.ZipFile(self.path, 'w', compression=zipfile.ZIP_DEFLATED) as _:
                    pass
        elif self.format == '7z':
            with py7zr.SevenZipFile(self.path, 'w', password=self.password) as _:
                pass
        elif self.format in ('tar', 'tar.gz', 'tar.bz2'):
            mode = 'w'
            if self.format == 'tar.gz':
                mode = 'w:gz'
            elif self.format == 'tar.bz2':
                mode = 'w:bz2'
            with tarfile.open(self.path, mode) as _:
                pass
        return self
    
    @classmethod
    def create_from(cls, path: Union[Path, str], format: str, files: List[Union[Path, str]], password: Optional[str] = None):
        """
        Создает новый архив с указанными файлами.
        
        Параметры:
        path - путь к создаваемому архиву
        format - формат архива
        files - список файлов/директорий для добавления
        password - пароль (опционально)
        
        Возвращает объект Archive.
        """
        archive = cls(path, format, password)
        
        # Поддерживаемые форматы для создания
        supported_formats = ['zip', '7z', 'tar', 'tar.gz', 'tar.bz2']
        
        if format not in supported_formats:
            raise NotImplementedError(f"Создание архивов формата {format} не поддерживается")

        # Создаем пустой архив, если файлов нет
        if not files:
            if format == 'zip':  # type: ignore[reportConstantCondition]
                with zipfile.ZipFile(archive.path, 'w') as _:
                    pass  # Создаем пустой zip-архив
            elif format == '7z':  # type: ignore[reportConstantCondition]
                with py7zr.SevenZipFile(archive.path, 'w', password=password) as _:
                    pass  # Создаем пустой 7z-архив
            elif format in ('tar', 'tar.gz', 'tar.bz2'):  # type: ignore[reportConstantCondition]
                mode = 'w'
                if format == 'tar.gz':
                    mode = 'w:gz'
                elif format == 'tar.bz2':
                    mode = 'w:bz2'
                with tarfile.open(archive.path, mode) as _:
                    pass  # Создаем пустой tar-архив
            return archive

        # Добавляем файлы, если они есть
        for item in files:
            item = Path(item)
            if item.is_dir():
                archive._add_directory(item)
            else:
                archive.add(item)
        return archive
    
import unittest
import os as _os  # type: ignore[unused-import]
import shutil as _shutil  # type: ignore[unused-import]
import tempfile
import sys as _sys  # type: ignore[unused-import]
from pathlib import Path

class TestArchive(unittest.TestCase):
    def setUp(self):
        # Создаем временную директорию
        self.test_dir = Path(tempfile.mkdtemp())
        
        # Создаем тестовые файлы с разными кодировками
        self.files = [
            ('file_ascii.txt', 'ASCII content'),
            ('file_кириллица.txt', 'Содержимое на русском'),
            ('file_日本語.txt', '日本語の内容'),
            ('file_العربية.txt', 'محتوَى عربي'),
            ('file_emoji😊.txt', 'Содержимое с эмодзи 😊')
        ]
        
        for name, content in self.files:
            (self.test_dir / name).write_text(content, encoding='utf-8')
        
        # Создаем вложенные директории
        self.dirs = [
            'dir_ascii',
            'dir_кириллица',
            'dir_日本語',
            'dir_العربية',
            'dir_emoji😊'
        ]
        
        for dir_name in self.dirs:
            dir_path = self.test_dir / dir_name
            dir_path.mkdir(exist_ok=True)
            
            for name, content in self.files:
                file_path = dir_path / name
                file_path.write_text(f"{dir_name}/{content}", encoding='utf-8')
        
        # Создаем глубоко вложенную структуру
        self.deep_dir = self.test_dir / 'deep' / 'dir1' / 'dir2' / 'dir3'
        self.deep_dir.mkdir(parents=True, exist_ok=True)
        (self.deep_dir / 'deep_file.txt').write_text('Deep content', encoding='utf-8')
        
        # Создаем большой файл
        self.large_file = self.test_dir / 'large_file.bin'
        with open(self.large_file, 'wb') as f:
            f.write(os.urandom(2 * 1024 * 1024))  # 2MB

    def tearDown(self):
        # Удаляем временную директорию
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_create_empty_archive(self):
        """Тестирование создания пустых архивов"""
        formats = ['zip', '7z', 'tar', 'tar.gz', 'tar.bz2']
        
        for fmt in formats:
            archive_path = self.test_dir / f'empty_{fmt}.{fmt}'
            archive = Archive(archive_path, fmt)
            archive.create()
            
            # Проверяем что файл архива создан и не пустой
            self.assertTrue(archive_path.exists(), f"Файл архива {fmt} не создан")
            self.assertGreater(archive_path.stat().st_size, 0, f"Пустой архив {fmt} имеет нулевой размер")
            
            # Проверяем что архив действительно пустой
            self.assertEqual(len(archive.list_files()), 0, f"Пустой архив {fmt} содержит файлы")
    
    def test_add_files_to_archive(self):
        """Тестирование добавления файлов в архив"""
        formats = ['zip', '7z', 'tar', 'tar.gz', 'tar.bz2']
        
        for fmt in formats:
            archive_path = self.test_dir / f'test_add.{fmt}'
            archive = Archive(archive_path, fmt)
            
            # Добавляем файлы
            for file in self.files:
                file_path = self.test_dir / file[0]
                archive.add(file_path)
            
            # Проверяем содержимое
            files_in_archive = archive.list_files()
            for file in self.files:
                # Для tar-архивов добавляется относительный путь
                if fmt.startswith('tar'):
                    self.assertIn(file[0], files_in_archive)
                else:
                    self.assertIn(file[0], files_in_archive)
    
    def test_add_directory_to_archive(self):
        """Тестирование добавления директорий в архив"""
        formats = ['zip', '7z', 'tar', 'tar.gz', 'tar.bz2']
        
        for fmt in formats:
            archive_path = self.test_dir / f'test_add_dir.{fmt}'
            archive = Archive(archive_path, fmt)
            
            # Добавляем директорию
            dir_path = self.test_dir / self.dirs[0]
            archive.add(dir_path)
            
            # Проверяем содержимое
            files_in_archive = archive.list_files()
            for file in self.files:
                # Формируем ожидаемый путь с учетом формата
                expected_path = f"{self.dirs[0]}/{file[0]}"
                # Для Windows заменяем разделители
                if sys.platform == 'win32':
                    expected_path = expected_path.replace('/', '\\')
                
                # Проверяем наличие файла в архиве
                self.assertIn(expected_path, files_in_archive, 
                             f"Файл {expected_path} отсутствует в архиве {fmt}")
    
    def test_extract_files(self):
        """Тестирование извлечения файлов"""
        formats = ['zip', '7z', 'tar', 'tar.gz', 'tar.bz2']
        
        for fmt in formats:
            # Создаем архив
            archive_path = self.test_dir / f'test_extract.{fmt}'
            archive = Archive(archive_path, fmt)
            
            # Добавляем файл и директорию
            archive.add(self.test_dir / self.files[0][0])
            archive.add(self.test_dir / self.dirs[0])
            
            # Извлекаем
            extract_dir = self.test_dir / f'extract_{fmt}'
            extract_dir.mkdir(exist_ok=True)
            archive.extract(path=extract_dir)
            
            # Проверяем извлеченные файлы
            self.assertTrue((extract_dir / self.files[0][0]).exists(),
                           f"Файл не извлечен из архива {fmt}")
            self.assertTrue((extract_dir / self.dirs[0] / self.files[0][0]).exists(),
                           f"Файл в директории не извлечен из архива {fmt}")
    
    def test_password_protection(self):
        """Тестирование работы с паролями"""
        formats = ['zip', '7z']  # Только эти форматы поддерживают пароли
        password = 'secret-пароль😊'
        test_file = self.test_dir / self.files[0][0]
        
        for fmt in formats:
            # Создаем защищенный архив
            archive_path = self.test_dir / f'protected.{fmt}'
            archive = Archive(archive_path, fmt, password)
            archive.add(test_file)
            
            # Извлекаем с правильным паролем
            extract_dir = self.test_dir / f'extract_protected_{fmt}'
            extract_dir.mkdir(exist_ok=True)
            archive = Archive(archive_path, password=password)
            archive.extract(path=extract_dir)
            self.assertTrue((extract_dir / test_file.name).exists(),
                           f"Файл не извлечен с правильным паролем из {fmt}")
            
            # Проверяем извлечение без пароля
            with self.assertRaises(Exception, msg=f"Для {fmt} без пароля не возникло исключения"):
                extract_fail_dir = self.test_dir / f'extract_fail_{fmt}'
                extract_fail_dir.mkdir(exist_ok=True)
                archive_no_pass = Archive(archive_path)
                archive_no_pass.extract(path=extract_fail_dir)
            
            # Проверяем извлечение с неправильным паролем
            with self.assertRaises(Exception, msg=f"Для {fmt} с неправильным паролем не возникло исключения"):
                extract_fail_dir = self.test_dir / f'extract_wrong_pass_{fmt}'
                extract_fail_dir.mkdir(exist_ok=True)
                archive_wrong_pass = Archive(archive_path, password='wrong-password')
                archive_wrong_pass.extract(path=extract_fail_dir)
    
    def test_special_characters(self):
        """Тестирование работы со специальными символами"""
        formats = ['zip', '7z', 'tar', 'tar.gz', 'tar.bz2']
        test_file = self.test_dir / 'file_кириллица.txt'
        
        for fmt in formats:
            # Создаем архив
            archive_path = self.test_dir / f'test_special_{fmt}.{fmt}'
            archive = Archive(archive_path, fmt)
            archive.add(test_file)
            
            # Извлекаем
            extract_dir = self.test_dir / f'extract_special_{fmt}'
            extract_dir.mkdir(exist_ok=True)
            archive.extract(path=extract_dir)
            
            # Проверяем файл
            extracted_file = extract_dir / test_file.name
            self.assertTrue(extracted_file.exists(),
                          f"Файл не извлечен из архива {fmt}")
            self.assertEqual(
                extracted_file.read_text(encoding='utf-8'),
                test_file.read_text(encoding='utf-8'),
                f"Содержимое файла не совпадает после извлечения из {fmt}"
            )
    
    def test_deep_structure(self):
        """Тестирование глубокой вложенности"""
        formats = ['zip', '7z', 'tar', 'tar.gz', 'tar.bz2']
        test_file = self.deep_dir / 'deep_file.txt'
        
        for fmt in formats:
            # Создаем архив
            archive_path = self.test_dir / f'test_deep_{fmt}.{fmt}'
            archive = Archive(archive_path, fmt)
            
            # Добавляем корневую директорию чтобы сохранить структуру
            archive.add(self.test_dir / 'deep')
            
            # Извлекаем
            extract_dir = self.test_dir / f'extract_deep_{fmt}'
            extract_dir.mkdir(exist_ok=True)
            archive.extract(path=extract_dir)
            
            # Проверяем файл
            extracted_file = extract_dir / 'deep' / 'dir1' / 'dir2' / 'dir3' / 'deep_file.txt'
            self.assertTrue(extracted_file.exists(),
                          f"Файл не извлечен из архива {fmt}")
            self.assertEqual(
                extracted_file.read_text(encoding='utf-8'),
                test_file.read_text(encoding='utf-8'),
                f"Содержимое файла не совпадает после извлечения из {fmt}"
            )
    
    def test_large_file(self):
        """Тестирование работы с большими файлами"""
        formats = ['zip', '7z', 'tar', 'tar.gz', 'tar.bz2']
        
        for fmt in formats:
            # Создаем архив
            archive_path = self.test_dir / f'test_large_{fmt}.{fmt}'
            archive = Archive(archive_path, fmt)
            archive.add(self.large_file)
            
            # Извлекаем
            extract_dir = self.test_dir / f'extract_large_{fmt}'
            extract_dir.mkdir(exist_ok=True)
            archive.extract(path=extract_dir)
            
            # Проверяем файл
            extracted_file = extract_dir / self.large_file.name
            self.assertTrue(extracted_file.exists(),
                          f"Файл не извлечен из архива {fmt}")
            self.assertEqual(
                extracted_file.stat().st_size,
                self.large_file.stat().st_size,
                f"Размер файла не совпадает после извлечения из {fmt}"
            )

if __name__ == '__main__':
    unittest.main()