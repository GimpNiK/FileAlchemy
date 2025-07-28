# FileAlchemy

**FileAlchemy v. 1.1.1** is a powerful and intuitive Python library for working with files, directories, and text data. It provides a user-friendly interface for performing file system operations, text processing, and encoding management, inspired by the Unix and Cmd command line syntax. Most of the command names duplicate the functionality of these two command shells. It is supposed to be used instead of bat and sh files, and used interactively in the Python Shell.

**Keywords**: Python file management, cross-platform file handling, text encoding detection, Unix-like file commands in Python 

## Main features

1. **File and directory management**:
   - Create, copy, delete, write text
   - Work with zip,tar,gztar,bztar,xztar archives (works using the shutil module).
   - Access Rights Management (chmod)

2. **Working with text**:
- Reading and writing files with automatic encoding detection
   - Transcoding between different encodings
- Operations with text in memory

3. **User-friendly interface**:
- Method call chains
   - Overloading operators >,>>,<,<< to work with file contents 
   - Support for special paths (~, .., environment variables)

4. **Cross-platform**:
   - Works on Windows, Linux and macOS
   - A single API for different operating systems

## Installation

```bash
pip install git+https://github.com/GimpNiK/FileAlchemy.git
```

Requirements:
- Python 3.8+
- Dependencies: `chardet' (for automatic detection of encodings)

## Quick start

```python
from FileAlchemy import CMD

# Initialize
cmd = CMD()

# Changing the working directory
cmd.cd ("..")

# Create a file and write the text
cmd.file("test.txt ").content = "Hello world!"

# Reading
the content = cmd file.file("test.txt").content
print(content) # "Hello world!"

#Saving the contents of multiple files into one
cmd.files("1.txt","2.txt") >> cmd.file("3.txt")

#Clearing the contents
of the del file("3.txt ").content

# Copy
the cmd.copy file("test.txt ", "backup.txt ")

# Working with
cmd archives.make_archive("backup.txt ", "archive.zip ")
``

## Detailed API description

### Initialization

```python
cmd = CMD(
    sep="\n", # Default delimiter for text
operations current_dir=".", # Initial working directory(by default, project location)
default_encoding="utf-8" # Default encoding
)
``

### Basic methods

#### Working with files

- `file(path)' - creates an object for working with the file
- `files(*paths)` - creates an object for working with a group of files
- `text(content="")` - creates an object for working with text


#### File operations(CMD methods)
- `mkfile(path) / touch(path)` - create an empty file
- `rmfile(path)` - deleting a file
- `nano(path)' - opening a file in a text editor
- `recode(path, to_encoding = min_encoding, from_encoding = realy_encoding)` - transcoding the file (if optional parameters are not specified, the file is overwritten to the lowest possible encoding)

#### Folder operations (CMD methods)
- `mkdir(path)` - creating a directory
- `rmdir(path)` - deleting a directory

#### Folder/file operations (CMD methods)
- `copy(from_path, to_path)' - copying a file/directory
- `make(path)' - creating a complete path
- `rm(path)` - delete folder/file
- `mkarch(from_path, to_path) / make_archive` - archive creation of a folder/file
- `unpack_archive(archive_path, extract_dir) / unparch` - unpacking the archive of a folder/file
- `chmod(path, mode)` - change the access rights of a folder/file

#### Working with paths
- `to_abspath(path)' - conversion to an absolute path
- `cd(path)' - change the current directory
- `ls(details = False)` - displays a list of files in the directory

#### Working with environment variables(CMD().parms)
- `set_gl`- sets the value of the global permanent(str)
- `del_gl` - deletes the value of the global permanent
- `set ` - sets the value of a local variable
- `sets' - sets the values of local variables(dict)
- `del ` - deletes the value of a local variable
- `dels' - deletes values of local variables (list)

All environment variables are substituted in the path:
``python
#Creating an instance of the cmd command line
= CMD()
#Creating
an environment variable my_var = cmd.parms["~"]
cmd.parms["my_var"] = my_var #local by value
cmd.parms["my var"] = lambda: my_var # local by reference
cmd.parms.set_gl("my_var") = my_var # global by value
cmd.ls (path = "%my_var%") #displays a list of files in the home directory
``
### Operator overload

The library provides convenient operators for working with content.:

```python
# Overwriting the content
cmd.file("a.txt") > cmd.file("b.txt")  # a.txt → b.txt
cmd.file("b.txt") < cmd.file("a.txt")  # b.txt ← a.txt

