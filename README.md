# LogiLinux - Python

Python bindings for the logilinux driver / Logitech Creator devices (MX Creative Console, MX Dialpad) on Linux.

## Requirements

- Linux with `/dev/input/event*` and `/dev/hidraw*` access
- Python 3.8+
- `libjpeg-dev` and `giflib-dev` (optional, for GIF/animation support)

## Installation (PyPI package WIP)

```sh
pip install logilinux
```

### From source

```sh
git clone https://github.com/your-username/logilinux.git
cd logilinux
pip install .
```

## Usage

### MX Creative Console (Keypad)

```python
from logilinux import Keypad
from PIL import Image
import io

# Connect to device
keypad = Keypad()
keypad.initialize()

# Generate a JPEG in memory
img = Image.new("RGB", (118, 118), (255, 0, 0))
buf = io.BytesIO()
img.save(buf, format="JPEG", quality=85)

# Display on key 0
keypad.set_key_image(0, buf.getvalue())

# Handle button presses
keypad.on_button(lambda button, pressed: print(button, pressed))

# Start event loop
keypad.start()
input("Press Enter to exit\n")
keypad.stop()
```

### MX Dialpad

```python
from logilinux import Dialpad

dialpad = Dialpad()

dialpad.on_rotate(lambda delta, high_res, rot_type: print(f"Rotated {delta}"))
dialpad.on_button(lambda button, pressed: print(f"{button.name} {'pressed' if pressed else 'released'}"))
dialpad.start()
input("Press Enter to exit\n")
dialpad.stop()
```

### Device discovery

```python
from logilinux import discover_devices, DeviceType

for dev in discover_devices():
    info = dev.get_info()
    print(f"{info.name} ({info.device_path})")
```

## API

### High-level classes

| Class | Device | Events |
|-------|--------|--------|
| `Dialpad` | MX Dialpad | Rotation, buttons |
| `Keypad`  | MX Creative Console | Buttons, LCD display |

### Keypad LCD methods

- `initialize()` — prepare the LCD screen
- `set_key_image(key_index, jpeg_bytes)` — display JPEG on a key (118×118)
- `set_key_gif(key_index, gif_bytes)` — play a GIF on a key
- `set_screen_image(jpeg_bytes)` — full-screen JPEG (434×434)
- `set_screen_gif(gif_bytes)` — full-screen GIF animation
- `stop_all_animations()` — stop all running animations

### Constants (on `Keypad` instance)

- `SCREEN_WIDTH` = 434
- `SCREEN_HEIGHT` = 434
- `KEY_SIZE` = 118
- `GAP_SIZE` = 40

### Enums

- `DeviceType.DIALPAD`, `DeviceType.MX_KEYPAD`
- `RotationType.DIAL`, `RotationType.DIAL_BREATH`, `RotationType.KEY_ROTATION`
- `EventType.ROTATION`, `EventType.BUTTON`
- `DialpadButton` — named buttons for MX Dialpad
- `MXKeypadButton` — named buttons for MX Creative Console (grid 0–8, P1_LEFT, P2_RIGHT)

## Permissions

Accessing HID devices typically requires root or udev rules. To run without `sudo`, create a udev rule:

```udev
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="046d", MODE="0666"
SUBSYSTEM=="input", ATTRS{idVendor}=="046d", MODE="0666"
```

## License

GPLv3
