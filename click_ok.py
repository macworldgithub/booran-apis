"""
Click Okay / Close Modal Button Helper
======================================
This script dismisses the 'ERAnet Administration menu' or any popup alert dialog:
1. Locates any open eraPower / Chrome / Edge window.
2. Sends the OK / Enter confirmation to dismiss in-page modals.
3. Can be run standalone anytime:
      python click_ok.py
"""

import sys
import time
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

VK_RETURN = 0x0D
VK_ESCAPE = 0x1B
VK_SPACE  = 0x20
KEYEVENTF_KEYUP = 0x0002


def send_key(vk_code):
    user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.05)


def find_browser_windows():
    results = []

    def enum_cb(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value
                # Match eraPower, Chromium, Chrome, Edge or dialog titles
                low = title.lower()
                if any(k in low for k in ["erapower", "pentana", "eranet", "chrome", "edge", "chromium", "administration"]):
                    results.append((hwnd, title))
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    return results


def click_ok():
    windows = find_browser_windows()
    if not windows:
        print("[click_ok] No eraPower / browser windows detected.")
        return False

    print(f"[click_ok] Found {len(windows)} matching window(s):")
    for hwnd, title in windows:
        print(f"  - [{hwnd}] {title}")

    # Bring to foreground and send Enter to trigger the default [OK] button
    for hwnd, title in windows:
        try:
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.2)
            print(f"[click_ok] Sending Enter/Space to '{title}'...")
            send_key(VK_RETURN)
            time.sleep(0.1)
            send_key(VK_SPACE)
            time.sleep(0.1)
        except Exception as e:
            print(f"  Warning: {e}")

    print("[click_ok] Done! OK command sent to active dialogs.")
    return True


if __name__ == "__main__":
    click_ok()
