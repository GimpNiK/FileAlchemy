import shutil as sh
import os
import platform
import subprocess
from pathlib import Path
from typing import Optional
import sys
import time
import stat as statmod

def copy(from_path: Path, to_path: Path, follow_symlinks: bool = True):
    """Копирует файл или директорию."""
    if not from_path.exists():
        raise FileNotFoundError(f"Source path '{from_path}' does not exist.")
    if from_path.is_file():
        sh.copy2(from_path, to_path, follow_symlinks=follow_symlinks)
    elif from_path.is_dir():
        sh.copytree(from_path, to_path, dirs_exist_ok=True, symlinks=not follow_symlinks)
    else:
        raise ValueError(f"'{from_path}' is not a valid file or directory.")

def mkdir(path: Path, mode: int = 0o777, parents: bool = False, exist_ok: bool = False):
    """Создаёт директорию по указанному пути."""
    path.mkdir(mode=mode, parents=parents, exist_ok=exist_ok)

def mkfile(path: Path):
    """Создаёт пустой файл по указанному пути."""
    path.touch()

def rmfile(path: Path):
    """Удаляет файл по указанному пути."""
    path.unlink()

def rmdir(path: Path, ignore_errors: bool = False, onexc=None):
    """Рекурсивно удаляет директорию по указанному пути. ignore_errors и onerror передаются полностью."""
    sh.rmtree(path, ignore_errors=ignore_errors, onexc=onexc)

def make_archive(from_path: Path, to_path: Path, format: str = "zip", owner: Optional[str] = None, group: Optional[str] = None):
    """Создаёт архив из директории или файла."""
    base_name = to_path.with_suffix('')
    base_dir = to_path.parent
    if not from_path.exists():
        raise FileNotFoundError(f"Каталог или файл '{from_path}' не найден.")
    sh.make_archive(str(base_name), format,
                   root_dir=str(from_path.parent),
                   base_dir=str(from_path.name),
                   owner=owner, group=group)

def extract_archive(from_path: Path, to_path: Path, format: Optional[str] = None):
    """Распаковывает архив в указанную директорию."""
    if not from_path.exists():
        raise FileNotFoundError(f"Архив '{from_path}' не найден")
    if to_path.exists():
        to_path.mkdir(parents=True, exist_ok=True)
    sh.unpack_archive(from_path, to_path, format)

def chmod(path: Path, mode: int):
    """Изменяет права доступа к файлу или директории."""
    if not path.exists():
        raise FileNotFoundError(f"Путь '{path}' не существует")
    if platform.system() == "Windows":
        try:
            if mode & 0o400:
                os.chmod(path, mode)
        except Exception:
            os.chmod(path, mode)
    else:
        os.chmod(path, mode)

def nano(path: Path, edit_txt="notepad"):
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

def remove(path: Path):
    """Удаляет файл или директорию рекурсивно."""
    if path.is_file() or path.is_symlink():
        path.unlink()
    elif path.is_dir():
        sh.rmtree(path)
    else:
        raise FileNotFoundError(f"Путь '{path}' не найден.")

def make(path: Path, is_file: bool = None):
    """Создаёт все папки в пути и, если нужно, файл."""
    if is_file is None:
        is_file = path.suffix != ""
    if is_file:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
    else:
        path.mkdir(parents=True, exist_ok=True)



def _ls_mode_str(mode):
    # Формирует строку прав доступа как в ls -l
    is_dir = 'd' if statmod.S_ISDIR(mode) else '-'
    perm = ''
    for who in ['USR', 'GRP', 'OTH']:
        for what in ['R', 'W', 'X']:
            perm += (mode & getattr(statmod, f'S_I{what}{who}')) and what.lower() or '-'
    return is_dir + perm

def _ls_owner_group(stat):
    if sys.platform.startswith('win'):
        import getpass
        user = getpass.getuser()
        return user, user
    else:
        import pwd, grp
        try:
            user = pwd.getpwuid(stat.st_uid).pw_name
        except Exception:
            user = str(stat.st_uid)
        try:
            group = grp.getgrgid(stat.st_gid).gr_name
        except Exception:
            group = str(stat.st_gid)
        return user, group

def _ls_time_str(st_mtime):
    t = time.localtime(st_mtime)
    return time.strftime("%b %d  %Y", t)

def ls(path: Path = Path("."), details: bool = False):
    """Возвращает строку: список файлов через пробел или ls -l через перевод строки."""
    if not details:
        return " ".join(str(p.name) for p in path.iterdir())
    result = []
    for p in sorted(path.iterdir()):
        stat = p.stat()
        mode = _ls_mode_str(stat.st_mode)
        nlink = stat.st_nlink
        user, group = _ls_owner_group(stat)
        size = stat.st_size
        mtime = _ls_time_str(stat.st_mtime)
        name = p.name
        line = f"{mode} {nlink} {user} {group} {size:>5} {mtime} {name}"
        result.append(line)
    return "\n".join(result)

