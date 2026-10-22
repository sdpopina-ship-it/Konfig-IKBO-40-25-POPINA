"""Разбор и обработка команд эмулятора оболочки ОС."""

from dataclasses import dataclass
from pathlib import Path

from src.vfs import VfsDirectory, VfsError, VfsFile, VfsNode, VirtualFileSystem

BYTES_PER_KILOBYTE = 1024
TAIL_SHORT_OPTION_PREFIX_LENGTH = len("-n")
CHMOD_ARGUMENT_COUNT = len(("permissions", "path"))
OCTAL_BASE = 8
OCTAL_DIGITS = "01234567"
OCTAL_PREFIX = "0o"
PERMISSION_DIGIT_COUNT = len("755")


@dataclass(frozen=True)
class CommandResult:
    """Результат выполнения одной команды."""

    message: str
    should_exit: bool = False
    is_error: bool = False
    working_path: tuple[str, ...] | None = None


def parse_command(line: str) -> tuple[str, list[str]]:
    """Разделить строку на имя команды и аргументы по пробелам."""

    parts = line.strip().split()
    if not parts:
        return "", []
    return parts[0], parts[1:]


def execute_command(
    line: str,
    vfs: VirtualFileSystem | None = None,
    current_path: tuple[str, ...] = (),
) -> CommandResult:
    """Выполнить поддерживаемую команду или вернуть сообщение об ошибке."""

    command, arguments = parse_command(line)
    if not command:
        return CommandResult("Ошибка: введите команду.", is_error=True)
    if command == "exit":
        return execute_exit(arguments)
    if command == "vfs-save":
        return execute_vfs_save(arguments, vfs)
    if command == "ls":
        return execute_ls(arguments, vfs, current_path)
    if command == "cd":
        return execute_cd(arguments, vfs, current_path)
    if command == "rev":
        return execute_rev(arguments, vfs, current_path)
    if command == "tail":
        return execute_tail(arguments, vfs, current_path)
    if command == "chmod":
        return execute_chmod(arguments, vfs, current_path)
    if command == "rmdir":
        return execute_rmdir(arguments, vfs, current_path)
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


def execute_vfs_save(
    arguments: list[str],
    vfs: VirtualFileSystem | None,
) -> CommandResult:
    """Сохранить загруженный снимок VFS в новый каталог."""

    if not vfs:
        return vfs_not_loaded_error()
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


def execute_ls(
    arguments: list[str],
    vfs: VirtualFileSystem | None,
    current_path: tuple[str, ...],
) -> CommandResult:
    """Вывести содержимое файла или каталога с флагами ls."""

    if not vfs:
        return vfs_not_loaded_error()
    try:
        flags, path = parse_ls_arguments(arguments)
        node, parts = vfs.resolve(path, current_path)
        message = format_listing(node, parts, flags)
    except VfsError as error:
        return CommandResult(f"Ошибка ls: {error}", is_error=True)
    return CommandResult(message)


def execute_cd(
    arguments: list[str],
    vfs: VirtualFileSystem | None,
    current_path: tuple[str, ...],
) -> CommandResult:
    """Перейти в каталог VFS по абсолютному или относительному пути."""

    if not vfs:
        return vfs_not_loaded_error()
    if len(arguments) > 1:
        return CommandResult("Ошибка: используйте cd [путь].", is_error=True)
    path = arguments[0] if arguments else "~"
    try:
        node, parts = vfs.resolve(path, current_path)
    except VfsError as error:
        return CommandResult(f"Ошибка cd: {error}", is_error=True)
    if not isinstance(node, VfsDirectory):
        message = f"Ошибка cd: это не каталог: {path}"
        return CommandResult(message, is_error=True)
    return CommandResult("", working_path=parts)


def execute_rev(
    arguments: list[str],
    vfs: VirtualFileSystem | None,
    current_path: tuple[str, ...],
) -> CommandResult:
    """Вывести строки текстового файла в обратном порядке символов."""

    text = read_command_file("rev", arguments, vfs, current_path)
    if isinstance(text, CommandResult):
        return text
    return CommandResult("\n".join(line[::-1] for line in text.splitlines()))


