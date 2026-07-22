"""Create a dated weather report by controlling Chrome and Excel with PyAutoGUI.

Install: python -m pip install pyautogui pillow
Run:     python daily_pyautogui_bot.py

Do not touch the mouse or keyboard while the bot runs. Move the mouse to any
screen corner to activate PyAutoGUI's emergency fail-safe.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

try:
    import pyautogui
except ImportError:
    print("Missing dependency. Run: python -m pip install pyautogui pillow")
    raise SystemExit(1)


LOCATION = "Singapore"
WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=1.3521&longitude=103.8198"
    "&current=temperature_2m&timezone=Asia%2FSingapore"
)
OUTPUT_DIRECTORY = Path(__file__).resolve().parent / "daily_report_outputs"

STARTUP_COUNTDOWN_SECONDS = 5
BROWSER_LOAD_SECONDS = 8
EXCEL_LOAD_SECONDS = 12
SAVE_DIALOG_SECONDS = 3

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.25


class Clipboard:
    """Standard-library clipboard helper kept alive for the entire run."""

    def __init__(self) -> None:
        self._root = tk.Tk()
        self._root.withdraw()

    def get(self) -> str:
        self._root.update()
        try:
            return self._root.clipboard_get()
        except tk.TclError:
            return ""

    def set(self, text: str) -> None:
        self._root.clipboard_clear()
        self._root.clipboard_append(text)
        self._root.update()

    def close(self) -> None:
        self._root.destroy()


def countdown(seconds: int) -> None:
    print("The bot is about to control your mouse and keyboard.")
    print("Move the mouse to a screen corner at any time to stop it.")
    for remaining in range(seconds, 0, -1):
        print(f"Starting in {remaining}...", flush=True)
        time.sleep(1)


def open_with_run_dialog(command: str) -> None:
    """Launch a Windows application through the Run dialog."""
    pyautogui.hotkey("win", "r")
    time.sleep(1)
    pyautogui.write(command, interval=0.01)
    pyautogui.press("enter")


def focus_window(title_fragment: str, timeout: int):
    """Wait for, activate, and maximize the requested application window."""
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        for window in reversed(pyautogui.getAllWindows()):
            if title_fragment.lower() not in window.title.lower():
                continue
            try:
                if window.isMinimized:
                    window.restore()
                window.activate()
                time.sleep(0.5)
                window.maximize()
                time.sleep(0.5)
                active = pyautogui.getActiveWindow()
                if active and title_fragment.lower() in active.title.lower():
                    return window
            except Exception as exc:
                last_error = exc
        time.sleep(0.5)
    details = f" Last window error: {last_error}" if last_error else ""
    raise RuntimeError(f"Could not focus the {title_fragment} window.{details}")


def find_chrome_executable() -> Path:
    """Find Chrome without depending on the terminal PATH setting."""
    candidates: list[Path] = []
    path_match = shutil.which("chrome") or shutil.which("chrome.exe")
    if path_match:
        candidates.append(Path(path_match))
    for environment_name in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        base = os.environ.get(environment_name)
        if base:
            candidates.append(
                Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe"
            )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise RuntimeError("Google Chrome was not found on this computer.")


def open_new_chrome_window(chrome_path: Path):
    """Launch Chrome and return only the newly created window handle."""
    before_handles = {
        getattr(window, "_hWnd", None)
        for window in pyautogui.getAllWindows()
        if "chrome" in window.title.lower()
    }
    subprocess.Popen([str(chrome_path), "--new-window", "about:blank"])
    deadline = time.time() + 15
    last_error: Exception | None = None
    while time.time() < deadline:
        for window in pyautogui.getAllWindows():
            handle = getattr(window, "_hWnd", None)
            if "chrome" not in window.title.lower() or handle in before_handles:
                continue
            try:
                if window.isMinimized:
                    window.restore()
                window.maximize()
                window.activate()
                time.sleep(1)
                active = pyautogui.getActiveWindow()
                if active and getattr(active, "_hWnd", None) == handle:
                    return window
            except Exception as exc:
                last_error = exc
        time.sleep(0.5)
    details = f" Last window error: {last_error}" if last_error else ""
    raise RuntimeError(
        "Chrome did not create a new controllable window." + details
    )


def find_excel_executable() -> Path:
    """Find the installed Microsoft Excel executable."""
    candidates: list[Path] = []
    path_match = shutil.which("excel") or shutil.which("excel.exe")
    if path_match:
        candidates.append(Path(path_match))
    for environment_name in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
        base = os.environ.get(environment_name)
        if base:
            candidates.extend(
                [
                    Path(base) / "Microsoft Office" / "root" / "Office16" / "EXCEL.EXE",
                    Path(base) / "Microsoft Office" / "Office16" / "EXCEL.EXE",
                ]
            )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise RuntimeError("Microsoft Excel was not found on this computer.")


def open_verified_blank_workbook():
    """Launch Excel and reacquire valid handles until a workbook exists."""
    before_handles = {
        getattr(window, "_hWnd", None)
        for window in pyautogui.getAllWindows()
        if "excel" in window.title.lower()
    }
    subprocess.Popen([str(find_excel_executable()), "/x"])

    def new_excel_windows():
        windows = []
        for window in pyautogui.getAllWindows():
            try:
                title = window.title.strip().lower()
            except Exception:
                continue
            handle = getattr(window, "_hWnd", None)
            if "excel" in title and handle not in before_handles:
                windows.append(window)
        return windows

    def find_workbook_window():
        for window in new_excel_windows():
            try:
                title = window.title.strip().lower()
                if re.match(r"^book\d+\s*-\s*excel", title):
                    return window
            except Exception:
                continue
        return None

    deadline = time.time() + EXCEL_LOAD_SECONDS + 10
    start_window = None
    while time.time() < deadline:
        workbook = find_workbook_window()
        if workbook is not None:
            workbook.maximize()
            workbook.activate()
            return workbook
        windows = new_excel_windows()
        if windows:
            start_window = windows[0]
            try:
                if start_window.isMinimized:
                    start_window.restore()
                start_window.maximize()
                start_window.activate()
                break
            except Exception:
                start_window = None
        time.sleep(0.5)
    if start_window is None:
        raise RuntimeError("Excel did not create a new application window.")

    time.sleep(1)
    pyautogui.hotkey("ctrl", "n")
    deadline = time.time() + 8
    while time.time() < deadline:
        workbook = find_workbook_window()
        if workbook is not None:
            workbook.maximize()
            workbook.activate()
            return workbook
        time.sleep(0.5)

    # Reacquire the Home window before clicking Blank workbook.
    windows = new_excel_windows()
    if not windows:
        raise RuntimeError("Excel Home window became unavailable.")
    start_window = windows[0]
    try:
        start_window.activate()
        start_window.maximize()
        pyautogui.click(
            start_window.left + int(start_window.width * 0.215),
            start_window.top + int(start_window.height * 0.39),
        )
    except Exception as exc:
        raise RuntimeError("Excel Home window became invalid.") from exc

    deadline = time.time() + 8
    while time.time() < deadline:
        workbook = find_workbook_window()
        if workbook is not None:
            workbook.maximize()
            workbook.activate()
            return workbook
        time.sleep(0.5)
    raise RuntimeError("Excel opened, but a blank workbook could not be created.")


def fetch_weather_from_chrome(clipboard: Clipboard) -> str:
    """Copy Open-Meteo's current Singapore temperature from visible Chrome."""
    print(f"Opening Chrome: {WEATHER_URL}")
    chrome_path = find_chrome_executable()
    chrome_window = open_new_chrome_window(chrome_path)

    pyautogui.hotkey("ctrl", "l")
    pyautogui.write(WEATHER_URL, interval=0.01)
    pyautogui.press("enter")
    time.sleep(BROWSER_LOAD_SECONDS)

    # Restore the exact window used for navigation before copying its body.
    chrome_window.activate()
    chrome_window.maximize()
    time.sleep(1)

    # A physical click makes the JSON document, rather than the address bar, active.
    pyautogui.click(
        chrome_window.left + chrome_window.width // 2,
        chrome_window.top + chrome_window.height // 2,
    )
    time.sleep(0.5)
    clipboard.set("")
    pyautogui.hotkey("ctrl", "a")
    pyautogui.hotkey("ctrl", "c")
    time.sleep(1)

    copied_text = clipboard.get().strip()
    if not copied_text:
        print(
            "Chrome clipboard was empty; reading the same visible weather URL "
            "through the standard-library fallback."
        )
        request = Request(WEATHER_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=15) as response:
            copied_text = response.read().decode("utf-8")

    try:
        payload = json.loads(copied_text)
        temperature = payload["current"]["temperature_2m"]
        unit = payload.get("current_units", {}).get("temperature_2m", "deg C")
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        match = re.search(
            r'"current"\s*:\s*\{.*?"temperature_2m"\s*:\s*(-?\d+(?:\.\d+)?)',
            copied_text,
            flags=re.DOTALL,
        )
        if not match:
            preview = copied_text[:160].replace("\n", " ") or "<clipboard empty>"
            raise RuntimeError(
                "Chrome did not copy the expected weather JSON. "
                f"Clipboard preview: {preview}"
            )
        temperature = float(match.group(1))
        unit = "deg C"

    weather = f"{LOCATION} temperature: {temperature} {unit}"
    print(f"Copied data: {weather}")
    return weather


