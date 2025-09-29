import os
import subprocess
import sys
from typing import Dict, List, Optional

try:
	import winreg  # type: ignore
except ImportError as exc:  # pragma: no cover
	raise RuntimeError("Windows-only module: requires winreg and Windows OS") from exc

# pywin32 imports (optional but preferred)
try:  # pragma: no cover - import path
	import win32api  # type: ignore
	import win32security  # type: ignore
	import win32net  # type: ignore
	import win32netcon  # type: ignore
	_HAS_PYWIN32 = True
except Exception:  # pragma: no cover
	_HAS_PYWIN32 = False

'''
User - пользователь // инициализация пользователя по имени/sid(User(id = ...))
CurUser - текущий пользователь
Users - все пользователи на компьютере

Список атрибутов:
User.id - SID пользователя
User.name - имя пользователя
User.domain - домен пользователя
User.type - тип пользователя

Users.(names / all) - список имен пользователей на компьютере

Список функций:
User(name = "Имя пользователя") - создает объект User
User.create(name = "Имя пользователя", password = "Новый пароль") - создает пользователя ->User
User.password.chg(old = "",new = "") - меняет пароль пользователя
User.delete() - удаляет пользователя

Автозапуск программ:
CurUser
User
Users
     .AutoRun      - автозапуск программы при входе в систему
     .AutoRunOnce  - автозапуск программы один раз
                 .add(name = "Имя программы", path = "Путь к программе") - добавляет программу в автозапуск
                 .remove(name = "Имя программы") - удаляет программу из автозапуска
                 .all - словарь программ в автозапуске (имя - путь)

Добавление в контекстное меню:
CurUser
User
Users
     .ContextMenu - контекстное меню
                 .add(name = "Имя программы", path = "Путь к программе") - добавляет программу в контекстное меню
                 .remove(name = "Имя программы") - удаляет программу из контекстного меню
                 .all - словарь программ в контекстном меню (имя - путь)

Добавление типов файлов(ассоциаций):
CurUser
User
Users
     .FileType  - ассоциации типов файлов
              .add(extension = ".txt", name = "Имя программы", path = "Путь к программе") - добавляет ассоциацию
              .remove(extension = ".txt") - удаляет ассоциацию
              .all - словарь ассоциаций (расширение - программа)
'''

# ------------------------------
# Helpers
# ------------------------------

def _run(cmd: List[str]) -> subprocess.CompletedProcess:
	return subprocess.run(cmd, capture_output=True, text=True, shell=False)


def _powershell(cmd: str) -> str:
	proc = _run(["powershell", "-NoProfile", "-Command", cmd])
	if proc.returncode != 0:
		raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
	return proc.stdout.strip()


def _get_current_user_sid() -> str:
	if _HAS_PYWIN32:
		# Prefer pywin32: use NameSamCompatible to get DOMAIN\User then resolve to SID
		try:
			name_sam = win32api.GetUserNameEx(win32api.NameSamCompatible)
			sid, domain, use = win32security.LookupAccountName(None, name_sam)
			return win32security.ConvertSidToStringSid(sid)
		except Exception:
			pass
	# Fallback to shell
	proc = _run(["whoami", "/user"])
	if proc.returncode != 0:
		return _powershell("(whoami /user | Select-String -Pattern '[A-Z0-9-]+' -AllMatches).Matches[-1].Value")
	lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
	if len(lines) >= 2:
		parts = lines[-1].split()
		return parts[-1]
	raise RuntimeError("Unable to determine current user SID")


def _get_sid_for_account(name: str) -> str:
	if _HAS_PYWIN32:
		try:
			sid, domain, use = win32security.LookupAccountName(None, name)
			return win32security.ConvertSidToStringSid(sid)
		except Exception:
			pass
	# Fallback to PowerShell .NET
	ps = f"([System.Security.Principal.NTAccount]\"{name}\").Translate([System.Security.Principal.SecurityIdentifier]).Value"
	return _powershell(ps)


def _list_local_user_names() -> List[str]:
	if _HAS_PYWIN32:
		try:
			level = 0
			resume = 0
			entries, total, resume = win32net.NetUserEnum(None, level, win32netcon.FILTER_NORMAL_ACCOUNT)
			return [e["name"] for e in entries]
		except Exception:
			pass
	# Fallback to `net user`
	proc = _run(["net", "user"]) 
	if proc.returncode != 0:
		return []
	lines = proc.stdout.splitlines()
	collect = False
	names: List[str] = []
	for ln in lines:
		if collect:
			if ln.strip() == "The command completed successfully.":
				break
			names.extend([x for x in ln.split() if x and x != "The" and x != "command" and x != "completed" and x != "successfully."])
		elif ln.strip().startswith("---"):
			collect = True
	return names


