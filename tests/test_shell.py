"""Проверки логики команд без запуска графического окна."""

import unittest

from src.shell import execute_command, parse_command


class ParseCommandTests(unittest.TestCase):
    """Проверки разбора строки команды."""

    def test_parses_command_and_arguments(self) -> None:
        self.assertEqual(parse_command("ls folder file"), ("ls", ["folder", "file"]))

    def test_ignores_extra_spaces(self) -> None:
        self.assertEqual(parse_command("  cd   folder  "), ("cd", ["folder"]))


class ExecuteCommandTests(unittest.TestCase):
    """Проверки результатов выполнения команд."""

    def test_stub_prints_its_name_and_arguments(self) -> None:
        result = execute_command("ls documents")
        self.assertEqual(result.message, "Команда: ls; аргументы: documents")
        self.assertFalse(result.should_exit)

    def test_unknown_command_returns_error(self) -> None:
        result = execute_command("pwd")
        self.assertIn("неизвестная команда", result.message)
        self.assertTrue(result.is_error)

    def test_exit_without_arguments_closes_application(self) -> None:
        result = execute_command("exit")
        self.assertTrue(result.should_exit)

    def test_exit_with_arguments_returns_error(self) -> None:
        result = execute_command("exit now")
        self.assertIn("не принимает аргументы", result.message)
        self.assertTrue(result.is_error)


if __name__ == "__main__":
    unittest.main()
