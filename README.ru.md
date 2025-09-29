# FileAlchemy

**FileAlchemy v. 1.1.1** — это мощная и интуитивно понятная Python-библиотека для работы с файлами, директориями и текстовыми данными. Она предоставляет удобный интерфейс для выполнения операций с файловой системой, обработки текста и управления кодировками, вдохновленный синтаксисом командной строки Unix и Cmd. Большинство названий команд дублирует функционал из этих двух командных оболочек. Предполагается использовать вместо bat и sh файлов, в интерактивном режиме использовать в Python Shell.

## Основные возможности

1. **Управление файлами и директориями**:
   - Создание, копирование, удаление, запись текста
   - Работа с архивами zip,tar,gztar,bztar,xztar (работает, используя модуль shutil).
   - Управление правами доступа (chmod)

2. **Работа с текстом**:
   - Чтение и запись файлов с автоматическим определением кодировки
   - Перекодировка между различными кодировками
   - Операции с текстом в памяти

3. **Удобный интерфейс**:
   - Цепочки вызовов методов
   - Перегрузка операторов >,>>,<,<< для работы с содержимым файлов 
   - Поддержка специальных путей (~, .., переменные окружения)

4. **Кроссплатформенность**:
   - Работает на Windows, Linux и macOS
   - Единый API для разных ОС

## Установка

```bash
pip install FileAlchemy
```

Требования:
- Python 3.8+
- Зависимости: `chardet` (для автоматического определения кодировок)

## Быстрый старт

```python
from FileAlchemy import CMD

# Инициализация
cmd = CMD()

# Изменение рабочей директории
cmd.cd("..")

# Создание файла и запись текста
cmd.file("test.txt").content = "Привет, мир!"

# Чтение файла
content = cmd.file("test.txt").content
print(content)  # "Привет, мир!"

#Сохранение содержимого нескольких файлов в один
cmd.files("1.txt","2.txt") >> cmd.file("3.txt")

#Очистка содержимого файла
del file("3.txt").content

# Копирование файла
cmd.copy("test.txt", "backup.txt")

# Работа с архивами
cmd.make_archive("backup.txt", "archive.zip")
```

## Подробное описание API

### Инициализация

```python
cmd = CMD(
    sep="\n",               # Разделитель по умолчанию для операций с текстом
    current_dir=".",        # Начальная рабочая директория(по умолчанию, места нахождения проекта)
    default_encoding="utf-8" # Кодировка по умолчанию
)
```

### Основные методы

#### Работа с файлами

- `file(path)` - создает объект для работы с файлом
- `files(*paths)` - создает объект для работы с группой файлов
- `text(content="")` - создает объект для работы с текстом


#### Операции с файлами(методы CMD)
- `mkfile(path) / touch(path)` - создание пустого файла
- `rmfile(path)` - удаление файла
- `nano(path)` - открытие файла в текстовом редакторе
- `recode(path, to_encoding = min_encoding, from_encoding = realy_encoding)` - перекодирование файла(если не указаны необязательные параметры файл перезаписывается в минимально возможную кодировку)

#### Операции с папками (методы CMD)
- `mkdir(path)` - создание директории
- `rmdir(path)` - удаление директории

#### Операции с папками/файлами (методы CMD)
- `copy(from_path, to_path)` - копирование файла/директории
- `make(path)` - создание полного пути
- `rm(path)` - удаление папки/файла
- `mkarch(from_path, to_path) / make_archive` - создание архива папки/файла
- `unpack_archive(archive_path, extract_dir) / unparch` - распаковка архива папки/файла
- `chmod(path, mode)` - изменение прав доступа папки/файла

#### Работа с путями
- `to_abspath(path)` - преобразование в абсолютный путь
- `cd(path)` - изменение текущей директории
- `ls(details = False)` - выводит список файлов в директории

#### Работа с переменными окружения(CMD().parms)
- `set_gl `- устанвливает значение глобальной перменной(str)
- `del_gl `  - удаляет значение глобальной перменной
- `set   `   - устанавливает значение локальной переменной
- `sets `    - устанавливает значения локальных переменных(dict)
- `del  `    - удаляет значение локальной переменной
- `dels `    - удаляет значения локальных переменных (list)

Все переменные окружения подставляются в пути:
```python
#Создаем экземпляр командной строки
cmd = CMD()
#Создаем переменную окружения
my_var = cmd.parms["~"]
cmd.parms["my_var"] = my_var #локальную по значению
cmd.parms["my var"] = lambda: my_var # локальную по ссылке
cmd.parms.set_gl("my_var") = my_var # глобальную по значению
cmd.ls(path = "%my_var%") #выведет список файлов в домашней директории
```
### Перегрузка операторов