class _RegistryView:
	def __init__(self, root, sub_path: str):
		self.root = root
		self.sub_path = sub_path

	def _open(self, access=winreg.KEY_READ):
		return winreg.OpenKey(self.root, self.sub_path, 0, access)

	def ensure(self):
		winreg.CreateKey(self.root, self.sub_path)

	def set_value(self, name: str, value: str):
		self.ensure()
		with winreg.OpenKey(self.root, self.sub_path, 0, winreg.KEY_SET_VALUE) as hk:
			winreg.SetValueEx(hk, name, 0, winreg.REG_SZ, value)

	def delete_value(self, name: str):
		try:
			with self._open(winreg.KEY_SET_VALUE) as hk:
				winreg.DeleteValue(hk, name)
		except FileNotFoundError:
			pass

	def get_values(self) -> Dict[str, str]:
		values: Dict[str, str] = {}
		try:
			with self._open(winreg.KEY_READ) as hk:
				index = 0
				while True:
					try:
						name, data, _typ = winreg.EnumValue(hk, index)
						values[name or "(Default)"] = data
						index += 1
					except OSError:
						break
		except FileNotFoundError:
			return {}
		return values

	def delete_tree(self):
		try:
			with self._open(winreg.KEY_READ | winreg.KEY_WRITE) as hk:
				# delete subkeys recursively
				while True:
					try:
						sub = winreg.EnumKey(hk, 0)
						winreg.DeleteKey(hk, sub)
					except OSError:
						break
			winreg.DeleteKey(self.root, self.sub_path)
		except FileNotFoundError:
			pass


# ------------------------------
# Feature blocks
# ------------------------------

class _AutoRunBase:
	def __init__(self, root, sid: Optional[str]):
		self.root = root
		self.sid = sid

	def _base_path(self) -> str:
		return r"Software\Microsoft\Windows\CurrentVersion\Run"

	def add(self, name: str, path: str) -> None:
		reg = _RegistryView(self.root, self._base_path())
		reg.set_value(name, path)

	def remove(self, name: str) -> None:
		reg = _RegistryView(self.root, self._base_path())
		reg.delete_value(name)

	@property
	def all(self) -> Dict[str, str]:
		reg = _RegistryView(self.root, self._base_path())
		return reg.get_values()


class _AutoRunOnce(_AutoRunBase):
	def _base_path(self) -> str:
		return r"Software\Microsoft\Windows\CurrentVersion\RunOnce"


class _ContextMenu:
	def __init__(self, root):
		self.root = root

	def _shell_key(self, name: str) -> _RegistryView:
		return _RegistryView(self.root, rf"Software\Classes\*\shell\{name}")

	def add(self, name: str, path: str) -> None:
		key = self._shell_key(name)
		key.ensure()
		cmd_key = _RegistryView(self.root, rf"{key.sub_path}\command")
		cmd_key.set_value("", path)

	def remove(self, name: str) -> None:
		key = self._shell_key(name)
		key.delete_tree()

	@property
	def all(self) -> Dict[str, str]:
		# Enumerate names under shell and read command default
		base = _RegistryView(self.root, r"Software\Classes\*\shell")
		result: Dict[str, str] = {}
		try:
			with winreg.OpenKey(base.root, base.sub_path, 0, winreg.KEY_READ) as hk:
				idx = 0
				while True:
					try:
						name = winreg.EnumKey(hk, idx)
						idx += 1
						cmd = _RegistryView(self.root, rf"{base.sub_path}\{name}\command").get_values().get("(Default)")
						if cmd:
							result[name] = cmd
					except OSError:
						break
		except FileNotFoundError:
			return {}
		return result


class _FileType:
	def __init__(self, root):
		self.root = root

	def _ext_key(self, ext: str) -> _RegistryView:
		if not ext.startswith('.'):
			ext = f'.{ext}'
		return _RegistryView(self.root, rf"Software\Classes\{ext}")

	def add(self, extension: str, name: str, path: str) -> None:
		# Associate extension with a program id (name), and set open command
		ext_key = self._ext_key(extension)
		ext_key.set_value("", name)
		cmd_key = _RegistryView(self.root, rf"Software\Classes\{name}\shell\open\command")
		cmd_key.set_value("", f'"{path}" "%1"')

	def remove(self, extension: str) -> None:
		ext_key = self._ext_key(extension)
		# Determine current association
		assoc = _RegistryView(self.root, ext_key.sub_path).get_values().get("(Default)")
		# Remove extension key
		_RegistryView(self.root, ext_key.sub_path).delete_tree()
		# Optionally remove associated command key
		if assoc:
			_RegistryView(self.root, rf"Software\Classes\{assoc}").delete_tree()

	@property
	def all(self) -> Dict[str, str]:
		# Return mapping: extension -> command (if exists)
		result: Dict[str, str] = {}
		base_path = r"Software\Classes"
		try:
			with winreg.OpenKey(self.root, base_path, 0, winreg.KEY_READ) as hk:
				idx = 0
				while True:
					try:
						name = winreg.EnumKey(hk, idx)
						idx += 1
						if not name.startswith('.'):
							continue
						# read prog id
						prog = _RegistryView(self.root, rf"{base_path}\{name}").get_values().get("(Default)")
						if not prog:
							continue
						cmd = _RegistryView(self.root, rf"{base_path}\{prog}\shell\open\command").get_values().get("(Default)")
						if cmd:
							result[name] = cmd
					except OSError:
						break
		except FileNotFoundError:
			return {}
		return result


