# python/__init__.py - High-level Pythonic wrapper for LogiLinux
"""
LogiLinux - Python bindings for Logitech Creator devices on Linux.

Provides a clean, Pythonic API for discovering and interacting with
Logitech MX Dialpad and MX Creative Console (Keypad) devices.

Basic usage::

    from logilinux import Dialpad, Keypad

    # Dialpad
    dialpad = Dialpad()
    def on_rotate(delta, high_res, rot_type):
        print(f"Rotated {delta} steps")
    def on_button(button, pressed):
        print(f"Button {button.name} {'pressed' if pressed else 'released'}")
    dialpad.on_rotate(on_rotate)
    dialpad.on_button(on_button)
    dialpad.start()

    # Keypad
    keypad = Keypad()
    keypad.initialize()
    keypad.set_key_image(0, jpeg_bytes)
"""

from ._logilinux import (
    Library as _Library,
    DeviceType as _DeviceType,
    DeviceCapability as _DeviceCapability,
    EventType as _EventType,
    RotationType as _RotationType,
    RotationEvent as _RotationEvent,
    ButtonEvent as _ButtonEvent,
    DialpadButton as _DialpadButton,
    MXKeypadButton as _MXKeypadButton,
    MXKeypadDevice as _MXKeypadDevice,
    Device as _Device,
    __version__,
    Version as _Version,
)

__all__ = [
    "Dialpad",
    "Keypad",
    "discover_devices",
    "get_version",
    "DeviceType",
    "DeviceCapability",
    "RotationType",
    "EventType",
    "DialpadButton",
    "MXKeypadButton",
    "MXKeypadDevice",
    "Version",
    "__version__",
]

# Re-export enums at the package level for convenience
DeviceType = _DeviceType
DeviceCapability = _DeviceCapability
RotationType = _RotationType
EventType = _EventType
DialpadButton = _DialpadButton
MXKeypadButton = _MXKeypadButton
MXKeypadDevice = _MXKeypadDevice
Version = _Version


def get_version():
    """Return the version of the underlying LogiLinux C library as a string."""
    v = _Library.get_version()
    return v.string


def discover_devices():
    """Discover all connected Logitech devices.

    Returns:
        list[Device]: List of Device objects (DialpadDevice or MXKeypadDevice).
    """
    lib = _Library()
    return lib.discover_devices()


class _ManagedLibrary:
    """Internal helper that manages a Library instance and device discovery."""

    def __init__(self):
        self._lib = _Library()
        self._device = None

    def _find_device_lcd(self, device_cls: _DeviceType):
        """Find a device, preferring keypads with LCD capability."""
        devices = self._lib.discover_devices()
        candidate = None
        for d in devices:
            if d.get_type() == device_cls:
                candidate = d
                # If it's a keypad, check if it has LCD (hidraw path)
                if isinstance(d, _MXKeypadDevice):
                    if d.has_lcd():
                        return d
        return candidate


class Dialpad:
    """High-level wrapper for the Logitech MX Dialpad.

    Usage::

        dialpad = Dialpad()
        dialpad.on_rotate(lambda delta, high_res, rot_type: print(delta))
        dialpad.on_button(lambda button, pressed: print(button, pressed))
        dialpad.start()
        # ...
        dialpad.stop()
    """

    def __init__(self):
        self._lib = _Library()
        self._device = self._lib.find_device(_DeviceType.DIALPAD)
        if not self._device:
            raise RuntimeError(
                "No MX Dialpad found. Make sure the device is connected "
                "and you have read permissions on /dev/input/event*."
            )
        self._rotation_cb = None
        self._button_cb = None
        self._any_cb = None
        self._device.set_event_callback(self._on_event)

    # --- Callback setters ---

    def on_rotate(self, callback):
        """Register a callback for rotation events.

        The callback receives ``(delta, delta_high_res, rotation_type)``.
        """
        self._rotation_cb = callback

    def on_button(self, callback):
        """Register a callback for button events.

        The callback receives ``(button, pressed)`` where *button* is a
        :class:`DialpadButton` enum member.
        """
        self._button_cb = callback

    def on_event(self, callback):
        """Register a callback for *all* raw events.

        The callback receives the native :class:`Event` object.
        """
        self._any_cb = callback

    # --- Lifecycle ---

    def start(self):
        """Start monitoring the device for events. Non-blocking (runs in a background thread)."""
        self._device.start_monitoring()

    def stop(self):
        """Stop monitoring the device."""
        self._device.stop_monitoring()

    @property
    def is_monitoring(self) -> bool:
        """Whether the device is currently being monitored."""
        return self._device.is_monitoring()

    def grab(self, exclusive: bool = True):
        """Grab or release the device exclusively (prevents other apps from receiving events).

        May require root or appropriate permissions.
        """
        self._device.grab_exclusive(exclusive)

    @property
    def info(self):
        """DeviceInfo for this device."""
        return self._device.get_info()

    # --- Internal ---

    def _on_event(self, event):
        if self._any_cb:
            self._any_cb(event)
        if isinstance(event, _RotationEvent) and self._rotation_cb:
            self._rotation_cb(
                event.delta, event.delta_high_res, event.rotation_type
            )
        elif isinstance(event, _ButtonEvent):
            if self._button_cb:
                button = _DialpadButton(event.button_code)
                self._button_cb(button, event.pressed)