# Adding the contents
of cmd.file("1and2.txt ") << cmd.files("1.txt ","2.txt ")
cmd.file("log.txt ") << cmd.text("new entry")  # adding to the end
```

### Encoding management

The library automatically detects file encodings and provides methods for working with them.:

```python
# Automatic encoding detection
file_obj = cmd.file("unknown.txt ")
print(file_obj.encoding) # for example, "utf-8" or "cp1251"

# Transcoding the file
file_obj.recode("utf-8")

# Determining the minimum suitable encoding
min_encoding = cmd.determine_minimal_encoding("Text")
``

## Usage examples


### 1. Creating backups

```python
# Create an archive with the current
import datetime date
today = datetime.datetime.now().strftime("%Y-%m-%d")
cmd.make_archive("project", f"backups/project_{today}.zip")
```

###2. Logging

```python
# Adding an entry to
the log_entry = f"{datetime.datetime.now()}: New event\n"
cmd.file("app.log") << cmd.text(log_entry)
``

###3. Working with configuration files

```python
# Reading the config
config = cmd.file("config.json").content
import json
settings = json.loads(config)

# Change and save
settings["timeout"] = 30
cmd.file("config.json").content = json.dumps(settings, indent=2)
```

## Implementation features

1. **Lazy operations** - files are read only when necessary
2. **Auto-repair** - automatic detection of encoding in case of reading errors
3. **Security** - checking the existence of files before operations
4. **Cross-platform** - a single API for different operating systems

**Under development:** 
1. Acceleration of reading and writing by removing waiting for the end of writing, multiple reading (threading).
2. Optimization of the controls for file search.
3. Improved archive management.

## License

MIT License. See the LICENSE file for details.



## Author

GimpNiK (https://github.com/GimpNiK ) is the developer and maintainer of the project.

# Full documentation

## Description

The 'CMD` class is the main interface for working with files, text, and directories. Provides methods for managing files, directories, encodings, and auxiliary classes for working with content.

---

## CMD class methods

### text(content: str = "", encoding: Optional[str] = None) -> _text
Creates a _text object for working with text in memory.
- **content** (`str`): source text
- **encoding** (`str | None`): encoding (default is default_encoding)
- **return**: the _text object

### file(path: str | Path, encoding: Optional[str] = None) -> _file
Creates a _file object to work with the file.
- **path** (`str | Path`): the path to the file
- **encoding** (`str | None`): encoding (detected automatically if not specified)
- **return**: _file object

