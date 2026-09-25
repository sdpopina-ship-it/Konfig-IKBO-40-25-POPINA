"""Графический интерфейс эмулятора оболочки ОС."""

import tkinter as tk
from tkinter import scrolledtext

from src.shell import execute_command

VFS_NAME = "demo-vfs"
BACKGROUND = "#1e1e1e"
FOREGROUND = "#d7d7d7"
PROMPT_COLOR = "#78dce8"
FONT = ("Menlo", 14)
PROMPT = "vfs:~$"


class ShellWindow:
    """Окно с историей команд и полем ввода."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(f"Эмулятор оболочки - VFS: {VFS_NAME}")
        self.root.configure(background=BACKGROUND)
        self.root.minsize(640, 360)
        self.output_lines: list[str] = []
        self.command_text = tk.StringVar()
        self.history = scrolledtext.ScrolledText(
            root,
            background=BACKGROUND,
            borderwidth=0,
            font=FONT,
            foreground=FOREGROUND,
            highlightthickness=0,
            selectbackground="#3d6f9d",
            state=tk.DISABLED,
            wrap=tk.WORD,
        )
        self.history.pack(padx=14, pady=(14, 0), fill=tk.BOTH, expand=True)
        self.entry = tk.Entry(
            root,
            background="#292929",
            borderwidth=1,
            font=FONT,
            foreground=FOREGROUND,
            highlightbackground="#4a4a4a",
            highlightcolor=PROMPT_COLOR,
            highlightthickness=1,
            insertbackground=FOREGROUND,
            textvariable=self.command_text,
        )
        self.entry.pack(padx=14, pady=(8, 14), fill=tk.X)
        self.entry.bind("<Return>", self.handle_input)
        self.command_text.trace_add("write", self.refresh_history)
        self.refresh_history()
        self.entry.focus_set()

    def handle_input(self, _event: tk.Event) -> None:
        """Показать введённую строку и результат её обработки."""

        line = self.command_text.get()
        self.output_lines.append(self.active_prompt())
        result = execute_command(line)
        self.output_lines.append(result.message)
        self.command_text.set("")
        if result.should_exit:
            self.root.after(400, self.root.destroy)

    def active_prompt(self) -> str:
        """Вернуть текущую строку приглашения вместе с набираемой командой."""

        command = self.command_text.get()
        return f"{PROMPT} {command}" if command else PROMPT

    def refresh_history(self, *_args: str) -> None:
        """Обновить историю, не разрешая пользователю редактировать её."""

        text = "\n".join([*self.output_lines, self.active_prompt()])
        self.history.configure(state=tk.NORMAL)
        self.history.delete("1.0", tk.END)
        self.history.insert("1.0", text)
        self.history.see(tk.END)
        self.history.configure(state=tk.DISABLED)


def main() -> None:
    """Создать и запустить окно приложения."""

    root = tk.Tk()
    ShellWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