def create_comment(weather: str) -> str:
    """Generate a short report comment from a Celsius temperature."""
    match = re.search(
        r"([+-]?\d+(?:\.\d+)?)\s*(?:\N{DEGREE SIGN}|deg\s*)?C",
        weather,
        re.IGNORECASE,
    )
    if not match:
        return "Weather update recorded"
    temperature = float(match.group(1))
    if temperature >= 32:
        return "Hot weather - stay hydrated"
    if temperature >= 25:
        return "Warm weather"
    if temperature >= 18:
        return "Comfortable weather"
    return "Cool weather - carry a jacket"


def unique_output_path(stem: str, suffix: str) -> Path:
    """Avoid overwriting an existing report while retaining today's date."""
    candidate = OUTPUT_DIRECTORY / f"{stem}{suffix}"
    if not candidate.exists():
        return candidate
    return OUTPUT_DIRECTORY / f"{stem}_{datetime.now():%H%M%S}{suffix}"


def populate_and_save_excel(
    clipboard: Clipboard,
    report_time: datetime,
    weather: str,
    comment: str,
    workbook_path: Path,
) -> None:
    """Open Excel, enter the report, format it, and save the workbook."""
    print("Opening Microsoft Excel...")
    workbook_window = open_verified_blank_workbook()

    row_time = report_time.strftime("%Y-%m-%d %H:%M:%S")
    weather_ascii = weather.replace("\N{DEGREE SIGN}", "deg ")
    workbook_window.activate()
    pyautogui.hotkey("ctrl", "home")

    # Type cells directly because clipboard paste is unreliable on this system.
    for value in ("Date & Time", "Fetched Data", "Comment"):
        pyautogui.write(value, interval=0.02)
        pyautogui.press("tab")
    pyautogui.press("home")
    pyautogui.press("down")
    for value in (row_time, weather_ascii, comment):
        safe_value = value.encode("ascii", errors="replace").decode("ascii")
        pyautogui.write(safe_value, interval=0.02)
        pyautogui.press("tab")
    time.sleep(1)

    pyautogui.hotkey("ctrl", "home")
    pyautogui.keyDown("shift")
    pyautogui.press("right", presses=2, interval=0.1)
    pyautogui.keyUp("shift")
    pyautogui.hotkey("ctrl", "b")
    pyautogui.hotkey("ctrl", "a")
    pyautogui.hotkey("alt", "h")
    pyautogui.press("o")
    pyautogui.press("i")
    time.sleep(1)
    pyautogui.hotkey("ctrl", "home")

    print(f"Saving workbook: {workbook_path}")
    pyautogui.press("f12")
    time.sleep(SAVE_DIALOG_SECONDS)
    pyautogui.hotkey("alt", "n")
    time.sleep(0.5)
    pyautogui.hotkey("ctrl", "a")
    pyautogui.write(str(workbook_path), interval=0.01)
    pyautogui.press("enter")

    deadline = time.time() + 15
    while time.time() < deadline and not workbook_path.is_file():
        time.sleep(0.5)
    if not workbook_path.is_file():
        raise RuntimeError(
            "Excel did not create the workbook file. The Save As dialog may "
            "still be open or may not have received the filename."
        )
    workbook_window.activate()
    workbook_window.maximize()
    time.sleep(1)


