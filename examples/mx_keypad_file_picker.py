#!/usr/bin/env python3
"""
mx_keypad_file_picker.py - Open a file prompt to select an image and display
it on the MX Creative Console LCD screen.

The script shows a file picker dialog using tkinter (part of Python's standard
library). The selected image is resized and shown either on a specific key
(118×118) or full-screen (434×434). Press grid buttons (0–8) to change which
key shows the image, or press P1/P2 to toggle between key and full-screen mode.

Usage:
    sudo python3 mx_keypad_file_picker.py
"""

import io
import signal
import sys
import time
from pathlib import Path

from logilinux import Keypad, MXKeypadButton, get_version


# ---------------------------------------------------------------------------
# File picker helper — uses tkinter, part of Python's stdlib
# ---------------------------------------------------------------------------
def pick_image_file() -> str | None:
    """Open a file-open dialog using easygui and return the selected file path, or
    ``None`` if the user cancelled."""
    try:
        import easygui
    except ImportError:
        print("easygui is not available. Install it with: pip install easygui", file=sys.stderr)
        return None

    file_path = easygui.fileopenbox(
        title="Select an image for the MX Keypad",
        filetypes=["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.gif", "*.tiff", "*.webp"],
    )
    return file_path if file_path else None


# ---------------------------------------------------------------------------
# Image loading & JPEG conversion
# ---------------------------------------------------------------------------
def load_and_resize_image(
    file_path: str,
    target_width: int,
    target_height: int,
    quality: int = 85,
) -> bytes | None:
    """Load an image from *file_path*, resize it to *target_width* ×
    *target_height* (cropping to fit if necessary), and return JPEG bytes.

    Returns ``None`` on failure.
    """
    try:
        from PIL import Image
    except ImportError:
        print(
            "Pillow is required. Install it with: pip install Pillow",
            file=sys.stderr,
        )
        return None

    try:
        img = Image.open(file_path).convert("RGB")
    except Exception as exc:
        print(f"Failed to open image: {exc}", file=sys.stderr)
        return None

    # --- Crop to the target aspect ratio, then resize ---
    target_aspect = target_width / target_height
    src_width, src_height = img.size
    src_aspect = src_width / src_height

    if src_aspect > target_aspect:
        # Image is wider — crop left/right
        new_width = int(src_height * target_aspect)
        offset = (src_width - new_width) // 2
        img = img.crop((offset, 0, offset + new_width, src_height))
    elif src_aspect < target_aspect:
        # Image is taller — crop top/bottom
        new_height = int(src_width / target_aspect)
        offset = (src_height - new_height) // 2
        img = img.crop((0, offset, src_width, offset + new_height))

    img = img.resize((target_width, target_height), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------
running = True


def _signal_handler(signum, frame):
    global running
    print("\nShutting down...")
    running = False


def main():
    global running

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    print(f"LogiLinux MX Keypad File Picker v{get_version()}")
    print("-" * 50)

    # --- Pick image ---
    file_path = pick_image_file()
    if file_path is None:
        print("No file selected. Exiting.")
        return 0

    print(f"Selected: {file_path}")

    # --- Connect to device ---
    print("Connecting to MX Keypad...")
    try:
        keypad = Keypad()
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    info = keypad.info
    print(f"Found: {info.name} ({info.device_path})")

    if not keypad.has_lcd():
        print("Device does not have an LCD. Cannot display image.", file=sys.stderr)
        return 1

    print("Initializing LCD...")
    if not keypad.initialize():
        print("Failed to initialize LCD!", file=sys.stderr)
        return 1

    print("LCD ready!\n")

    # --- Pre-render images at both sizes ---
    print("Rendering images...", end=" ", flush=True)
    key_jpeg = load_and_resize_image(file_path, keypad.KEY_SIZE, keypad.KEY_SIZE)
    screen_jpeg = load_and_resize_image(
        file_path, keypad.SCREEN_WIDTH, keypad.SCREEN_HEIGHT
    )
    if key_jpeg is None or screen_jpeg is None:
        return 1
    print("done.\n")

    # Start with the image on key 0, full-screen mode off
    current_key = 0
    full_screen = False
    keypad.set_key_image(current_key, key_jpeg)

    # --- Print instructions ---
    print("=== Controls ===")
    print("  Grid buttons 0–8 : Show image on that key")
    print("  P1 (Left)        : Toggle full-screen display")
    print("  P2 (Right)       : Clear all keys")
    print("  Ctrl+C           : Exit")
    print()

    # --- Button callback ---
    def on_button(button, pressed):
        nonlocal current_key, full_screen

        if not pressed:
            return

        if button == MXKeypadButton.P1_LEFT:
            full_screen = not full_screen
            if full_screen:
                print("→ Full-screen mode ON")
                keypad.set_screen_image(screen_jpeg)
            else:
                print("→ Full-screen mode OFF — restoring key image")
                keypad.stop_screen_animation()
                # Re-show the image on the currently selected key
                keypad.set_key_image(current_key, key_jpeg)
            return

        if button == MXKeypadButton.P2_RIGHT:
            print("→ Clearing all keys")
            for i in range(9):
                keypad.set_key_image(i, key_jpeg if i == current_key else b"")
            return

        # Grid buttons 0–8
        key_index = button.value
        if 0 <= key_index <= 8:
            current_key = key_index
            if full_screen:
                print(f"Key {key_index} pressed (ignored — full-screen mode active)")
            else:
                print(f"Key {key_index} pressed — showing image")
                keypad.set_key_image(key_index, key_jpeg)

    keypad.on_button(on_button)

    # --- Start monitoring ---
    keypad.start()

    # Display the selected path on screen
    print(f"Displaying: {Path(file_path).name}")
    print(f"  Key size : {keypad.KEY_SIZE}×{keypad.KEY_SIZE}")
    print(f"  Screen   : {keypad.SCREEN_WIDTH}×{keypad.SCREEN_HEIGHT}")
    print("Waiting for input (Ctrl+C to quit)...\n")

    try:
        while running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        keypad.stop_all_animations()
        keypad.stop()
        print("Goodbye!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
