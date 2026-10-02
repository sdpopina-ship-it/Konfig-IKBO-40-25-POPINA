"""Запись событий вызова команд в JSON-файл."""

import getpass
import json
from datetime import datetime
from pathlib import Path

from src.shell import CommandResult, parse_command


class CommandLogger:
    """Сохраняет историю выполненных команд в JSON-массив."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def log(self, line: str, result: CommandResult) -> str | None:
        """Добавить событие в журнал или вернуть текст ошибки записи."""

        try:
            events = self.load_events()
            events.append(make_event(line, result))
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(events, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except (OSError, ValueError, json.JSONDecodeError) as error:
            return str(error)
        return None

    def load_events(self) -> list[dict[str, object]]:
        """Получить существующие события из файла журнала."""

        if not self.path.exists():
            return []
        events = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(events, list):
            raise ValueError("Журнал должен содержать JSON-массив.")
        return events


def make_event(line: str, result: CommandResult) -> dict[str, object]:
    """Сформировать JSON-событие для одной команды."""

    command, arguments = parse_command(line)
    return {
        "command": command,
        "arguments": arguments,
        "user": getpass.getuser(),
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "success": not result.is_error,
    }