Библиотека предоставляет удобные операторы для работы с содержимым:

```python
# Перезапись содержимого
cmd.file("a.txt") > cmd.file("b.txt")  # a.txt → b.txt
cmd.file("b.txt") < cmd.file("a.txt")  # b.txt ← a.txt

# Добавление содержимого
cmd.file("1and2.txt") << cmd.files("1.txt","2.txt")
cmd.file("log.txt") << cmd.text("новая запись")  # добавление в конец
```

### Управление кодировками

Библиотека автоматически определяет кодировки файлов и предоставляет методы для работы с ними:

```python
# Автоматическое определение кодировки
file_obj = cmd.file("unknown.txt")
print(file_obj.encoding)  # например, "utf-8" или "cp1251"

# Перекодировка файла
file_obj.recode("utf-8")

# Определение минимальной подходящей кодировки
min_encoding = cmd.determine_minimal_encoding("Текст")
```

## Примеры использования


### 1. Создание резервных копий

```python
# Создание архива с текущей датой
import datetime
today = datetime.datetime.now().strftime("%Y-%m-%d")
cmd.make_archive("project", f"backups/project_{today}.zip")
```

### 2. Логирование

```python
# Добавление записи в лог-файл
log_entry = f"{datetime.datetime.now()}: Новое событие\n"
cmd.file("app.log") << cmd.text(log_entry)
```

### 3. Работа с конфигурационными файлами

```python
# Чтение конфига
config = cmd.file("config.json").content
import json
settings = json.loads(config)

# Изменение и сохранение
settings["timeout"] = 30
cmd.file("config.json").content = json.dumps(settings, indent=2)
```

## Особенности реализации

1. **Ленивые операции** - файлы читаются только при необходимости
2. **Автовосстановление** - автоматическое определение кодировки при ошибках чтения
3. **Безопасность** - проверка существования файлов перед операциями
4. **Кроссплатформенность** - единое API для разных операционных систем

**В процессе разработки:** 
1. Ускорение чтения и записи за счет снятия ожидания конца записи, множественное чтение(threading).
2. Оптимизация регулярок для поиска файлов.
3. Улучшение работы с архивами.

## Лицензия

MIT License. Смотрите файл LICENSE для подробностей.



## Автор

