from setuptools import setup, find_packages



setup(
    name="FileAlchemy",
    version="1.1.1",
    author="GimpNiK",
    author_email="reshfizika@mail.ru",
    description="Powerful Python library for file system operations and text processing",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/GimpNiK/FileAlchemy",
    packages=find_packages(),

    keywords="python file system text-processing encoding chardet unix-commands",
    
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
         "Topic :: Utilities",
        "Topic :: System :: Filesystems",
    ],
    python_requires=">=3.8",
    install_requires=[
        "chardet",
    ],
)
