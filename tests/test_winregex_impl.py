import types
import builtins
import pytest

try:
	import FileAlchemy.Windows.regedit as wr
except Exception:
	import FileAlchemy.winregex as wr


class FakeReg:
	KEY_READ = 0x20019
	KEY_WRITE = 0x20006
	KEY_SET_VALUE = 0x0002

	class Error(Exception):
		pass

	def __init__(self):
		self.store = {}

	class Handle:
		def __init__(self, path):
			self.path = path
		def __enter__(self):
			return self
		def __exit__(self, exc_type, exc, tb):
			return False

	def _norm(self, root, sub):
		root_name = 'HKCU' if root == 'HKCU' else 'HKLM' if root == 'HKLM' else 'HKU'
		return f"{root_name}\\{sub}" if sub else root_name

	def CreateKey(self, root, sub):
		key = self._norm(root, sub)
		self.store.setdefault(key, {"values": {}, "subs": set()})
		# ensure parent has this as sub
		if '\\' in key:
			parent = key.rsplit('\\', 1)[0]
			self.store.setdefault(parent, {"values": {}, "subs": set()})
			self.store[parent]["subs"].add(key)
		return self.Handle(key)

	def OpenKey(self, root, sub, _=0, __=0):
		key = self._norm(root, sub)
		if key not in self.store:
			raise FileNotFoundError
		return self.Handle(key)

	def SetValueEx(self, handle, name, _r, _t, value):
		self.store.setdefault(handle.path, {"values": {}, "subs": set()})
		self.store[handle.path]["values"][name] = value

	def EnumValue(self, handle, index):
		items = list(self.store.get(handle.path, {"values": {}})["values"].items())
		if index >= len(items):
			raise OSError
		name, val = items[index]
		return name, val, None

	def EnumKey(self, handle, index):
		subs = list(self.store.get(handle.path, {"subs": set()})["subs"])
		if index >= len(subs):
			raise OSError
		return subs[index].split('\\')[-1]

	def DeleteValue(self, handle, name):
		try:
			del self.store[handle.path]["values"][name]
		except Exception:
			raise FileNotFoundError

	def DeleteKey(self, root, sub):
		key = self._norm(root, sub)
		if key in self.store:
			# remove from parent subs
			if '\\' in key:
				parent = key.rsplit('\\', 1)[0]
				if parent in self.store:
					self.store[parent]["subs"].discard(key)
			del self.store[key]
		else:
			raise FileNotFoundError


class FakeProc:
	def __init__(self, rc=0, out='', err=''):
		self.returncode = rc
		self.stdout = out
		self.stderr = err


def fake_run_factory(users_state):
	def fake_run(cmd, capture_output=True, text=True, shell=False):
		if cmd[:2] == ["whoami", "/user"]:
			return FakeProc(0, "\nUSER INFORMATION\n----------------\nname sid S-1-5-123\n")
		if cmd and cmd[0] == "powershell":
			# return simple string
			return FakeProc(0, "S-1-5-123")
		if cmd[:2] == ["net", "user"] and len(cmd) == 2:
			# list users
			names = users_state["names"]
			body = "\n".join(["----------", "  ".join(names), "The command completed successfully."])
			return FakeProc(0, body)
		if cmd[:2] == ["net", "user"] and any(arg == "/add" for arg in cmd):
			name = cmd[2]
			if name not in users_state["names"]:
				users_state["names"].append(name)
			return FakeProc(0, "User added")
		if cmd[:2] == ["net", "user"] and any(arg == "/delete" for arg in cmd):
			name = cmd[2]
			if name in users_state["names"]:
				users_state["names"].remove(name)
			return FakeProc(0, "User deleted")
		if cmd[:2] == ["net", "user"] and len(cmd) >= 4 and "/add" not in cmd and "/delete" not in cmd:
			# change password
			return FakeProc(0, "Password changed")
		return FakeProc(0, "")
	return fake_run