class Keypad:
    """High-level wrapper for the Logitech MX Creative Console (Keypad).

    Usage::

        keypad = Keypad()
        keypad.initialize()
        keypad.on_button(lambda button, pressed: print(button, pressed))
        keypad.start()
        keypad.set_key_image(0, jpeg_bytes)
        # ...
        keypad.stop()
    """

    def __init__(self):
        self._lib = _Library()
        # find_device for MX_KEYPAD prefers hidraw devices
        self._device = self._lib.find_device(_DeviceType.MX_KEYPAD)
        if not self._device:
            raise RuntimeError(
                "No MX Keypad found. Make sure the device is connected "
                "and you have permissions for /dev/hidraw*."
            )
        # We need the actual MXKeypadDevice for LCD operations
        # find_device() should return the correct type, but cast to be safe
        self._mx = self._device  # type: _MXKeypadDevice
        self._button_cb = None
        self._any_cb = None
        self._device.set_event_callback(self._on_event)

    # --- Lifecycle ---

    def initialize(self) -> bool:
        """Initialize the LCD screen. Must be called before using display features.

        Returns True on success.
        """
        return self._mx.initialize()

    def has_lcd(self) -> bool:
        """Check if this device has a built-in LCD (hidraw path available)."""
        return self._mx.has_lcd()

    def start(self):
        """Start monitoring the device for button events. Non-blocking."""
        self._device.start_monitoring()

    def stop(self):
        """Stop monitoring the device."""
        self._device.stop_monitoring()

    @property
    def is_monitoring(self) -> bool:
        """Whether the device is currently being monitored."""
        return self._device.is_monitoring()

    @property
    def info(self):
        """DeviceInfo for this device."""
        return self._device.get_info()

    # --- Callbacks ---

    def on_button(self, callback):
        """Register a callback for button events.

        The callback receives ``(button, pressed)`` where *button* is a
        :class:`MXKeypadButton` enum member or an int for unknown codes.
        """
        self._button_cb = callback

    def on_event(self, callback):
        """Register a callback for *all* raw events.

        The callback receives the native :class:`Event` object.
        """
        self._any_cb = callback

    # --- Display ---

    def set_key_image(self, key_index: int, jpeg_data: bytes) -> bool:
        """Set a JPEG image on a single key (0-8).

        The JPEG should be 118x118 pixels (``KEY_SIZE x KEY_SIZE``).
        """
        # Convert Python bytes to std::vector<uint8_t>
        return self._mx.set_key_image(key_index, list(jpeg_data))

    def set_key_color(self, key_index: int, r: int, g: int, b: int) -> bool:
        """Set a key to a solid RGB color (note: may not be implemented in the C lib)."""
        return self._mx.set_key_color(key_index, r, g, b)

    def set_screen_image(self, jpeg_data: bytes) -> bool:
        """Set a JPEG image across the full 434x434 screen."""
        return self._mx.set_screen_image(list(jpeg_data))

    def set_raw_image(self, x: int, y: int, width: int, height: int,
                      jpeg_data: bytes) -> bool:
        """Place a JPEG image at arbitrary coordinates on the screen."""
        return self._mx.set_raw_image(x, y, width, height, list(jpeg_data))

    # --- GIFs / Animations ---

    def set_key_gif(self, key_index: int, gif_data: bytes,
                    loop: bool = True) -> bool:
        """Play a GIF animation on a single key."""
        return self._mx.set_key_gif(key_index, list(gif_data), loop)

    def set_key_gif_from_file(self, key_index: int, gif_path: str,
                               loop: bool = True) -> bool:
        """Play a GIF animation on a single key, loading from file."""
        return self._mx.set_key_gif_from_file(key_index, gif_path, loop)

    def stop_key_animation(self, key_index: int):
        """Stop animation on a specific key."""
        self._mx.stop_key_animation(key_index)

    def stop_all_animations(self):
        """Stop all key and screen animations."""
        self._mx.stop_all_animations()

    def set_screen_gif(self, gif_data: bytes, loop: bool = True) -> bool:
        """Play a full-screen GIF animation (434x434)."""
        return self._mx.set_screen_gif(list(gif_data), loop)

    def set_screen_gif_from_file(self, gif_path: str,
                                  loop: bool = True) -> bool:
        """Play a full-screen GIF animation from file (434x434)."""
        return self._mx.set_screen_gif_from_file(gif_path, loop)

    def stop_screen_animation(self):
        """Stop the full-screen animation."""
        self._mx.stop_screen_animation()

    # --- Constants ---

    @property
    def SCREEN_WIDTH(self) -> int:
        return _MXKeypadDevice.SCREEN_WIDTH

    @property
    def SCREEN_HEIGHT(self) -> int:
        return _MXKeypadDevice.SCREEN_HEIGHT

    @property
    def KEY_SIZE(self) -> int:
        return _MXKeypadDevice.KEY_SIZE

    @property
    def GAP_SIZE(self) -> int:
        return _MXKeypadDevice.GAP_SIZE

    # --- Internal ---

    def _on_event(self, event):
        if self._any_cb:
            self._any_cb(event)
        if isinstance(event, _ButtonEvent) and self._button_cb:
            button = _MXKeypadButton(event.button_code)
            self._button_cb(button, event.pressed)
