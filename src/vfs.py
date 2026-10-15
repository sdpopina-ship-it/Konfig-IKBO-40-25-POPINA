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
    mode: int = 0o644


@dataclass
class VfsDirectory:
    """Каталог с дочерними объектами виртуальной файловой системы."""

    children: dict[str, VfsNode] = field(default_factory=dict)
    mode: int = 0o755


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
        target_path.mkdir(parents=True, mode=self.root.mode)
        target_path.chmod(self.root.mode)
        write_directory(self.root, target_path)

    def resolve(
        self,
        path: str,
        current_path: tuple[str, ...] = (),
    ) -> tuple[VfsNode, tuple[str, ...]]:
        """Найти объект VFS по абсолютному или относительному пути."""

        parts = normalize_virtual_path(path, current_path)
        node: VfsNode = self.root
        for part in parts:
            if not isinstance(node, VfsDirectory):
                raise VfsError(f"Это не каталог: {part}")
            try:
                node = node.children[part]
            except KeyError as error:
                raise VfsError(f"Путь не найден: {path}") from error
        return node, parts

    def read_text(
        self,
        path: str,
        current_path: tuple[str, ...] = (),
    ) -> str:
        """Прочитать UTF-8 текстовый файл из снимка VFS."""

        node, _ = self.resolve(path, current_path)
        if isinstance(node, VfsDirectory):
            raise VfsError(f"Это каталог: {path}")
        try:
            return node.content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise VfsError(f"Файл не является UTF-8 текстом: {path}") from error


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
            destination.mkdir(mode=node.mode)
            destination.chmod(node.mode)
            write_directory(node, destination)
        else:
            destination.write_bytes(node.content)
            destination.chmod(node.mode)


def normalize_virtual_path(
    path: str,
    current_path: tuple[str, ...],
) -> tuple[str, ...]:
    """Нормализовать путь, не позволяя подняться выше корня VFS."""

    is_rooted = path.startswith("/") or path == "~" or path.startswith("~/")
    parts = [] if is_rooted else list(current_path)
    tail = trim_virtual_path_prefix(path)
    for part in tail.split("/"):
        if part in {"", "."}:
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return tuple(parts)


def trim_virtual_path_prefix(path: str) -> str:
    """Убрать только допустимый признак корня из пути VFS."""

    if path.startswith("/"):
        return path[1:]
    if path == "~":
        return ""
    return path[2:] if path.startswith("~/") else path
