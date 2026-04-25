#!/usr/bin/env python3
"""
setup.py - Build and install the logilinux Python package.

Compiles the C++ library (liblogilinux) and Python bindings into a single
self-contained extension module, so users can simply:

    pip install .

No separate liblogilinux.so installation is needed.
"""

import os
import sys
import subprocess
from pathlib import Path
import os

from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext


# ── Platform / dependency detection ──────────────────────────────────────────

HERE = Path(__file__).parent.resolve()
LIB_SRC = HERE / "lib" / "src"
LIB_INCLUDE = HERE / "lib" / "include"
PY_SRC = HERE / "python" / "logilinux"

THREAD_LIBS = []
if sys.platform == "linux":
    THREAD_LIBS = ["pthread"]

# Detect libjpeg (optional, for GIF support in the C library)
def _find_include(name: str) -> list[str]:
    """Try to find a system include path for a library header."""
    for candidate in ["/usr/include", "/usr/local/include", "/opt/homebrew/include"]:
        p = Path(candidate) / name
        if p.exists():
            return [str(Path(candidate))]
    # Some distros put headers in subdirectories
    import subprocess as _sp
    try:
        result = _sp.run(["dpkg", "-S", name], capture_output=True, text=True, check=False)
        if result.returncode == 0 and result.stdout:
            parts = result.stdout.split(":")[0].strip()
            return []
    except FileNotFoundError:
        pass
    return []

def _find_library(name: str) -> bool:
    """Check if a shared library is available on the system."""
    import ctypes
    for libname in [f"lib{name}.so", f"lib{name}.so.6", f"lib{name}.so.5", name]:
        try:
            ctypes.CDLL(libname, use_errno=False)
            return True
        except Exception:
            pass
    return False

# Detect libjpeg (optional, for GIF support in the C library)
JPEG_AVAILABLE = _find_library("jpeg")
GIF_AVAILABLE = _find_library("gif")

JPEG_INCLUDES: list[str] = []
JPEG_LIBS: list[str] = []
if JPEG_AVAILABLE:
    JPEG_INCLUDES = _find_include("jpeglib.h")
    JPEG_LIBS = ["jpeg"]

GIF_INCLUDES: list[str] = []
GIF_LIBS: list[str] = []
if GIF_AVAILABLE:
    inc = _find_include("gif_lib.h")
    GIF_INCLUDES = inc
    GIF_LIBS = ["gif"]
    # Some distros (Arch, Fedora) have gif_lib.h without a .so symlink
    # Let's also try pkg-config
    if not inc:
        import subprocess as _sp
        try:
            result = _sp.run(["pkg-config", "--cflags", "giflib"], capture_output=True, text=True, check=False)
            if result.returncode == 0 and result.stdout:
                for part in result.stdout.split():
                    if part.startswith("-I"):
                        GIF_INCLUDES.append(part[2:])
        except FileNotFoundError:
            pass
    if not inc and not GIF_INCLUDES:
        # giflib not actually available after all
        GIF_AVAILABLE = False


# ── Collect C++ sources ────────────────────────────────────────────────────

LIB_SOURCES = [
    "lib/src/core/library.cpp",
    "lib/src/core/device_manager.cpp",
    "lib/src/core/input_monitor.cpp",
    "lib/src/devices/dialpad_device.cpp",
    "lib/src/devices/mx_keypad_device.cpp",
    "lib/src/util/gif_decoder.cpp",
]

BINDING_SOURCE = "python/logilinux/_logilinux_py.cpp"

EXTRA_OBJECTS = []
EXTRA_INCLUDES = [
    str(LIB_INCLUDE),
    str(LIB_SRC),       # for #include "../devices/..." style
]

EXTRA_LIBRARIES = THREAD_LIBS + JPEG_LIBS + GIF_LIBS
EXTRA_LIBRARY_DIRS = []
EXTRA_COMPILE_ARGS = ["-std=c++17", "-O2", "-fvisibility=hidden"]
EXTRA_LINK_ARGS = []

# If libjpeg and giflib both found with headers, enable GIF support
GIF_SUPPORT = JPEG_AVAILABLE and GIF_AVAILABLE and bool(GIF_INCLUDES) and bool(JPEG_INCLUDES)
if GIF_SUPPORT:
    EXTRA_COMPILE_ARGS.append("-DHAVE_GIFLIB=1")
    EXTRA_INCLUDES.extend(GIF_INCLUDES)
    EXTRA_INCLUDES.extend(JPEG_INCLUDES)
else:
    if not JPEG_AVAILABLE:
        print("WARNING: libjpeg not found - GIF support disabled")
    if not GIF_AVAILABLE:
        print("WARNING: giflib not found - GIF support disabled")
    if JPEG_AVAILABLE and GIF_AVAILABLE and (not GIF_INCLUDES or not JPEG_INCLUDES):
        print("WARNING: giflib/libjpeg headers not found - GIF support disabled")


# ── Custom build command to handle pybind11 ─────────────────────────────────

class Pybind11BuildExt(build_ext):
    """Custom build_ext that finds pybind11 and ensures proper compilation."""

    def build_extensions(self) -> None:
        try:
            import pybind11
            pybind11_include = pybind11.get_include()
        except ImportError:
            # Try to detect from the installed pybind11 package data
            pybind11_include = None
            result = subprocess.run(
                [sys.executable, "-c",
                 "import pybind11; print(pybind11.get_include())"],
                capture_output=True, text=True, check=False,
            )
            if result.returncode == 0:
                pybind11_include = result.stdout.strip()
            else:
                raise RuntimeError(
                    "pybind11 is required. Install it with: "
                    "pip install pybind11"
                )

        for ext in self.extensions:
            ext.include_dirs.append(pybind11_include)
        super().build_extensions()


# ── Define the extension ──────────────────────────────────────────────────

# Debug: verify all source paths are relative
_all_sources = LIB_SOURCES + [BINDING_SOURCE]
for _s in _all_sources:
    if os.path.isabs(_s):
        raise RuntimeError(f"Absolute path in sources: {_s}")
    _p = Path(_s)
    if not _p.exists():
        raise RuntimeError(f"Source file not found: {_p.resolve()}")

logilinux_ext = Extension(
    "logilinux._logilinux",
    sources=_all_sources,
    depends=[],   # setuptools will figure this out from sources
    include_dirs=EXTRA_INCLUDES,
    libraries=EXTRA_LIBRARIES,
    library_dirs=EXTRA_LIBRARY_DIRS,
    extra_compile_args=EXTRA_COMPILE_ARGS,
    extra_link_args=EXTRA_LINK_ARGS,
    language="c++",
)


# ── Run setup ──────────────────────────────────────────────────────────────

setup(
    ext_modules=[logilinux_ext],
    include_package_data=False,
    cmdclass={
        "build_ext": Pybind11BuildExt,
    },
)
