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

    def test_rmdir_changes_snapshot_without_changing_source(self) -> None:
        """Удаление пустого каталога не затрагивает исходную папку на диске."""

        with tempfile.TemporaryDirectory() as directory:
            source = create_source_tree(Path(directory))
            empty_directory = source / "empty"
            empty_directory.mkdir()
            vfs = VirtualFileSystem.from_directory(source)
            vfs.remove_empty_directory("empty")
            self.assertTrue(empty_directory.is_dir())
            with self.assertRaises(VfsError):
                vfs.resolve("empty")

    def test_chmod_changes_snapshot_without_changing_source(self) -> None:
        """Изменение прав VFS не меняет права исходного файла на диске."""

        with tempfile.TemporaryDirectory() as directory:
            source = create_source_tree(Path(directory))
            source_file = source / "level-one" / "original.txt"
            source_file.chmod(0o644)
            vfs = VirtualFileSystem.from_directory(source)
            vfs.change_mode("level-one/original.txt", 0o600)
            node, _ = vfs.resolve("level-one/original.txt")
            self.assertEqual(node.mode, 0o600)
            self.assertEqual(source_file.stat().st_mode & 0o777, 0o644)


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
