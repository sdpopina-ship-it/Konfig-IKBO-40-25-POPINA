"""Проверки команд оболочки без запуска графического окна."""

import unittest

from src.shell import execute_command, parse_command
from src.vfs import VfsDirectory, VfsFile, VirtualFileSystem


class ParseCommandTests(unittest.TestCase):
    """Проверки разбора строки команды."""

    def test_parses_command_and_arguments(self) -> None:
        """Первое слово становится командой, остальные — аргументами."""

        expected = ("ls", ["folder", "file"])
        self.assertEqual(parse_command("ls folder file"), expected)

    def test_ignores_extra_spaces(self) -> None:
        """Лишние пробелы не попадают в аргументы."""

        self.assertEqual(parse_command("  cd   folder  "), ("cd", ["folder"]))


class ShellCommandTests(unittest.TestCase):
    """Проверки поведения команд с загруженной VFS."""

    def setUp(self) -> None:
        """Подготовить VFS с каталогом, текстовыми и скрытыми файлами."""

        records = "\n".join(f"line-{number}" for number in range(1, 13))
        self.vfs = VirtualFileSystem(
            "test-vfs",
            VfsDirectory(
                {
                    ".hidden.txt": VfsFile(b"secret"),
                    "docs": VfsDirectory(
                        {"guide.txt": VfsFile(b"alpha\nbeta\ngamma\n")}
                    ),
                    "records.txt": VfsFile(records.encode("utf-8")),
                }
            ),
        )

    def test_ls_hides_dot_files_without_a_flag(self) -> None:
        """Обычный ls не показывает скрытые файлы."""

        result = execute_command("ls", self.vfs)
        self.assertEqual(result.message, "docs\nrecords.txt")

    def test_ls_supports_combined_flags_in_any_order(self) -> None:
        """Каждая перестановка -l, -a и -h даёт расширенный вывод."""

        for flags in ("-lah", "-lha", "-alh", "-ahl", "-hla", "-hal"):
            with self.subTest(flags=flags):
                result = execute_command(f"ls {flags}", self.vfs)
                self.assertIn(".hidden.txt", result.message)
                self.assertIn("drwxr-xr-x", result.message)
                self.assertIn("6B .hidden.txt", result.message)

    def test_ls_rejects_unknown_flag(self) -> None:
        """Неизвестный флаг ls возвращает понятную ошибку."""

        result = execute_command("ls -z", self.vfs)
        self.assertTrue(result.is_error)
        self.assertIn("неизвестный флаг", result.message)

    def test_cd_supports_relative_and_absolute_paths(self) -> None:
        """cd понимает относительные, абсолютные пути и возврат к корню."""

        relative = execute_command("cd docs", self.vfs)
        self.assertEqual(relative.working_path, ("docs",))
        absolute = execute_command("cd /", self.vfs, relative.working_path)
        self.assertEqual(absolute.working_path, ())
        direct = execute_command("cd /docs", self.vfs)
        self.assertEqual(direct.working_path, ("docs",))
        parent = execute_command("cd ..", self.vfs, direct.working_path)
        self.assertEqual(parent.working_path, ())
        root = execute_command("cd ../../..", self.vfs)
        self.assertEqual(root.working_path, ())

    def test_cd_rejects_file_path(self) -> None:
        """cd не разрешает перейти в объект, который является файлом."""

        result = execute_command("cd records.txt", self.vfs)
        self.assertTrue(result.is_error)
        self.assertIn("не каталог", result.message)

    def test_rev_reverses_each_text_line(self) -> None:
        """rev переворачивает символы в каждой строке указанного файла."""

        result = execute_command("rev docs/guide.txt", self.vfs)
        self.assertEqual(result.message, "ahpla\nateb\nammag")

    def test_tail_supports_default_and_n_flag(self) -> None:
        """tail выводит десять строк по умолчанию и число после -n."""

        default = execute_command("tail records.txt", self.vfs)
        self.assertTrue(default.message.startswith("line-3"))
        two_lines = execute_command("tail -n 2 records.txt", self.vfs)
        self.assertEqual(two_lines.message, "line-11\nline-12")
        compact = execute_command("tail -n1 records.txt", self.vfs)
        self.assertEqual(compact.message, "line-12")

    def test_vfs_command_requires_loaded_file_system(self) -> None:
        """Команды VFS объясняют, почему они недоступны без снимка."""

        result = execute_command("ls")
        self.assertTrue(result.is_error)
        self.assertIn("VFS не загружена", result.message)

    def test_exit_behaviour_is_preserved(self) -> None:
        """exit завершает приложение только без аргументов."""

        correct = execute_command("exit", self.vfs)
        incorrect = execute_command("exit now", self.vfs)
        self.assertTrue(correct.should_exit)
        self.assertTrue(incorrect.is_error)


if __name__ == "__main__":
    unittest.main()
