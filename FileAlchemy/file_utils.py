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
    """Copies a file or directory."""
    if not from_path.exists():
        raise FileNotFoundError(f"Source path '{from_path}' does not exist.")
    if from_path.is_file():
        sh.copy2(from_path, to_path, follow_symlinks=follow_symlinks)
    elif from_path.is_dir():
        sh.copytree(from_path, to_path, dirs_exist_ok=True, symlinks=not follow_symlinks)
    else:
        raise ValueError(f"'{from_path}' is not a valid file or directory.")

def mkdir(path: Path, mode: int = 0o777, parents: bool = False, exist_ok: bool = False):
    """Creates a directory at the specified path."""
    path.mkdir(mode=mode, parents=parents, exist_ok=exist_ok)

def mkfile(path: Path):
    """Creates an empty file at the specified path."""
    path.touch()

def rmfile(path: Path):
    """Deletes the file at the specified path."""
    path.unlink()

def rmdir(path: Path, ignore_errors: bool = False, onerror=None):
    """Recursively deletes a directory at the specified path.
    The ignore_errors and onerror parameters are passed through."""
    sh.rmtree(path, ignore_errors=ignore_errors, onerror=onerror)

def make_archive(from_path: Path, to_path: Path, format: str = "zip", owner: Optional[str] = None, group: Optional[str] = None):
    """Creates an archive from a directory or file."""
    base_name = to_path.with_suffix('')
    base_dir = to_path.parent
    if not from_path.exists():
        raise FileNotFoundError(f"Directory or file '{from_path}' not found.")
    sh.make_archive(str(base_name), format,
                    root_dir=str(from_path.parent),
                    base_dir=str(from_path.name),
                    owner=owner, group=group)

def extract_archive(from_path: Path, to_path: Path, format: Optional[str] = None):
    """Extracts an archive into the specified directory."""
    if not from_path.exists():
        raise FileNotFoundError(f"Archive '{from_path}' not found.")
    if to_path.exists():
        to_path.mkdir(parents=True, exist_ok=True)
    sh.unpack_archive(from_path, to_path, format)

def chmod(path: Path, mode: int):
    """Changes access permissions of a file or directory."""
    if not path.exists():
        raise FileNotFoundError(f"Path '{path}' does not exist.")
    if platform.system() == "Windows":
        try:
            if mode & 0o400:
                os.chmod(path, mode)
        except Exception:
            os.chmod(path, mode)
    else:
        os.chmod(path, mode)

def nano(path: Path, edit_txt="notepad"):
    """Opens a file in a text editor."""
    if not path.exists():
        raise FileNotFoundError(f"File '{path}' not found.")
    if platform.system() == "Windows":
        editor_command = ["notepad", str(path)]
    elif platform.system() == "Linux":
        editor_command = ["nano", str(path)]
    elif platform.system() == "Darwin":
        editor_command = ["nano", str(path)]
    else:
        raise OSError(f"Operating system '{platform.system()}' is not supported.")
    subprocess.run(editor_command, check=True)

def remove(path: Path):
    """Recursively deletes a file or directory."""
    if path.is_file() or path.is_symlink():
        path.unlink()
    elif path.is_dir():
        sh.rmtree(path)
    else:
        raise FileNotFoundError(f"Path '{path}' not found.")

def make(path: Path, is_file: bool = None):
    """Creates all folders in the path and, if needed, a file."""
    if is_file is None:
        is_file = path.suffix != ""
    if is_file:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
    else:
        path.mkdir(parents=True, exist_ok=True)

def _ls_mode_str(mode):
    # Builds a permission string like 'ls -l'
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
    """Returns a string: list of files separated by spaces or ls -l style listing separated by new lines."""
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
