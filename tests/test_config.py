"""Проверки параметров запуска, скриптов и JSON-журнала."""

import json
import tempfile
import unittest
from pathlib import Path

from src.command_log import CommandLogger
from src.config import format_configuration, parse_arguments, read_startup_script
from src.shell import execute_command


class ConfigurationTests(unittest.TestCase):
    """Проверки параметров командной строки."""

    def test_reads_all_supported_paths(self) -> None:
        config = parse_arguments(
            [
                "--vfs-path",
                "example-vfs",
                "--log-path",
                "logs/commands.json",
                "--script-path",
                "scripts/startup.txt",
            ]
        )
        self.assertEqual(config.vfs_path, Path("example-vfs"))
        self.assertEqual(config.log_path, Path("logs/commands.json"))
        self.assertEqual(config.script_path, Path("scripts/startup.txt"))

    def test_formats_debug_information(self) -> None:
        config = parse_arguments(["--vfs-path", "example-vfs"])
        self.assertIn("example-vfs", format_configuration(config))
        self.assertIn("не указан", format_configuration(config))


class ScriptAndLogTests(unittest.TestCase):
    """Проверки стартового скрипта и журнала команд."""

    def test_reads_nonempty_script_lines(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "startup.txt"
            path.write_text("ls\n\ncd documents\n", encoding="utf-8")
            self.assertEqual(read_startup_script(path), ["ls", "cd documents"])

    def test_writes_command_event_to_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "commands.json"
            logger = CommandLogger(path)
            error = logger.log("ls documents", execute_command("ls documents"))
            self.assertIsNone(error)
            events = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(events[0]["command"], "ls")
            self.assertEqual(events[0]["arguments"], ["documents"])
            self.assertIn("user", events[0])
            self.assertIn("timestamp", events[0])


if __name__ == "__main__":
    unittest.main()