def execute_tail(
    arguments: list[str],
    vfs: VirtualFileSystem | None,
    current_path: tuple[str, ...],
) -> CommandResult:
    """Вывести последние строки текстового файла, как команда tail."""

    try:
        count, path = parse_tail_arguments(arguments)
    except VfsError as error:
        return CommandResult(f"Ошибка tail: {error}", is_error=True)
    text = read_command_file("tail", [path], vfs, current_path)
    if isinstance(text, CommandResult):
        return text
    lines = text.splitlines()
    return CommandResult("\n".join(lines[-count:] if count else []))


def execute_chmod(
    arguments: list[str],
    vfs: VirtualFileSystem | None,
    current_path: tuple[str, ...],
) -> CommandResult:
    """Изменить права файла или каталога в памяти VFS."""

    if not vfs:
        return vfs_not_loaded_error()
    if len(arguments) != CHMOD_ARGUMENT_COUNT:
        return CommandResult(
            "Ошибка: используйте chmod <права> <путь>.",
            is_error=True,
        )
    try:
        mode = parse_permission_mode(arguments[0])
        vfs.change_mode(arguments[1], mode, current_path)
    except VfsError as error:
        return CommandResult(f"Ошибка chmod: {error}", is_error=True)
    return CommandResult(f"Права изменены: {arguments[1]} -> {mode:03o}")


def execute_rmdir(
    arguments: list[str],
    vfs: VirtualFileSystem | None,
    current_path: tuple[str, ...],
) -> CommandResult:
    """Удалить пустой каталог только из снимка VFS в памяти."""

    if not vfs:
        return vfs_not_loaded_error()
    if len(arguments) != 1:
        return CommandResult("Ошибка: используйте rmdir <путь>.", is_error=True)
    try:
        vfs.remove_empty_directory(arguments[0], current_path)
    except VfsError as error:
        return CommandResult(f"Ошибка rmdir: {error}", is_error=True)
    return CommandResult(f"Каталог удалён из VFS: {arguments[0]}")


def parse_ls_arguments(arguments: list[str]) -> tuple[set[str], str]:
    """Прочитать флаги -l, -a, -h и необязательный путь команды ls."""

    flags: set[str] = set()
    paths: list[str] = []
    for argument in arguments:
        if argument.startswith("-") and argument != "-":
            flags.update(parse_ls_flags(argument))
        else:
            paths.append(argument)
    if len(paths) > 1:
        raise VfsError("команда ls принимает не более одного пути")
    return flags, paths[0] if paths else "."


def parse_ls_flags(argument: str) -> set[str]:
    """Разобрать одну объединённую группу флагов команды ls."""

    flags = set(argument[1:])
    unknown = flags - {"l", "a", "h"}
    if unknown:
        raise VfsError(f"неизвестный флаг: -{''.join(sorted(unknown))}")
    return flags


def format_listing(
    node: VfsNode,
    parts: tuple[str, ...],
    flags: set[str],
) -> str:
    """Подготовить строки вывода ls для файла или каталога VFS."""

    if isinstance(node, VfsFile):
        name = parts[-1] if parts else ""
        return format_listing_entry(name, node, flags)
    entries = list(node.children.items())
    if "a" in flags:
        entries = [(".", node), ("..", node), *entries]
    entries = filter_hidden_entries(entries, flags)
    entries.sort(key=lambda item: item[0])
    lines = [format_listing_entry(name, item, flags) for name, item in entries]
    return "\n".join(lines)


def filter_hidden_entries(
    entries: list[tuple[str, VfsNode]],
    flags: set[str],
) -> list[tuple[str, VfsNode]]:
    """Исключить скрытые имена, если флаг -a не был передан."""

    if "a" in flags:
        return entries
    return [(name, node) for name, node in entries if not name.startswith(".")]


def format_listing_entry(name: str, node: VfsNode, flags: set[str]) -> str:
    """Оформить одну строку ls с именем либо с расширенными атрибутами."""

    if "l" not in flags:
        return name
    size = format_size(node_size(node), "h" in flags)
    return f"{format_permissions(node)} {size:>6} {name}"


