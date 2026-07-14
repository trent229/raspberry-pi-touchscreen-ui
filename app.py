#!/usr/bin/env python3
"""Touchscreen Control Center for Raspberry Pi OS.

Designed for a Raspberry Pi Zero W and a small HDMI touchscreen. The interface
uses only the Python standard library so it remains lightweight and easy to
deploy.
"""

from __future__ import annotations

import datetime as dt
import os
import shutil
import socket
import subprocess
import tkinter as tk
from pathlib import Path
from typing import Callable


BG = "#07111f"
PANEL = "#0d1b2d"
PANEL_ALT = "#12243a"
CYAN = "#24d6e5"
BLUE = "#3388ff"
GREEN = "#58e39b"
AMBER = "#ffbd59"
RED = "#ff667a"
TEXT = "#f2f7fb"
MUTED = "#8fa6bd"


def read_text(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except (OSError, ValueError):
        return ""


def cpu_temperature() -> str:
    raw = read_text("/sys/class/thermal/thermal_zone0/temp")
    try:
        return f"{int(raw) / 1000:.1f} °C"
    except ValueError:
        return "Unavailable"


def memory_status() -> tuple[str, str]:
    values: dict[str, int] = {}
    for line in read_text("/proc/meminfo").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        try:
            values[key] = int(value.strip().split()[0])
        except (ValueError, IndexError):
            continue

    total = values.get("MemTotal", 0)
    available = values.get("MemAvailable", 0)
    used = max(total - available, 0)
    if not total:
        return "Unavailable", "0%"
    return f"{used / 1024:.0f} / {total / 1024:.0f} MB", f"{used / total * 100:.0f}%"


def disk_status() -> tuple[str, str]:
    try:
        total, used, _ = shutil.disk_usage("/")
    except OSError:
        return "Unavailable", "0%"
    gib = 1024**3
    return f"{used / gib:.1f} / {total / gib:.1f} GB", f"{used / total * 100:.0f}%"


def ip_address() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.2)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "Not connected"
    finally:
        sock.close()


def wifi_quality() -> str:
    lines = read_text("/proc/net/wireless").splitlines()
    if len(lines) < 3:
        return "No Wi-Fi signal"
    try:
        fields = lines[2].split()
        quality = float(fields[2].rstrip("."))
        percent = max(0, min(100, round(quality / 70 * 100)))
        return f"Wi-Fi {percent}%"
    except (ValueError, IndexError):
        return "Wi-Fi connected"


def uptime() -> str:
    try:
        seconds = int(float(read_text("/proc/uptime").split()[0]))
    except (ValueError, IndexError):
        return "Unavailable"
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes = seconds // 60
    if days:
        return f"{days}d {hours}h {minutes}m"
    return f"{hours}h {minutes}m"


class StatusCard(tk.Frame):
    def __init__(self, parent: tk.Widget, title: str, accent: str) -> None:
        super().__init__(parent, bg=PANEL, highlightbackground="#1d3650", highlightthickness=1)
        self.columnconfigure(0, weight=1)
        self.accent = tk.Frame(self, bg=accent, width=5)
        self.accent.grid(row=0, column=0, rowspan=3, sticky="nsw")
        self.title = tk.Label(self, text=title.upper(), bg=PANEL, fg=MUTED, anchor="w")
        self.title.grid(row=0, column=0, sticky="new", padx=(18, 10), pady=(10, 0))
        self.value = tk.Label(self, text="--", bg=PANEL, fg=TEXT, anchor="w")
        self.value.grid(row=1, column=0, sticky="new", padx=(18, 10), pady=(2, 0))
        self.detail = tk.Label(self, text="", bg=PANEL, fg=accent, anchor="w")
        self.detail.grid(row=2, column=0, sticky="new", padx=(18, 10), pady=(0, 10))

    def set_fonts(self, small: tuple, large: tuple) -> None:
        self.title.configure(font=small)
        self.value.configure(font=large)
        self.detail.configure(font=small)

    def update_value(self, value: str, detail: str = "") -> None:
        self.value.configure(text=value)
        self.detail.configure(text=detail)


class TouchControlApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Touchscreen Control Center")
        self.configure(bg=BG)
        self.attributes("-fullscreen", True)
        self.bind("<F11>", self.toggle_fullscreen)
        self.bind("<Escape>", lambda _event: self.attributes("-fullscreen", False))

        width = max(self.winfo_screenwidth(), 800)
        height = max(self.winfo_screenheight(), 480)
        self.scale = max(0.8, min(width / 1024, height / 600))
        self.font_small = ("DejaVu Sans", max(9, int(11 * self.scale)))
        self.font_body = ("DejaVu Sans", max(11, int(14 * self.scale)))
        self.font_button = ("DejaVu Sans", max(10, int(13 * self.scale)), "bold")
        self.font_value = ("DejaVu Sans", max(17, int(24 * self.scale)), "bold")
        self.font_heading = ("DejaVu Sans", max(18, int(27 * self.scale)), "bold")

        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.pages: dict[str, tk.Frame] = {}
        self.nav_buttons: dict[str, tk.Button] = {}
        self.active_page = "Dashboard"

        self.build_header()
        self.build_pages()
        self.build_navigation()
        self.show_page("Dashboard")
        self.refresh_status()

    def build_header(self) -> None:
        header = tk.Frame(self, bg=BG, height=int(76 * self.scale))
        header.grid(row=0, column=0, sticky="ew", padx=int(20 * self.scale), pady=(int(10 * self.scale), 0))
        header.columnconfigure(0, weight=1)

        title_wrap = tk.Frame(header, bg=BG)
        title_wrap.grid(row=0, column=0, sticky="w")
        tk.Label(title_wrap, text="TOUCH", bg=BG, fg=CYAN, font=self.font_heading).pack(side="left")
        tk.Label(title_wrap, text=" CONTROL", bg=BG, fg=TEXT, font=self.font_heading).pack(side="left")
        tk.Label(
            header,
            text="EMBEDDED USER INTERFACE",
            bg=BG,
            fg=MUTED,
            font=self.font_small,
        ).grid(row=1, column=0, sticky="w")

        self.clock_label = tk.Label(header, text="", bg=BG, fg=TEXT, font=self.font_value, anchor="e")
        self.clock_label.grid(row=0, column=1, sticky="e")
        self.date_label = tk.Label(header, text="", bg=BG, fg=MUTED, font=self.font_small, anchor="e")
        self.date_label.grid(row=1, column=1, sticky="e")

    def build_pages(self) -> None:
        container = tk.Frame(self, bg=BG)
        container.grid(row=1, column=0, sticky="nsew", padx=int(20 * self.scale), pady=int(10 * self.scale))
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        for name in ("Dashboard", "Touch Test", "System", "Power"):
            page = tk.Frame(container, bg=BG)
            page.grid(row=0, column=0, sticky="nsew")
            self.pages[name] = page

        self.build_dashboard(self.pages["Dashboard"])
        self.build_touch_test(self.pages["Touch Test"])
        self.build_system_page(self.pages["System"])
        self.build_power_page(self.pages["Power"])

    def build_dashboard(self, page: tk.Frame) -> None:
        for row in range(2):
            page.rowconfigure(row, weight=1, uniform="card")
        for column in range(2):
            page.columnconfigure(column, weight=1, uniform="card")

        self.temp_card = StatusCard(page, "Processor temperature", CYAN)
        self.memory_card = StatusCard(page, "Memory", BLUE)
        self.network_card = StatusCard(page, "Network", GREEN)
        self.storage_card = StatusCard(page, "Storage", AMBER)
        cards = (self.temp_card, self.memory_card, self.network_card, self.storage_card)
        for index, card in enumerate(cards):
            card.grid(
                row=index // 2,
                column=index % 2,
                sticky="nsew",
                padx=(0 if index % 2 == 0 else 6, 6 if index % 2 == 0 else 0),
                pady=(0 if index < 2 else 6, 6 if index < 2 else 0),
            )
            card.set_fonts(self.font_small, self.font_value)

    def build_touch_test(self, page: tk.Frame) -> None:
        page.rowconfigure(1, weight=1)
        page.columnconfigure(0, weight=1)

        top = tk.Frame(page, bg=BG)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        top.columnconfigure(0, weight=1)
        tk.Label(
            top,
            text="TOUCH TEST — drag a finger across the panel",
            bg=BG,
            fg=TEXT,
            font=self.font_body,
        ).grid(row=0, column=0, sticky="w")
        tk.Button(
            top,
            text="CLEAR",
            command=lambda: self.touch_canvas.delete("stroke"),
            bg=PANEL_ALT,
            fg=TEXT,
            activebackground=BLUE,
            activeforeground=TEXT,
            relief="flat",
            font=self.font_button,
            padx=20,
            pady=8,
        ).grid(row=0, column=1, sticky="e")

        self.touch_canvas = tk.Canvas(
            page,
            bg="#091827",
            highlightbackground="#1d3650",
            highlightthickness=1,
            cursor="crosshair",
        )
        self.touch_canvas.grid(row=1, column=0, sticky="nsew")
        self.touch_canvas.bind("<Button-1>", self.draw_touch)
        self.touch_canvas.bind("<B1-Motion>", self.draw_touch)

    def build_system_page(self, page: tk.Frame) -> None:
        page.columnconfigure(1, weight=1)
        fields = ("Hostname", "IP address", "Wi-Fi", "Uptime", "Processor load", "Display")
        self.system_values: dict[str, tk.Label] = {}
        for row, field in enumerate(fields):
            tk.Label(
                page,
                text=field.upper(),
                bg=BG,
                fg=MUTED,
                font=self.font_small,
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=(10, 30), pady=10)
            value = tk.Label(
                page,
                text="--",
                bg=PANEL,
                fg=TEXT,
                font=self.font_body,
                anchor="w",
                padx=18,
                pady=8,
            )
            value.grid(row=row, column=1, sticky="ew", pady=5)
            self.system_values[field] = value

    def build_power_page(self, page: tk.Frame) -> None:
        for column in range(3):
            page.columnconfigure(column, weight=1, uniform="power")
        page.rowconfigure(0, weight=1)

        actions: tuple[tuple[str, str, Callable[[], None]], ...] = (
            ("RESTART", AMBER, lambda: self.confirm_power("restart")),
            ("SHUT DOWN", RED, lambda: self.confirm_power("poweroff")),
            ("EXIT UI", BLUE, self.destroy),
        )
        for column, (label, color, command) in enumerate(actions):
            button = tk.Button(
                page,
                text=label,
                command=command,
                bg=PANEL,
                fg=color,
                activebackground=color,
                activeforeground=BG,
                highlightbackground=color,
                highlightthickness=2,
                relief="flat",
                font=self.font_value,
            )
            button.grid(row=0, column=column, sticky="nsew", padx=6, pady=20)

    def build_navigation(self) -> None:
        nav = tk.Frame(self, bg=PANEL, height=int(70 * self.scale))
        nav.grid(row=2, column=0, sticky="ew")
        names = ("Dashboard", "Touch Test", "System", "Power")
        for column, name in enumerate(names):
            nav.columnconfigure(column, weight=1, uniform="nav")
            button = tk.Button(
                nav,
                text=name.upper(),
                command=lambda selected=name: self.show_page(selected),
                bg=PANEL,
                fg=MUTED,
                activebackground=PANEL_ALT,
                activeforeground=CYAN,
                relief="flat",
                bd=0,
                font=self.font_button,
                pady=max(10, int(16 * self.scale)),
            )
            button.grid(row=0, column=column, sticky="nsew")
            self.nav_buttons[name] = button

    def show_page(self, name: str) -> None:
        self.active_page = name
        self.pages[name].tkraise()
        for button_name, button in self.nav_buttons.items():
            selected = button_name == name
            button.configure(
                fg=CYAN if selected else MUTED,
                bg=PANEL_ALT if selected else PANEL,
            )

    def draw_touch(self, event: tk.Event) -> None:
        radius = max(8, int(11 * self.scale))
        self.touch_canvas.create_oval(
            event.x - radius,
            event.y - radius,
            event.x + radius,
            event.y + radius,
            fill=CYAN,
            outline="",
            tags="stroke",
        )

    def refresh_status(self) -> None:
        now = dt.datetime.now()
        self.clock_label.configure(text=now.strftime("%I:%M:%S %p").lstrip("0"))
        self.date_label.configure(text=now.strftime("%A, %B %d, %Y"))

        temperature = cpu_temperature()
        memory_value, memory_percent = memory_status()
        storage_value, storage_percent = disk_status()
        address = ip_address()
        wifi = wifi_quality()

        self.temp_card.update_value(temperature, "NORMAL" if temperature != "Unavailable" else "CHECK SENSOR")
        self.memory_card.update_value(memory_value, f"{memory_percent} USED")
        self.network_card.update_value(address, wifi.upper())
        self.storage_card.update_value(storage_value, f"{storage_percent} USED")

        try:
            load = f"{os.getloadavg()[0]:.2f} (1 minute)"
        except OSError:
            load = "Unavailable"
        self.system_values["Hostname"].configure(text=socket.gethostname())
        self.system_values["IP address"].configure(text=address)
        self.system_values["Wi-Fi"].configure(text=wifi)
        self.system_values["Uptime"].configure(text=uptime())
        self.system_values["Processor load"].configure(text=load)
        self.system_values["Display"].configure(
            text=f"{self.winfo_screenwidth()} × {self.winfo_screenheight()}"
        )

        self.after(1000, self.refresh_status)

    def confirm_power(self, action: str) -> None:
        overlay = tk.Frame(self, bg="#02070d", highlightbackground=CYAN, highlightthickness=2)
        overlay.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.62, relheight=0.42)
        for column in range(2):
            overlay.columnconfigure(column, weight=1)
        overlay.rowconfigure(0, weight=1)

        label = "RESTART" if action == "restart" else "SHUT DOWN"
        tk.Label(
            overlay,
            text=f"CONFIRM {label}?",
            bg="#02070d",
            fg=TEXT,
            font=self.font_heading,
        ).grid(row=0, column=0, columnspan=2, pady=(25, 10))
        tk.Button(
            overlay,
            text="CANCEL",
            command=overlay.destroy,
            bg=PANEL,
            fg=TEXT,
            activebackground=PANEL_ALT,
            activeforeground=TEXT,
            relief="flat",
            font=self.font_button,
            pady=15,
        ).grid(row=1, column=0, sticky="ew", padx=(20, 8), pady=(0, 22))
        tk.Button(
            overlay,
            text="CONFIRM",
            command=lambda: self.run_power_action(action),
            bg=RED if action == "poweroff" else AMBER,
            fg=BG,
            activebackground=TEXT,
            activeforeground=BG,
            relief="flat",
            font=self.font_button,
            pady=15,
        ).grid(row=1, column=1, sticky="ew", padx=(8, 20), pady=(0, 22))

    @staticmethod
    def run_power_action(action: str) -> None:
        command = "reboot" if action == "restart" else "poweroff"
        subprocess.Popen(["sudo", "systemctl", command])

    def toggle_fullscreen(self, _event: tk.Event | None = None) -> None:
        current = bool(self.attributes("-fullscreen"))
        self.attributes("-fullscreen", not current)


def main() -> None:
    app = TouchControlApp()
    app.mainloop()


if __name__ == "__main__":
    main()
