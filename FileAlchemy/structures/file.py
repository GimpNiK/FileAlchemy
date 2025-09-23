import os
import stat
from  pathlib import Path
import platform
import subprocess
from datetime import datetime,timezone

from typing import Optional,Union,Dict

from .stream import Stream
from ..encoding_utils import *


class File(Stream):
    """
    Класс для работы с отдельным файлом.
    Позволяет читать, записывать, очищать содержимое и перекодировать файл.
    """
    def __init__(self, path: Path | str, encoding: str = 'utf-8'):
        self.path = Path(path)
        self.encoding = encoding
    
    def __str__(self) -> str:
        """Возвращает путь к файлу в виде строки."""
        return str(self.path)
    
    def __repr__(self) -> str:
        """Возвращает строковое представление объекта с путем и кодировкой."""
        return f"<File: {self.path}, encoding={self.encoding}>"
    
    #переопределение операции потоков
    def __stream_getData__(self):
        return self.content
    def __stream_append__(self, value:str):
        self.content += value
    def __stream_rewrite__(self, value:str):
        self.content = value

    @property
    def content(self) -> str:
        """Содержимое файла как строка (автоматически определяет кодировку при ошибке)."""
        try:
            return self.path.read_text(encoding=self.encoding)
        except UnicodeDecodeError:
            enc = detect_encoding(self.path)
            return self.path.read_text(encoding=enc)
    @content.setter
    def content(self, value: str):
        """Записывает строку в файл, автоматически определяя минимальную подходящую кодировку."""
        min_encoding = determine_minimal_encoding(value)
        try:
            self.path.write_text(value, encoding=min_encoding)
            self.encoding = min_encoding  # Обновляем кодировку файла
        except Exception as e:
            raise IOError(f"Не удалось записать в '{self.path}': {e}")
    @content.deleter
    def content(self):
        """Очищает содержимое файла."""
        try:
            self.path.write_text("", encoding=self.encoding)
        except Exception as e:
            raise IOError(f"Не удалось очистить '{self.path}': {e}")
    
    def create(self, mode: int = 438, ignore_errors: bool = True):
        """Создаёт пустой файл по указанному пути."""
        self.path.touch(mode = mode,exist_ok = ignore_errors)
    def remove(self):
        """Удаляет файл по указанному пути."""
        self.path.unlink()
    def nano(self, edit_txt:str = "notepad"):
        path = self.path
        """Открывает файл в текстовом редакторе."""
        if not path.exists():
            raise FileNotFoundError(f"Файл '{path}' не найден.")
        if platform.system() == "Windows":
            editor_command = ["notepad", str(path)]
        elif platform.system() == "Linux":
            editor_command = ["nano", str(path)]
        elif platform.system() == "Darwin":
            editor_command = ["nano", str(path)]
        else:
            raise OSError(f"Операционная система '{platform.system()}' не поддерживается.")
        subprocess.run(editor_command, check=True)
    
    def chmod(self, mode: int):
        """Изменяет права доступа к файлу."""
        if not self.path.exists():
            raise FileNotFoundError(f"Путь '{self.path}' не существует")
        if platform.system() == "Windows":
            try:
                if mode & 0o400:
                    os.chmod(self.path, mode)
            except Exception:
                os.chmod(self.path, mode)
        else:
            os.chmod(self.path, mode)
    def recode(self, to_encoding: Optional[str] = None, from_encoding: Optional[str] = None):
        """
        Перекодирует файл в другую кодировку.
        :param to_encoding: Целевая кодировка
        :param from_encoding: Исходная кодировка (опционально)
        :return: self._cmd для цепочек вызовов
        """
        try:
            if to_encoding is None:
                    to_encoding = determine_minimal_encoding(self.content)
            if from_encoding is None:
                try:
                    content = self.path.read_text(encoding=self.encoding)
                except UnicodeDecodeError:
                    detected_encoding = detect_encoding(self.path)
                    content = self.path.read_text(encoding=detected_encoding)
            else:
                content = self.path.read_text(encoding=from_encoding)
            self.path.write_text(content, encoding=to_encoding)
            self.encoding = to_encoding
        except Exception as e:
            raise IOError(f"Ошибка перекодировки файла '{self.path}': {e}")

    @property
    def name(self) -> str:
        """Имя файла/директории"""
        return self.path.name

    @property
    def parent(self):
        """Родительская директория"""
        from .dir import Dir
        return Dir(self.path.parent)

    @property
    def extension(self) -> str:
        """Расширение файла (все суффиксы)"""
        suffixes = self.path.suffixes
        return "".join(suffixes) if suffixes else ""

    
    def sizeof(self) -> int:
        """Размер в байтах"""
        return self.path.stat().st_size

    
    def created_utc(self) -> datetime:
        """Время создания в UTC"""
        if platform.system() == 'Windows':
            timestamp = os.path.getctime(self.path)
        else:
            stat = os.stat(self.path)
            timestamp = getattr(stat, 'st_birthtime', stat.st_mtime)
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)

    
    def modified_utc(self) -> datetime:
        """Время последнего изменения в UTC"""
        return datetime.fromtimestamp(os.path.getmtime(self.path), tz=timezone.utc)


    def accessed_utc(self) -> datetime:
        """Время последнего доступа в UTC"""
        return datetime.fromtimestamp(os.path.getatime(self.path), tz=timezone.utc)

    
    def created_lcl(self) -> datetime:
        """Локальное время создания"""
        if platform.system() == 'Windows':
            timestamp = os.path.getctime(self.path)
        else:
            stat = os.stat(self.path)
            timestamp = getattr(stat, 'st_birthtime', stat.st_mtime)
        return datetime.fromtimestamp(timestamp).astimezone()


    def modified_lcl(self) -> datetime:
        """Локальное время последнего изменения"""
        return datetime.fromtimestamp(os.path.getmtime(self.path)).astimezone()
    
    
    def accessed_lcl(self) -> datetime:
        """Локальное время последнего доступа"""
        return datetime.fromtimestamp(os.path.getatime(self.path)).astimezone()


    def is_symlink(self) -> bool:
        """Является ли символьной ссылкой"""
        return self.path.is_symlink()

    @property
    def hidden(self):
        # Проверяем, существует ли файл
        if not os.path.exists(self.path):
            raise FileNotFoundError(f"Файл '{self.path}' не найден.")
        
        # Получаем информацию о файле
        file_info = os.stat(self.path)
        
        # Проверяем на Windows
        if os.name == 'nt':
            # На Windows файл скрыт, если установлен атрибут FILE_ATTRIBUTE_HIDDEN
            return bool(file_info.st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN)
        
        # Проверяем на Unix-подобных системах
        else:
            # На Unix-подобных системах файл скрыт, если его имя начинается с '.'
            return os.path.basename(file_path).startswith('.')


    def metadata(self) -> Dict[str,Union[bool,int,str,datetime]]:
        """Метаданные файла"""
        # Получаем stat один раз для всех свойств
        stat_result = os.stat(self.path)
        
        # Определяем время создания с учетом платформы
        if platform.system() == 'Windows':
            creation_time = os.path.getctime(self.path)
        else:
            creation_time = getattr(stat_result, 'st_birthtime', stat_result.st_mtime)
        
        # Преобразуем timestamp в datetime один раз
        def to_utc(ts:float) -> datetime:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        
        def to_local(ts:float) -> datetime:
            return datetime.fromtimestamp(ts).astimezone()
        
        # Определяем скрытость файла
        is_hidden = (
            bool(stat_result.st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN)
            if os.name == 'nt' 
            else self.path.name.startswith('.')
        ) if hasattr(stat_result, 'st_file_attributes') else self.path.name.startswith('.')
        
        return {
            'name': self.path.name,  # Используем напрямую вместо вызова self.name
            'extension': ''.join(self.path.suffixes),  # Прямой доступ вместо self.extension
            'sizeof': stat_result.st_size,
            'created_utc': to_utc(creation_time),
            'modified_utc': to_utc(stat_result.st_mtime),
            'accessed_utc': to_utc(stat_result.st_atime),
            'created_local': to_local(creation_time),
            'modified_local': to_local(stat_result.st_mtime),
            'accessed_local': to_local(stat_result.st_atime),
            'is_symlink': self.path.is_symlink(),
            'hidden': is_hidden
        }