@pytest.fixture()
def fake_env(monkeypatch):
	# Force module to use shell fallbacks instead of pywin32 paths for deterministic tests
	monkeypatch.setattr(wr, "_HAS_PYWIN32", False, raising=False)
	# Patch subprocess runner used by module
	users_state = {"names": ["Admin", "Guest"]}
	monkeypatch.setattr(wr, "_run", fake_run_factory(users_state))
	monkeypatch.setattr(wr, "_powershell", lambda cmd: "S-1-5-123")
	# Fake registry
	freg = FakeReg()
	# Patch symbols used inside module
	monkeypatch.setattr(wr, "winreg", types.SimpleNamespace(
		KEY_READ=freg.KEY_READ,
		KEY_WRITE=freg.KEY_WRITE,
		KEY_SET_VALUE=freg.KEY_SET_VALUE,
		REG_SZ=1,
		OpenKey=freg.OpenKey,
		CreateKey=freg.CreateKey,
		SetValueEx=freg.SetValueEx,
		EnumValue=freg.EnumValue,
		EnumKey=freg.EnumKey,
		DeleteValue=freg.DeleteValue,
		DeleteKey=freg.DeleteKey,
		HKEY_CURRENT_USER='HKCU',
		HKEY_LOCAL_MACHINE='HKLM',
		HKEY_USERS='HKU',
	))
	return freg, users_state


def test_curuser_and_users_listing(fake_env):
	_, users_state = fake_env
	cu = wr.CurUser()
	assert isinstance(cu.AutoRun.all, dict)
	us = wr.Users()
	assert set(us.names) == set(users_state["names"]) 
	assert set(us.all) == set(users_state["names"]) 


def test_autorun_and_autorunonce(fake_env):
	freg, _ = fake_env
	cu = wr.CurUser()
	cu.AutoRun.add("AppA", r"C:\\AppA.exe")
	cu.AutoRun.add("AppB", r"C:\\AppB.exe")
	assert "AppA.exe" in cu.AutoRun.all["AppA"]
	cu.AutoRun.remove("AppA")
	assert "AppA" not in cu.AutoRun.all

	cu.AutoRunOnce.add("Once", r"C:\\Once.exe")
	assert "Once.exe" in cu.AutoRunOnce.all["Once"]
	cu.AutoRunOnce.remove("Once")
	assert "Once" not in cu.AutoRunOnce.all


def test_context_menu_add_remove_and_list(fake_env):
	freg, _ = fake_env
	cu = wr.CurUser()
	cu.ContextMenu.add("OpenWithX", r"C:\\X.exe \"%1\"")
	cu.ContextMenu.add("DoY", r"C:\\Y.exe \"%1\"")
	all_items = cu.ContextMenu.all
	assert "X.exe" in all_items["OpenWithX"]
	assert "Y.exe" in all_items["DoY"]
	cu.ContextMenu.remove("OpenWithX")
	assert "OpenWithX" not in cu.ContextMenu.all


def test_filetype_association_add_list_remove(fake_env):
	freg, _ = fake_env
	cu = wr.CurUser()
	cu.FileType.add(extension=".abc", name="ABCApp", path=r"C:\\ABC.exe")
	assocs = cu.FileType.all
	assert ".abc" in assocs
	assert "ABC.exe" in assocs[".abc"]
	cu.FileType.remove(".abc")
	assert ".abc" not in cu.FileType.all


def test_user_create_password_change_delete(fake_env):
	_, users_state = fake_env
	u = wr.User.create(name="tmpUser", password="P@ss1!")
	assert "tmpUser" in users_state["names"]
	u.password.chg(new="P@ss2!")
	u.delete()
	assert "tmpUser" not in users_state["names"]


def test_user_id_name_domain_type(fake_env):
	u = wr.User(name="Admin")
	assert u.id.startswith("S-1-")
	assert u.name == "Admin"
	# domain may be None in fake env, but function returns string from powershell mock
	assert isinstance(u.domain, str)
	# type may return Local/None; with mock powershell, it may raise and return None
	t = u.type
	assert t in ("Local", None)
