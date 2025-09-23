import platform
import os
import shutil
from datetime import datetime,timezone
from typing import Dict,Any
from pathlib import Path
class Dir:
    def __init__(self, path: "Dir|Path|str"):
        if isinstance(path,Dir):
            self = path
        else:
            self.path = Path(path)
            if self.path.suffix !="":
                raise ValueError(f"Путь {path} не является папкой")

    def create(self, mode: int = 0o777, parents: bool = False, ignore_errors: bool = False):
        """Создаёт директорию по указанному пути."""
        self.path.mkdir(mode=mode, parents=parents, exist_ok = ignore_errors)

    def move_to(self,dir : "Dir|Path|str"):
        """Перемещает данную папку в указанную"""
        Dir(dir).create()
        shutil.move(str(self.path),str(dir))
        return self
    def rename(self, new_name: str):
        """Переименовывает папку"""
        new_path = self.path.parent / new_name
        self.path.rename(new_path)
        self.path = new_path

    def chmod(self, mode: int):
        """Изменяет права доступа к файлу или директории."""
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
    
    def __truediv__(self, name: str):
        from .file import File
        if name == "":
            return self
        elif name[-1] == "/" or name[-1] == "\\" and Path(name).suffix =="":
            return Dir(self.path / name)
        else:
            return File(self.path / name)
    def __iter__(self):
        from .file import File
        for path in self.path.iterdir():
            if path.is_file():
                yield File(path)
            elif path.is_dir():
                yield Dir(path)
            else:
                yield path
    def __str__(self):
        return str(self.path) + os.path.sep
    def __repr__(self):
        return f"<Dir: { str(self.path) + os.path.sep}>"
    
    @property
    def name(self) -> str:
        """Имя директории"""
        return self.path.name
    @name.setter
    def name(self,new_name : str):
        self.rename(new_name)

    @property
    def parent(self):
        """Родительская директория"""
        return Dir(self.path.parent)
    @parent.setter
    def parent(self, dir : "Dir|Path|str"):
        self.move_to(dir)
        return Dir(self.path.parent)
    
    @property
    def hidden(self) -> bool:
        if platform.system() == 'Windows':
            try:
                import win32api
                import win32con
                attrs = win32api.GetFileAttributes(str(self.path))
                return bool(attrs & win32con.FILE_ATTRIBUTE_HIDDEN)
            except ImportError:
                raise ImportError("Для изменения скрытости на Windows требуется pywin32")
        else:
            return self.name.startswith('.')

    @hidden.setter
    def hidden(self, value: bool):

        system = platform.system()

        if system == 'Windows':
            try:
                import win32api
                import win32con
                attrs = win32api.GetFileAttributes(str(self.path))
                if value:
                    attrs |= win32con.FILE_ATTRIBUTE_HIDDEN
                else:
                    attrs &= ~win32con.FILE_ATTRIBUTE_HIDDEN
                win32api.SetFileAttributes(str(self.path), attrs) # type: ignore
            except ImportError:
                raise ImportError("Для изменения скрытости на Windows требуется pywin32")
        else:
            # Unix-подобные: скрытые файлы начинаются с точки
            name = self.name
            if value:
                if not name.startswith('.'):
                    self.name = '.' + name
            else:
                if name.startswith('.'):
                    self.name = name[1:]
    
    def len_files_and_dirs(self, recursive: bool = True, symlinks: bool = False) -> Dict[str, int]:
        """Количество элементов в директории"""
        try:
            with os.scandir(self.path) as scan:
                entries = list(scan)
                files = sum(1 for entry in entries if entry.is_file())
                dirs = sum(1 for entry in entries if entry.is_dir())
                return {'files': files, 'subdirectories': dirs, 'total': files + dirs}
        except OSError:
            return {'files': 0, 'subdirectories': 0, 'total': 0}

        
    def sizeof(self, recursive: bool =True, symlink: bool = False) -> int:
        """Размер директории в байтах (рекурсивно)"""
        return sum(f.stat().st_size for f in self.path.rglob('*') if f.is_file())

    
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

    

    def metadata(self) -> Dict[str, Any]:
        """Метаданные директории"""
        return {
            'name': self.name,
            'item_count': self.len_files_and_dirs(),
            'sizeof': self.sizeof(),
            'created_utc': self.created_utc(),
            'modified_utc': self.modified_utc(),
            'accessed_utc': self.accessed_utc(),
            'created_lcl': self.created_lcl(),
            'modified_lcl': self.modified_lcl(),
            'accessed_lcl': self.accessed_lcl(),
            'is_symlink': self.is_symlink(),
            'hidden': self.hidden,
        }