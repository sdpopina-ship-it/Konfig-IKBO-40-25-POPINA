"""Проверки хранения VFS в памяти и сохранения её снимка."""

import tempfile
import unittest
from pathlib import Path

from src.shell import execute_command
from src.vfs import VfsError, VirtualFileSystem


class VirtualFileSystemTests(unittest.TestCase):
    """Проверки чтения и безопасного сохранения снимка VFS."""

    def test_saves_loaded_snapshot_without_changing_source(self) -> None:
        """Сохранение использует прежние данные из памяти, а не диск."""

        with tempfile.TemporaryDirectory() as directory:
            source = create_source_tree(Path(directory))
            vfs = VirtualFileSystem.from_directory(source)
            source_file = source / "level-one" / "original.txt"
            source_file.write_text("изменено после загрузки", encoding="utf-8")
            target = Path(directory) / "saved"
            vfs.save_to_directory(target)
            saved_file = target / "level-one" / "original.txt"
            nested_file = target / "level-one" / "level-two" / "data.bin"
            self.assertEqual(saved_file.read_text(encoding="utf-8"), "оригинал")
            self.assertEqual(nested_file.read_bytes(), b"\\x00\\x01\\x02")
            self.assertEqual(
                source_file.read_text(encoding="utf-8"),
                "изменено после загрузки",
            )

    def test_refuses_to_overwrite_existing_target(self) -> None:
        """Существующий каталог нельзя случайно перезаписать командой VFS."""

        with tempfile.TemporaryDirectory() as directory:
            source = create_source_tree(Path(directory))
            target = Path(directory) / "target"
            target.mkdir()
            vfs = VirtualFileSystem.from_directory(source)
            with self.assertRaises(VfsError):
                vfs.save_to_directory(target)

    def test_command_saves_loaded_virtual_file_system(self) -> None:
        """Команда vfs-save создаёт физическую копию снимка VFS."""

        with tempfile.TemporaryDirectory() as directory:
            source = create_source_tree(Path(directory))
            target = Path(directory) / "saved"
            vfs = VirtualFileSystem.from_directory(source)
            result = execute_command(f"vfs-save {target}", vfs)
            self.assertFalse(result.is_error)
            self.assertTrue((target / "level-one" / "original.txt").exists())

    def test_command_requires_loaded_virtual_file_system(self) -> None:
        """Команда vfs-save объясняет, почему она недоступна без VFS."""

        result = execute_command("vfs-save output")
        self.assertTrue(result.is_error)
        self.assertIn("VFS не загружена", result.message)


def create_source_tree(base_path: Path) -> Path:
    """Подготовить исходное дерево с текстовым и бинарным файлами."""

    source = base_path / "source"
    nested = source / "level-one" / "level-two"
    nested.mkdir(parents=True)
    (source / "level-one" / "original.txt").write_text(
        "оригинал",
        encoding="utf-8",
    )
    (nested / "data.bin").write_bytes(b"\\x00\\x01\\x02")
    return source