GimpNiK (https://github.com/GimpNiK) - разработчик и maintainer проекта.

# Полная документация

## Описание

Класс `CMD` — основной интерфейс для работы с файлами, текстом и директориями. Предоставляет методы для управления файлами, директориями, кодировками, а также вспомогательные классы для работы с содержимым.

---

## Методы класса CMD

### text(content: str = "", encoding: Optional[str] = None) -> _text
Создаёт объект _text для работы с текстом в памяти.
- **content** (`str`): исходный текст
- **encoding** (`str | None`): кодировка (по умолчанию — default_encoding)
- **return**: объект _text

### file(path: str | Path, encoding: Optional[str] = None) -> _file
Создаёт объект _file для работы с файлом.
- **path** (`str | Path`): путь к файлу
- **encoding** (`str | None`): кодировка (определяется автоматически, если не указана)
- **return**: объект _file

### files(*args, encoding: Optional[str] = None) -> _files
Создаёт объект _files для работы с группой файлов.
- **args** (`str | Path | _file`): пути к файлам или объекты _file
- **encoding** (`str | None`): кодировка (по умолчанию — default_encoding)
- **return**: объект _files

### cd(path: str | Path) -> CMD
Меняет текущую рабочую директорию.
- **path** (`str | Path`): новый путь
- **return**: self (для цепочек вызовов)

### copy(from_path: str | Path, to_path: str | Path, *, follow_symlinks: bool = True, ignore_errors: bool = False) -> CMD
Копирует файл или директорию.
- **from_path** (`str | Path`): исходный путь
- **to_path** (`str | Path`): куда копировать
- **follow_symlinks** (`bool`): следовать за символическими ссылками
- **ignore_errors** (`bool`): игнорировать ошибки
- **return**: self

### mkdir(path: str | Path, mode: int = 0o777, parents: bool = False, exist_ok: bool = False, ignore_errors: bool = False) -> CMD
Создаёт директорию.
- **path** (`str | Path`): путь к директории
- **mode** (`int`): права доступа
- **parents** (`bool`): создавать родительские директории
- **exist_ok** (`bool`): не выдавать ошибку, если директория уже существует
- **ignore_errors** (`bool`): игнорировать ошибки
- **return**: self

### mkfile(path: str | Path, ignore_errors: bool = False) -> CMD
Создаёт пустой файл.
- **path** (`str | Path`): путь к файлу
- **ignore_errors** (`bool`): игнорировать ошибки
- **return**: self

### rmfile(path: str | Path, ignore_errors: bool = False) -> CMD
Удаляет файл.
- **path** (`str | Path`): путь к файлу
- **ignore_errors** (`bool`): игнорировать ошибки
- **return**: self

### rmdir(path: str | Path, ignore_errors: bool = False, onerror=None) -> CMD
Рекурсивно удаляет директорию.
- **path** (`str | Path`): путь к директории
- **ignore_errors** (`bool`): игнорировать ошибки
- **onerror** (`callable | None`): обработчик ошибок
- **return**: self

### make_archive(from_path: str | Path, to_path: str | Path | None = None, format: str = "zip", owner: Optional[str] = None, group: Optional[str] = None, ignore_errors: bool = False) -> CMD
Создаёт архив из файла или директории.
- **from_path** (`str | Path`): что архивировать
- **to_path** (`str | Path | None`): куда сохранить архив (по умолчанию — рядом с исходником)
- **format** (`str`): формат архива (zip, tar и др.)
- **owner** (`str | None`): владелец (опционально)
- **group** (`str | None`): группа (опционально)
- **ignore_errors** (`bool`): игнорировать ошибки
- **return**: self

### extract_archive(archive_path: str | Path, extract_dir: Optional[str | Path] = None, format: Optional[str] = None, ignore_errors: bool = False) -> CMD
Распаковывает архив в директорию.
- **archive_path** (`str | Path`): путь к архиву
- **extract_dir** (`str | Path | None`): куда распаковать (по умолчанию — текущая директория)
- **format** (`str | None`): формат архива (опционально)
- **ignore_errors** (`bool`): игнорировать ошибки
- **return**: self

### chmod(path: str | Path, mode: int, ignore_errors: bool = False) -> CMD
Меняет права доступа к файлу или директории.
- **path** (`str | Path`): путь
- **mode** (`int`): новый режим (например, 0o755)
- **ignore_errors** (`bool`): игнорировать ошибки
- **return**: self

### recode(file_path: str | Path, to_encoding: str, from_encoding: Optional[str] = None, ignore_errors: bool = False) -> CMD
Перекодирует файл в другую кодировку.
- **file_path** (`str | Path`): путь к файлу
- **to_encoding** (`str`): целевая кодировка
- **from_encoding** (`str | None`): исходная кодировка (опционально)
- **ignore_errors** (`bool`): игнорировать ошибки
- **return**: self

### nano(path: str | Path, edit_txt="notepad", ignore_errors: bool = False) -> CMD
Открывает файл в текстовом редакторе.
- **path** (`str | Path`): путь к файлу
- **edit_txt** (`str`): имя редактора (по умолчанию notepad)
- **ignore_errors** (`bool`): игнорировать ошибки
- **return**: self

### remove(path: str | Path, ignore_errors: bool = False) -> CMD
Удаляет файл или директорию рекурсивно.
- **path** (`str | Path`): путь
- **ignore_errors** (`bool`): игнорировать ошибки
- **return**: self

### make(path: str | Path, is_file: bool = None, ignore_errors: bool = False) -> CMD
Создаёт все папки в пути и, если нужно, файл.
- **path** (`str | Path`): путь
- **is_file** (`bool | None`): является ли путь файлом
- **ignore_errors** (`bool`): игнорировать ошибки
- **return**: self

### ls(path: str | Path = ".", details: bool = False, ignore_errors: bool = False)
Список файлов и директорий в указанном пути.
- **path** (`str | Path`): путь
- **details** (`bool`): возвращать подробную информацию
- **ignore_errors** (`bool`): игнорировать ошибки
- **return**: список файлов или словарь с деталями

---

## Операции потоков (>>, >, <<, <) с файлами и текстом

Класс CMD поддерживает удобные операторы для передачи и объединения содержимого между файлами и текстовыми объектами:

- `a > b` — копирует содержимое объекта `a` в объект `b` (перезаписывает содержимое `b`).
- `a >> b` — добавляет содержимое объекта `a` в конец объекта `b` (с учётом разделителя `sep`).
- `a < b` — копирует содержимое объекта `b` в объект `a` (перезаписывает содержимое `a`).
- `a << b` — добавляет содержимое объекта `b` в конец объекта `a` (с учётом разделителя `sep`).

