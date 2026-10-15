"""Разбор и обработка команд первого этапа."""

from dataclasses import dataclass
from pathlib import Path

from src.vfs import VfsError, VirtualFileSystem


@dataclass(frozen=True)
class CommandResult:
    """Результат выполнения одной команды."""

    message: str
    should_exit: bool = False
    is_error: bool = False


def parse_command(line: str) -> tuple[str, list[str]]:
    """Разделить строку на имя команды и аргументы по пробелам."""

    parts = line.strip().split()
    if not parts:
        return "", []
    return parts[0], parts[1:]


def execute_command(
    line: str,
    vfs: VirtualFileSystem | None = None,
) -> CommandResult:
    """Выполнить поддерживаемую команду или вернуть сообщение об ошибке."""

    command, arguments = parse_command(line)
    if not command:
        return CommandResult("Ошибка: введите команду.", is_error=True)
    if command == "exit":
        return execute_exit(arguments)
    if command == "vfs-save":
        return execute_vfs_save(arguments, vfs)
    if command in {"ls", "cd"}:
        return execute_stub(command, arguments)
    return CommandResult(
        f"Ошибка: неизвестная команда: {command}",
        is_error=True,
    )


def execute_exit(arguments: list[str]) -> CommandResult:
    """Обработать команду завершения приложения."""

    if arguments:
        return CommandResult(
            "Ошибка: команда exit не принимает аргументы.",
            is_error=True,
        )
    return CommandResult("Завершение работы.", should_exit=True)


def execute_stub(command: str, arguments: list[str]) -> CommandResult:
    """Вывести имя команды-заглушки и её аргументы."""

    arguments_text = " ".join(arguments) if arguments else "нет"
    return CommandResult(f"Команда: {command}; аргументы: {arguments_text}")


def execute_vfs_save(
    arguments: list[str],
    vfs: VirtualFileSystem | None,
) -> CommandResult:
    """Сохранить загруженный снимок VFS в новый каталог."""

    if not vfs:
        return CommandResult(
            "Ошибка: VFS не загружена. Укажите --vfs-path при запуске.",
            is_error=True,
        )
    if len(arguments) != 1:
        return CommandResult(
            "Ошибка: используйте vfs-save <путь>.",
            is_error=True,
        )
    try:
        vfs.save_to_directory(Path(arguments[0]))
    except (OSError, VfsError) as error:
        return CommandResult(f"Ошибка сохранения VFS: {error}", is_error=True)
    return CommandResult(f"VFS сохранена в: {arguments[0]}")