### files(*args, encoding: Optional[str] = None) -> _files
Creates a _files object for working with a group of files.
- **args** (`str | Path | _file'): file paths or _file objects
- **encoding** (`str | None`): encoding (default is default_encoding)
- **return**: the _files object

### cd(path: str | Path) -> CMD
Changes the current working directory.
- **path** (`str | Path`): A new path
- **return**: self (for call chains)

### copy(from_path: str | Path, to_path: str | Path, *, follow_symlinks: bool = True, ignore_errors: bool = False) -> CMD
Copies a file or directory.
- **from_path** (`str | Path`): source path
- **to_path** (`str | Path`): where to copy
- **follow_symlinks** (`bool`): follow symbolic links
- **ignore_errors** (`bool`): ignore errors
- **return**: self

### mkdir(path: str | Path, mode: int = 0o777, parents: bool = False, exist_ok: bool = False, ignore_errors: bool = False) -> CMD
Creates a directory.
- **path** (`str | Path`): path to the directory
- **mode** (`int`): access rights
- **parents** (`bool`): create parent directories
- **exist_ok** (`bool`): do not issue an error if the directory already exists.
- **ignore_errors** (`bool`): ignore errors
- **return**: self

### mkfile(path: str | Path, ignore_errors: bool = False) -> CMD
Creates an empty file.
- **path** (`str | Path`): the path to the file
- **ignore_errors** (`bool`): ignore errors
- **return**: self

### rmfile(path: str | Path, ignore_errors: bool = False) -> CMD
Deletes the file.
- **path** (`str | Path`): the path to the file
- **ignore_errors** (`bool`): ignore errors
- **return**: self

### rmdir(path: str | Path, ignore_errors: bool = False, onerror=None) -> CMD
Deletes the directory recursively.
- **path** (`str | Path`): path to the directory
- **ignore_errors** (`bool`): ignore errors
- **onerror** (`callable | None'): error handler
- **return**: self

### make_archive(from_path: str | Path, to_path: str | Path | None = None, format: str = "zip", owner: Optional[str] = None, group: Optional[str] = None, ignore_errors: bool = False) -> CMD
Creates an archive from a file or directory.
- **from_path** (`str | Path`): what to archive
- **to_path** (`str | Path | None'): where to save the archive (by default, next to the source)
- **format** (`str`): archive format (zip, tar, etc.)
- **owner** (`str | None'): owner (optional)
- **group** (`str | None`): group (optional)
- **ignore_errors** (`bool`): ignore errors
- **return**: self

### extract_archive(archive_path: str | Path, extract_dir: Optional[str | Path] = None, format: Optional[str] = None, ignore_errors: bool = False) -> CMD
Unpacks the archive into a directory.
- **archive_path** (`str | Path`): the path to the archive
- **extract_dir** (`str | Path | None'): where to unpack (default is the current directory)
- **format** (`str | None'): archive format (optional)
- **ignore_errors** (`bool`): ignore errors
- **return**: self

### chmod(path: str | Path, mode: int, ignore_errors: bool = False) -> CMD
Changes access rights to a file or directory.
- **path** (`str | Path`): path
- **mode** (`int'): new mode (e.g. 0o755)
- **ignore_errors** (`bool`): ignore errors
- **return**: self

### recode(file_path: str | Path, to_encoding: str, from_encoding: Optional[str] = None, ignore_errors: bool = False) -> CMD
Recodes the file to a different encoding.
- **file_path** (`str | Path`): the path to the file
- **to_encoding** (`str`): target encoding
- **from_encoding** (`str | None`): source encoding (optional)
- **ignore_errors** (`bool`): ignore errors
- **return**: self

### nano(path: str | Path, edit_txt="notepad", ignore_errors: bool = False) -> CMD
Opens the file in a text editor.
- **path** (`str | Path`): the path to the file
- **edit_txt** (`str'): editor name (default is notepad)
- **ignore_errors** (`bool`): ignore errors
- **return**: self

### remove(path: str | Path, ignore_errors: bool = False) -> CMD
Deletes a file or directory recursively.
- **path** (`str | Path`): path
- **ignore_errors** (`bool`): ignore errors
- **return**: self

### make(path: str | Path, is_file: bool = None, ignore_errors: bool = False) -> CMD
Creates all folders in the path and, if necessary, a file.
- **path** (`str | Path`): path
- **is_file** (`bool | None`): is the path a file
- **ignore_errors** (`bool`): ignore errors
- **return**: self

### ls(path: str | Path = ".", details: bool = False, ignore_errors: bool = False)
A list of files and directories in the specified path.
- **path** (`str | Path`): path
- **details** (`bool`): return detailed information
- **ignore_errors** (`bool`): ignore errors
- **return**: a list of files or a dictionary with details

---

## Stream operations (>>, >, <<, <) with files and text

The CMD class supports convenient operators for transferring and combining content between files and text objects.:

- `a > b` — copies the contents of object `a` to object `b` (overwrites the contents of `b`).
- `a >> b` — adds the contents of object `a` to the end of object `b` (taking into account the separator `sep`).
- `a < b` — copies the contents of object `b` to object `a` (overwrites the contents of `a').
- `a << b` — adds the contents of object `b` to the end of object `a` (taking into account the separator `sep`).
