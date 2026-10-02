"""Параметры запуска эмулятора и чтение стартовых скриптов."""

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class AppConfig:
    """Пути, переданные пользователем при запуске эмулятора."""

    vfs_path: Path | None
    log_path: Path | None
    script_path: Path | None


def parse_arguments(arguments: Sequence[str] | None = None) -> AppConfig:
    """Прочитать поддерживаемые параметры командной строки."""

    parser = argparse.ArgumentParser(description="Эмулятор оболочки ОС")
    parser.add_argument("--vfs-path", help="путь к исходной директории VFS")
    parser.add_argument("--log-path", help="путь к JSON-файлу журнала")
    parser.add_argument("--script-path", help="путь к стартовому скрипту")
    parsed = parser.parse_args(arguments)
    return AppConfig(
        vfs_path=to_path(parsed.vfs_path),
        log_path=to_path(parsed.log_path),
        script_path=to_path(parsed.script_path),
    )


def to_path(value: str | None) -> Path | None:
    """Преобразовать непустое значение параметра в путь."""

    return Path(value) if value else None


def format_configuration(config: AppConfig) -> str:
    """Подготовить отладочный вывод параметров запуска."""

    return "\n".join(
        (
            "Параметры запуска:",
            f"  VFS: {format_path(config.vfs_path)}",
            f"  Лог: {format_path(config.log_path)}",
            f"  Скрипт: {format_path(config.script_path)}",
        )
    )


def format_path(path: Path | None) -> str:
    """Вернуть путь либо отметку об отсутствии параметра."""

    return str(path) if path else "не указан"


def read_startup_script(path: Path) -> list[str]:
    """Прочитать непустые строки стартового скрипта."""

    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
