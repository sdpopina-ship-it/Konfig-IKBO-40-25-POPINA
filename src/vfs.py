"""Виртуальная файловая система, хранящая снимок каталога в памяти."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeAlias


class VfsError(Exception):
    """Ошибка чтения или сохранения виртуальной файловой системы."""


@dataclass
class VfsFile:
    """Файл, данные которого уже находятся в памяти."""

    content: bytes


@dataclass
class VfsDirectory:
    """Каталог с дочерними объектами виртуальной файловой системы."""

    children: dict[str, VfsNode] = field(default_factory=dict)


VfsNode: TypeAlias = VfsFile | VfsDirectory


@dataclass
class VirtualFileSystem:
    """Снимок структуры каталога, не связанный с файлами после загрузки."""

    name: str
    root: VfsDirectory

    @classmethod
    def from_directory(cls, source_path: Path) -> VirtualFileSystem:
        """Загрузить дерево исходного каталога в оперативную память."""

        validate_source_directory(source_path)
        return cls(name=source_path.name, root=read_directory(source_path))

    def save_to_directory(self, target_path: Path) -> None:
        """Сохранить снимок VFS в новый каталог на физическом диске."""

        if target_path.exists() or target_path.is_symlink():
            raise VfsError(f"Путь сохранения уже существует: {target_path}")
        target_path.mkdir(parents=True)
        write_directory(self.root, target_path)


def validate_source_directory(source_path: Path) -> None:
    """Проверить, что исходный путь — доступный обычный каталог."""

    if source_path.is_symlink():
        message = "Исходный путь VFS не должен быть символической ссылкой."
        raise VfsError(message)
    if not source_path.exists():
        raise VfsError(f"Исходный путь VFS не найден: {source_path}")
    if not source_path.is_dir():
        message = f"Исходный путь VFS не является каталогом: {source_path}"
        raise VfsError(message)


def read_directory(path: Path) -> VfsDirectory:
    """Рекурсивно прочитать обычный каталог без изменения его содержимого."""

    directory = VfsDirectory()
    for entry in sorted(path.iterdir(), key=lambda item: item.name):
        if entry.is_symlink():
            raise VfsError(f"Символические ссылки не поддерживаются: {entry}")
        if entry.is_dir():
            directory.children[entry.name] = read_directory(entry)
        elif entry.is_file():
            directory.children[entry.name] = VfsFile(entry.read_bytes())
        else:
            raise VfsError(f"Неподдерживаемый объект VFS: {entry}")
    return directory


def write_directory(directory: VfsDirectory, path: Path) -> None:
    """Рекурсивно записать сохранённое в памяти дерево в целевой каталог."""

    for name, node in directory.children.items():
        destination = path / name
        if isinstance(node, VfsDirectory):
            destination.mkdir()
            write_directory(node, destination)
        else:
            destination.write_bytes(node.content)