def main() -> int:
    if sys.platform != "win32":
        print("This bot is configured for Windows, Chrome, and Microsoft Excel.")
        return 1
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    report_time = datetime.now()
    date_text = report_time.strftime("%Y-%m-%d")
    workbook_path = unique_output_path(f"daily_report_{date_text}", ".xlsx")
    screenshot_path = unique_output_path(
        f"daily_report_{date_text}_screenshot", ".png"
    )

    clipboard = Clipboard()
    try:
        countdown(STARTUP_COUNTDOWN_SECONDS)
        weather = fetch_weather_from_chrome(clipboard)
        comment = create_comment(weather)
        populate_and_save_excel(
            clipboard, report_time, weather, comment, workbook_path
        )
        pyautogui.screenshot(str(screenshot_path))
        print(f"Saved screenshot: {screenshot_path}")
        print("Daily report automation completed successfully.")
        return 0
    except pyautogui.FailSafeException:
        print("Automation stopped by the PyAutoGUI fail-safe.")
        return 2
    except KeyboardInterrupt:
        print("Automation interrupted by the keyboard.")
        return 2
    except Exception as exc:
        print(f"Automation failed: {exc}")
        return 1
    finally:
        clipboard.close()


if __name__ == "__main__":
    raise SystemExit(main())
