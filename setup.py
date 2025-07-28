from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="FileAlchemy",
    version="1.1.1",
    author="GimpNiK",
    author_email="reshfizika@mail.ru",
    description="Powerful Python library for file system operations and text processing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/GimpNiK/FileAlchemy",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "chardet",
    ],
)