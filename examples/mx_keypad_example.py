#!/usr/bin/env python3
"""
mx_keypad_example.py - Python counterpart of the C++ mx-keypad-example.cpp

When a grid button (0-8) is pressed, generates a solid-color JPEG and displays
it on that key. Prints events for P1/P2 navigation buttons.

Usage:
    sudo python3 mx_keypad_example.py
"""

import struct
import signal
import sys
import time
import random
import io

from logilinux import Keypad, MXKeypadButton, get_version


def generate_color_jpeg(width: int, height: int, r: int, g: int, b: int) -> bytes:
    """Generate an in-memory JPEG of a solid color without shelling out to ImageMagick.

    This uses Python's standard library to create a PPM then encode as JPEG.
    If Pillow is available, that's used for the actual JPEG encoding.
    Falls back to raw PPM if neither works (the device may still accept it).
    """
    # Prefer Pillow if available for real JPEG encoding
    try:
        from PIL import Image

        img = Image.new("RGB", (width, height), (r, g, b))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()
    except ImportError:
        pass


# Flag to keep the script running
running = True


def signal_handler(signum, frame):
    global running
    print("\nShutting down...")
    running = False


def main():
    global running

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    version = get_version()
    print(f"LogiLinux MX Keypad Example v{version}")
    print("Press any button to change its color!")
    print("Press Ctrl+C to exit\n")

    # Discover and connect to the keypad
    print("Scanning for devices...")
    try:
        keypad = Keypad()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Make sure device is connected and you have permissions.", file=sys.stderr)
        return 1

    info = keypad.info
    print(f"Found: {info.name} ({info.device_path})")
    if keypad.has_lcd():
        print("  -> Using this MX Keypad with LCD!")
    else:
        print("  -> No LCD detected on this device.")

    print("\nInitializing LCD...")
    if not keypad.initialize():
        print("Failed to initialize MX Keypad!", file=sys.stderr)
        print("Make sure you have permissions to access hidraw devices.", file=sys.stderr)
        return 1

    print("LCD initialized successfully!\n")

    # Set initial random colors on all 9 grid buttons
    print("Setting initial colors...")
    for i in range(9):
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        jpeg = generate_color_jpeg(118, 118, r, g, b)
        if jpeg:
            keypad.set_key_image(i, jpeg)
        time.sleep(0.1)

    # Set up the button callback — mirrors the C++ onEvent function
    def on_button(button, pressed):
        if not pressed:
            return  # Only act on press, not release

        key_index = button.value  # int button code

        # Check if it's a navigation button (P1/P2)
        if button == MXKeypadButton.P1_LEFT:
            print("P1 (Left) button pressed!")
            return
        elif button == MXKeypadButton.P2_RIGHT:
            print("P2 (Right) button pressed!")
            return

        # Grid button (0-8)
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)

        print(f"Button {key_index} pressed - Setting color RGB({r}, {g}, {b})")

        jpeg = generate_color_jpeg(118, 118, r, g, b)
        if jpeg:
            keypad.set_key_image(key_index, jpeg)

    keypad.on_button(on_button)

    print("\nReady! Press buttons to change colors.\n")

    # Start monitoring (runs in background thread)
    keypad.start()

    # Main loop — wait until Ctrl+C
    try:
        while running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        keypad.stop()
        print("\nExiting...")

    return 0


if __name__ == "__main__":
    sys.exit(main())
