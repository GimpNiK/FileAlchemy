import os
from .ViewPort import ViewPort
import shutil as sh
from pathlib import Path
from typing import Optional, List, Any
from .encoding_utils import check_bom,detect_encoding,determine_minimal_encoding
from .file_utils import copy, mkdir, mkfile, rmfile, rmdir, make_archive, extract_archive, chmod, nano, make, remove, ls

class CMD:
	"""
	Класс CMD — основной интерфейс для работы с файлами, текстом и директориями.
	Предоставляет методы для управления файлами, директориями, кодировками, а также вспомогательные классы для работы с содержимым.
	"""
	class _Content:
		"""
		Базовый класс для представления содержимого (текста или файла).
		Позволяет использовать операторы для передачи содержимого между объектами.
		"""
		content: str
		encoding: str
		_cmd: 'CMD|None' = None

		def __str__(self) -> str:
			"""Возвращает строковое представление содержимого."""
			return self.content
		
		def __repr__(self) -> str:
			"""Возвращает строковое представление объекта с указанием кодировки."""
			return f"<{self.__class__.__name__} encoding={self.encoding}>"

		def __gt__(self, other):
			"""
			Оператор > : копирует содержимое текущего объекта в другой объект _Content.
			"""
			if not isinstance(other, CMD._Content) or isinstance(other, CMD._files):
				raise TypeError(f">: Ожидался наследник _Content и не _files, а не {type(other).__name__}")
			other.content = self.content
			return self._cmd

		def __lt__(self, other):
			"""
			Оператор < : копирует содержимое из другого объекта _Content в текущий.
			"""
			if not isinstance(other, CMD._Content) or isinstance(self, CMD._files):
				raise TypeError(f"<: Ожидался наследник _Content и не _files, а не self: {type(self).__name__}, other: {type(other).__name__}")
			self.content = other.content
			return self._cmd

		def __rshift__(self, other):
			"""
			Оператор >> : добавляет содержимое текущего объекта к другому с разделителем.
			"""
			if not isinstance(other, CMD._Content) or isinstance(other, CMD._files):
				raise TypeError(f">>: Ожидался наследник _Content и не _files, а не {type(other).__name__}")
			sep = other._cmd.sep if other._cmd is not None and other.content != "" else ""
			other.content = other.content + sep + self.content
			return self._cmd

		def __lshift__(self, other):
			"""
			Оператор << : добавляет содержимое другого объекта к текущему с разделителем.
			"""
			if not isinstance(other, CMD._Content) or isinstance(self, CMD._files):
				raise TypeError(f"<<: Ожидался наследник _Content и не _files, а не self: {type(self).__name__}, other: {type(other).__name__}")
			sep = self._cmd.parms["sep"] if self._cmd is not None and self.content != "" else ""
			self.content = self.content + sep + other.content
			return self._cmd

	class _file(_Content):
		"""
		Класс для работы с отдельным файлом.
		Позволяет читать, записывать, очищать содержимое и перекодировать файл.
		"""
		def __init__(self, path: Path | str, encoding: str = 'utf-8', _cmd: 'CMD|None' = None):
			self.path = Path(path)
			self.encoding = encoding
			self._cmd = _cmd
		
		def __str__(self) -> str:
			"""Возвращает путь к файлу в виде строки."""
			return str(self.path)
		
		def __repr__(self) -> str:
			"""Возвращает строковое представление объекта с путем и кодировкой."""
			return f"<_file path={self.path} encoding={self.encoding}>"

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

		def recode(self, to_encoding: Optional[str] = None, from_encoding: Optional[str] = None) -> "CMD|None":
			"""
			Перекодирует файл в другую кодировку.
			:param to_encoding: Целевая кодировка
			:param from_encoding: Исходная кодировка (опционально)
			:return: self._cmd для цепочек вызовов
			"""
			try:
				if to_encoding is None:
						to_encoding = determine_minimal_encoding(self.path)
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
				return self._cmd
			except Exception as e:
				raise IOError(f"Ошибка перекодировки файла '{self.path}': {e}")

	class _files(_Content):
		"""
		Класс для работы с группой файлов.
		Позволяет читать содержимое всех файлов как единую строку, очищать их.
		"""
		def __init__(self, *args: Any, encoding: str = 'utf-8', _cmd: 'CMD|None' = None):
			self._file_objects = []
			for arg in args:
				if isinstance(arg, CMD._file):
					self._file_objects.append(arg)
				elif isinstance(arg, (str, Path)):
					self._file_objects.append(CMD._file(arg, encoding, _cmd))
				else:
					raise TypeError(f"Неподдерживаемый тип: {type(arg).__name__}")
			self.encoding = encoding
			self._cmd = _cmd

		def __str__(self) -> str:
			"""Возвращает список путей файлов через запятую."""
			return ", ".join(str(f.path) for f in self._file_objects)
		
		def __repr__(self) -> str:
			"""Возвращает строковое представление объекта с путями файлов."""
			paths = [str(f.path) for f in self._file_objects]
			return f"<_files paths={paths} count={len(paths)}>"

		@property
		def content(self) -> str:
			"""Содержимое всех файлов, объединённое через разделитель sep."""
			contents = []
			for file_obj in self._file_objects:
				contents.append(file_obj.content)
			sep = self._cmd.sep if self._cmd is not None else ""
			return sep.join(contents)

		@content.setter
		def content(self, value: str):
			"""Запись содержимого в несколько файлов не поддерживается."""
			raise NotImplementedError("Запись контента в несколько файлов одновременно не поддерживается")

		@content.deleter
		def content(self) -> List[Path]:
			"""Очищает содержимое всех файлов. Возвращает список файлов с ошибками."""
			errors = []
			for file_obj in self._file_objects:
				try:
					del file_obj.content
				except Exception:
					errors.append(file_obj.path)
			return errors

	class _text(_Content):
		"""
		Класс для работы с текстом в памяти (без файловой системы).
		"""
		def __init__(self, content: str = "", encoding: str = 'utf-8', _cmd: 'CMD|None' = None):
			self.content = content
			self.encoding = encoding
			self._cmd = _cmd
		
		def __str__(self) -> str:
			"""Возвращает первые 50 символов текста (или весь текст, если он короче)."""
			return self.content[:50] + "..." if len(self.content) > 50 else self.content
		
		def __repr__(self) -> str:
			"""Возвращает строковое представление объекта с длиной текста и кодировкой."""
			return f"<_text length={len(self.content)} encoding={self.encoding}>"

	def text(self, content: str = "", encoding: Optional[str] = None) -> _text:
		"""
		Создаёт объект _text для работы с текстом в памяти.
		:param content: Исходный текст
		:param encoding: Кодировка (по умолчанию — default_encoding)
		:return: объект _text
		"""
		enc = encoding or self.parms["default_encoding"]
		return CMD._text(content, enc, self)

	def file(self, path: str | Path, encoding: Optional[str] = None) -> _file:
		"""
		Создаёт объект _file для работы с файлом.
		:param path: Путь к файлу
		:param encoding: Кодировка (определяется автоматически, если не указана)
		:return: объект _file
		"""
		try:
			enc = encoding or detect_encoding(path)
		except FileNotFoundError:
			enc = self.parms["default_encoding"]
		return CMD._file(self.to_abspath(path), enc, self)

	def files(self, *args, encoding: Optional[str] = None) -> _files:
		"""
		Создаёт объект _files для работы с группой файлов.
		:param args: Пути к файлам или объекты _file
		:param encoding: Кодировка (по умолчанию — default_encoding)
		:return: объект _files
		"""
		enc = encoding or self.default_encoding
		return CMD._files(*args, encoding=enc, _cmd=self)

		
		
	def __init__(
		self,
		sep: str = "\n",
		current_dir: str | Path = os.getcwd(),
		default_encoding: str = 'utf-8',
		parms :ViewPort = ViewPort()
	):
		"""
		Инициализация CMD.
		:param sep: Разделитель для объединения содержимого
		:param current_dir: Текущая рабочая директория
		:param default_encoding: Кодировка по умолчанию
		:param parms: Объект ViewPort для параметров окружения
		"""
		self.current_dir = Path(current_dir)
		parms.sets({
			"~": lambda: Path(os.path.expanduser('~')),
			"..": lambda: self.current_dir.parent,
			"CURRENTDIR": lambda: self.current_dir
		})
		parms["default_encoding"] = default_encoding
		parms["sep"] = sep
		self.parms = parms

	@property
	def getenv(self) -> dict:
		"""
		Возвращает объединённый словарь переменных окружения и пользовательских параметров.
		"""
		return self.parms.parms

	def to_abspath(self, path: str | Path) -> Path:
		"""
		Преобразует путь в абсолютный с учётом переменных окружения и специальных обозначений.
		:param path: Путь (строка или Path)
		:return: Абсолютный Path
		"""
		path = Path(path)
		parts = path.parts
		new_path = Path()

		for part in parts:
			if len(part) >= 3 and part.startswith('%') and part.endswith('%'):
				var_name = part[1:-1]
				if var_name in self.getenv:
					new_path = new_path / Path(self.getenv[var_name])
				else:
					new_path = new_path / part
			elif part == '~':
				new_path = new_path / Path(os.path.expanduser('~'))
			elif part == '..':
				new_path = new_path.parent if new_path.parts else self.current_dir.parent
			elif part == '.':
				new_path = new_path / self.current_dir
			elif part:
				new_path = new_path / part

		if not new_path.is_absolute():
			new_path = self.current_dir / new_path

		return new_path.resolve()

	def cd(self, path: str | Path):
		"""
		Меняет текущую рабочую директорию.
		:param path: Новый путь
		:return: self (для цепочек вызовов)
		"""
		self.current_dir = self.to_abspath(path)
		return self

	def copy(self, from_path: str | Path, to_path: str | Path, *, follow_symlinks: bool = True, ignore_errors: bool = False):
		"""
		Копирует файл или директорию.
		:param from_path: Исходный путь
		:param to_path: Куда копировать
		:param follow_symlinks: Следовать за символическими ссылками
		:param ignore_errors: Игнорировать ошибки
		:return: self
		"""
		from_path = self.to_abspath(from_path)
		to_path = self.to_abspath(to_path)
		try:
			copy(from_path, to_path, follow_symlinks=follow_symlinks)
		except Exception:
			if not ignore_errors:
				raise
		return self

	def mkdir(self, path: str | Path, mode: int = 0o777, parents: bool = False, exist_ok: bool = False, ignore_errors: bool = False):
		"""
		Создаёт директорию.
		:param path: Путь к директории
		:param mode: Права доступа
		:param parents: Создавать родительские директории
		:param exist_ok: Не выдавать ошибку, если директория уже существует
		:param ignore_errors: Игнорировать ошибки
		:return: self
		"""
		path = self.to_abspath(path)
		try:
			mkdir(path, mode=mode, parents=parents, exist_ok=exist_ok)
		except Exception:
			if not ignore_errors:
				raise
		return self

	def mkfile(self, path: str | Path, ignore_errors: bool = False):
		"""
		Создаёт пустой файл.
		:param path: Путь к файлу
		:param ignore_errors: Игнорировать ошибки
		:return: self
		"""
		path = self.to_abspath(path)
		try:
			mkfile(path)
		except Exception:
			if not ignore_errors:
				raise
		return self

	def rmfile(self, path: str | Path, ignore_errors: bool = False):
		"""
		Удаляет файл.
		:param path: Путь к файлу
		:param ignore_errors: Игнорировать ошибки
		:return: self
		"""
		path = self.to_abspath(path)
		try:
			rmfile(path)
		except Exception:
			if not ignore_errors:
				raise
		return self

	def rmdir(self, path: str | Path, ignore_errors: bool = False, onerror=None):
		"""
		Рекурсивно удаляет директорию.
		:param path: Путь к директории
		:param ignore_errors: Игнорировать ошибки
		:param onerror: Обработчик ошибок
		:return: self
		"""
		path = self.to_abspath(path)
		rmdir(path, ignore_errors=ignore_errors, onerror=onerror)
		return self

	def make_archive(self, from_path: str | Path, to_path: str | Path | None = None, format: str = "zip", owner: Optional[str] = None, group: Optional[str] = None, ignore_errors: bool = False):
		"""
		Создаёт архив из файла или директории.
		:param from_path: Что архивировать
		:param to_path: Куда сохранить архив (по умолчанию — рядом с исходником)
		:param format: Формат архива (zip, tar и др.)
		:param owner: Владелец (опционально)
		:param group: Группа (опционально)
		:param ignore_errors: Игнорировать ошибки
		:return: self
		"""
		from_path = self.to_abspath(from_path)
		if to_path is None:
			archive_name = f"{from_path.name}.{format}"
			to_path = self.current_dir / archive_name
		else:
			to_path = self.to_abspath(to_path)
		try:
			make_archive(from_path, to_path, format=format, owner=owner, group=group)
		except Exception:
			if not ignore_errors:
				raise
		return self
		
	def extract_archive(self, archive_path: str | Path, extract_dir: Optional[str | Path] = None, format: Optional[str] = None, ignore_errors: bool = False):
		"""
		Распаковывает архив в директорию.
		:param archive_path: Путь к архиву
		:param extract_dir: Куда распаковать (по умолчанию — текущая директория)
		:param format: Формат архива (опционально)
		:param ignore_errors: Игнорировать ошибки
		:return: self
		"""
		archive_path = self.to_abspath(archive_path)
		if extract_dir is None:
			extract_dir = self.current_dir
		else:
			extract_dir = self.to_abspath(extract_dir)
		try:
			extract_archive(archive_path, extract_dir, format=format)
		except Exception:
			if not ignore_errors:
				raise
		return self
		
	def chmod(self, path: str | Path, mode: int, ignore_errors: bool = False):
		"""
		Меняет права доступа к файлу или директории.
		:param path: Путь
		:param mode: Новый режим (например, 0o755)
		:param ignore_errors: Игнорировать ошибки
		:return: self
		"""
		path = self.to_abspath(path)
		try:
			chmod(path, mode=mode)
		except Exception:
			if not ignore_errors:
				raise
		return self
		
	def recode(self, file_path: str | Path, to_encoding: str, from_encoding: Optional[str] = None, ignore_errors: bool = False):
		"""
		Перекодирует файл в другую кодировку (см. CMD._file.recode).
		:param file_path: Путь к файлу
		:param to_encoding: Целевая кодировка
		:param from_encoding: Исходная кодировка (опционально)
		:param ignore_errors: Игнорировать ошибки
		:return: self
		"""
		try:
			file_obj = self.file(file_path)
			file_obj.recode(to_encoding, from_encoding)
		except Exception as e:
			if not ignore_errors:
				raise
		return self
		
	def nano(self, path: str | Path, edit_txt="notepad", ignore_errors: bool = False):
		"""
		Открывает файл в текстовом редакторе.
		:param path: Путь к файлу
		:param edit_txt: Имя редактора (по умолчанию notepad)
		:param ignore_errors: Игнорировать ошибки
		:return: self
		"""
		path = self.to_abspath(path)
		try:
			nano(path, edit_txt=edit_txt)
		except Exception:
			if not ignore_errors:
				raise
		return self

	def remove(self, path: str | Path, ignore_errors: bool = False):
		"""
		Удаляет файл или директорию рекурсивно.
		:param path: Путь
		:param ignore_errors: Игнорировать ошибки
		:return: self
		"""
		path = self.to_abspath(path)
		try:
			remove(path)
		except Exception:
			if not ignore_errors:
				raise
		return self

	def make(self, path: str | Path, is_file: bool = None, ignore_errors: bool = False):
		"""
		Создаёт все папки в пути и, если нужно, файл.
		:param path: Путь
		:param is_file: Является ли путь файлом
		:param ignore_errors: Игнорировать ошибки
		:return: self
		"""
		path = self.to_abspath(path)
		try:
			make(path, is_file=is_file)
		except Exception:
			if not ignore_errors:
				raise
		return self

	def ls(self, path: str | Path = ".", details: bool = False, ignore_errors: bool = False):
		"""
		Список файлов и директорий в указанном пути.
		:param path: Путь
		:param details: Возвращать подробную информацию
		:param ignore_errors: Игнорировать ошибки
		:return: список файлов или словарь с деталями
		"""
		path = self.to_abspath(path)
		try:
			return ls(path, details=details)
		except Exception:
			if not ignore_errors:
				raise
			return {} if details else []


	#Псевдонимы 
	touch = mkfile
	rm = remove
	rmtree = rmdir
	mk_archive = make_archive
	mkarch = make_archive
	unpack_archive = extract_archive
	unparch = extract_archive
	unp_arch =extract_archive
	ext_arch =extract_archive
	extarch = extract_archive
	convert_encoding = recode

	def __str__(self):
		"""Возвращает текущую рабочую директорию как строку."""
		return str(self.current_dir)

	def __repr__(self):
		"""Возвращает строковое представление объекта CMD с текущей директорией."""
		return f"<CMD current_dir={self.current_dir}>"