# ------------------------------
# Public API
# ------------------------------

class _UserBase:
	def __init__(self, root, sid: Optional[str] = None):
		self._root = root
		self._sid = sid
		# Feature blocks bound to a registry root
		self.AutoRun = _AutoRunBase(root, sid)
		self.AutoRunOnce = _AutoRunOnce(root, sid)
		self.ContextMenu = _ContextMenu(root)
		self.FileType = _FileType(root)


class CurUser(_UserBase):
	def __init__(self):
		# HKCU
		super().__init__(winreg.HKEY_CURRENT_USER, _get_current_user_sid())


class Users(_UserBase):
	def __init__(self):
		# HKLM (all users). Writes may require admin rights.
		super().__init__(winreg.HKEY_LOCAL_MACHINE, None)

	@property
	def names(self) -> List[str]:
		return _list_local_user_names()

	@property
	def all(self) -> List[str]:
		return self.names


class User(_UserBase):
	class _Password:
		def __init__(self, owner: "User"):
			self._owner = owner

		def chg(self, old: str = "", new: str = "") -> None:
			if _HAS_PYWIN32:
				try:
					# Level 1003 allows updating just the password
					win32net.NetUserSetInfo(None, self._owner._name, 1003, {"password": new})
					return
				except Exception as exc:
					raise RuntimeError(str(exc))
			# Fallback
			proc = _run(["net", "user", self._owner._name, new])
			if proc.returncode != 0:
				raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())

	def __init__(self, name: Optional[str] = None, id: Optional[str] = None):
		if not name and not id:
			raise ValueError("Provide user name or sid via id=")
		if id and not name:
			self._sid = id
			self._name = name
		elif name and not id:
			self._name = name
			self._sid = _get_sid_for_account(name)
		else:
			self._name = name
			self._sid = id
		# Bind to HKEY_USERS\<SID>
		root = winreg.HKEY_USERS
		self._hku_path = self._sid
		self._root_handle = root
		# Features for that user hive (read/write if hive is loaded)
		super().__init__(winreg.HKEY_USERS, self._sid)
		# Expose password helper per spec: user.password.chg(...)
		self.password = User._Password(self)

	@property
	def id(self) -> str:
		return self._sid  # SID

	@property
	def name(self) -> Optional[str]:
		return self._name

	@property
	def domain(self) -> Optional[str]:
		if _HAS_PYWIN32:
			try:
				name_sam = win32api.GetUserNameEx(win32api.NameSamCompatible)
				if "\\" in name_sam:
					return name_sam.split("\\", 1)[0]
				return None
			except Exception:
				return None
		# Fallback
		try:
			return _powershell(f"(whoami).Split('\\\\')[0]")
		except Exception:
			return None

	@property
	def type(self) -> Optional[str]:
		if _HAS_PYWIN32:
			try:
				# If account domain equals local computer name -> Local
				comp = win32api.GetComputerName()
				name_sam = win32api.GetUserNameEx(win32api.NameSamCompatible)
				domain = name_sam.split("\\", 1)[0] if "\\" in name_sam else None
				return "Local" if domain and domain.upper() == comp.upper() else None
			except Exception:
				return None
		# Fallback best-effort
		try:
			info = _powershell(f"(Get-LocalUser -Name '{self._name}').Enabled")
			return "Local" if info else None
		except Exception:
			return None

	@staticmethod
	def create(name: str, password: str) -> "User":
		if _HAS_PYWIN32:
			try:
				info = {
					"name": name,
					"password": password,
					"priv": win32netcon.USER_PRIV_USER,
					"home_dir": None,
					"comment": None,
					"flags": win32netcon.UF_SCRIPT,
					"script_path": None,
				}
				win32net.NetUserAdd(None, 1, info)
				return User(name=name)
			except Exception as exc:
				raise RuntimeError(str(exc))
		# Fallback
		proc = _run(["net", "user", name, password, "/add"])
		if proc.returncode != 0:
			raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
		return User(name=name)

	def password_chg(self, new: str) -> None:
		if _HAS_PYWIN32:
			try:
				win32net.NetUserSetInfo(None, self._name, 1003, {"password": new})
				return
			except Exception as exc:
				raise RuntimeError(str(exc))
		proc = _run(["net", "user", self._name, new])
		if proc.returncode != 0:
			raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())

	def delete(self) -> None:
		if _HAS_PYWIN32:
			try:
				win32net.NetUserDel(None, self._name)
				return
			except Exception as exc:
				raise RuntimeError(str(exc))
		proc = _run(["net", "user", self._name, "/delete"])
		if proc.returncode != 0:
			raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