def node_size(node: VfsNode) -> int:
    """Вернуть размер файла либо нулевой размер каталога для вывода ls."""

    return len(node.content) if isinstance(node, VfsFile) else 0


def format_size(size: int, human_readable: bool) -> str:
    """Вернуть числовой либо компактный человекочитаемый размер."""

    if not human_readable:
        return str(size)
    units = ("B", "K", "M", "G")
    value = float(size)
    for unit in units:
        if value < BYTES_PER_KILOBYTE or unit == units[-1]:
            return f"{value:g}{unit}"
        value /= BYTES_PER_KILOBYTE
    return f"{size}B"


def format_permissions(node: VfsNode) -> str:
    """Сформировать строку прав доступа в стиле ls -l."""

    prefix = "d" if isinstance(node, VfsDirectory) else "-"
    groups = (
        permission_group(node.mode, (0o400, 0o200, 0o100)),
        permission_group(node.mode, (0o040, 0o020, 0o010)),
        permission_group(node.mode, (0o004, 0o002, 0o001)),
    )
    return prefix + "".join(groups)


def permission_group(mode: int, bits: tuple[int, int, int]) -> str:
    """Оформить одну группу прав доступа: пользователь, группа или остальные."""

    return "".join(symbol if mode & bit else "-"
                   for symbol, bit in zip("rwx", bits, strict=True))


def parse_tail_arguments(arguments: list[str]) -> tuple[int, str]:
    """Разобрать путь и флаг -n команды tail."""

    count = 10
    paths: list[str] = []
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument == "-n":
            index += 1
            if index >= len(arguments):
                raise VfsError("после -n нужно указать число")
            count = parse_tail_count(arguments[index])
        elif argument.startswith("-n") and (
            len(argument) > TAIL_SHORT_OPTION_PREFIX_LENGTH
        ):
            count = parse_tail_count(argument[TAIL_SHORT_OPTION_PREFIX_LENGTH:])
        else:
            paths.append(argument)
        index += 1
    if len(paths) != 1:
        raise VfsError("используйте tail [-n число] <файл>")
    return count, paths[0]


def parse_permission_mode(value: str) -> int:
    """Прочитать три восьмеричные цифры прав доступа команды chmod."""

    mode_text = value.lower().removeprefix(OCTAL_PREFIX)
    if mode_text.startswith("0") and len(mode_text) > PERMISSION_DIGIT_COUNT:
        mode_text = mode_text[1:]
    if len(mode_text) != PERMISSION_DIGIT_COUNT:
        raise VfsError("права должны состоять из трёх восьмеричных цифр")
    if any(digit not in OCTAL_DIGITS for digit in mode_text):
        raise VfsError("права должны состоять из цифр от 0 до 7")
    return int(mode_text, OCTAL_BASE)


def parse_tail_count(value: str) -> int:
    """Проверить число строк, запрошенное в tail."""

    try:
        count = int(value)
    except ValueError as error:
        raise VfsError("число строк должно быть целым") from error
    if count < 0:
        raise VfsError("число строк не может быть отрицательным")
    return count


def read_command_file(
    command: str,
    arguments: list[str],
    vfs: VirtualFileSystem | None,
    current_path: tuple[str, ...],
) -> str | CommandResult:
    """Прочитать один текстовый файл для команды rev или tail."""

    if not vfs:
        return vfs_not_loaded_error()
    if len(arguments) != 1:
        return CommandResult(
            f"Ошибка {command}: используйте {command} <файл>.",
            is_error=True,
        )
    try:
        return vfs.read_text(arguments[0], current_path)
    except VfsError as error:
        return CommandResult(f"Ошибка {command}: {error}", is_error=True)


def vfs_not_loaded_error() -> CommandResult:
    """Вернуть общую ошибку для команд, которым требуется загруженная VFS."""

    return CommandResult(
        "Ошибка: VFS не загружена. Укажите --vfs-path при запуске.",
        is_error=True,
    )
