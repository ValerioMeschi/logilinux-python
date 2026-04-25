#!/usr/bin/env bash
# build_python.sh - Build and install LogiLinux Python bindings
#
# Usage:
#   ./build_python.sh                   # install into .venv and test
#   ./build_python.sh --system          # install system-wide (with --break-system-packages)
#   ./build_python.sh --clean           # remove old build artifacts first
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# ── Parse flags ──────────────────────────────────────────────────────────────
SYSTEM_INSTALL=false
CLEAN=false
for arg in "$@"; do
    case "$arg" in
        --system) SYSTEM_INSTALL=true ;;
        --clean)  CLEAN=true ;;
    esac
done

# ── Clean ────────────────────────────────────────────────────────────────────
if $CLEAN; then
    echo "Cleaning old build artifacts..."
    rm -rf build/ dist/ *.egg-info __pycache__/
    find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name '*.pyc' -delete
    echo "Done."
fi

# ── Python / venv ────────────────────────────────────────────────────────────
if $SYSTEM_INSTALL; then
    echo "Installing system-wide..."
    pip3 install --break-system-packages . 2>&1 || pip3 install . 2>&1
    echo ""
    echo "✓ Installed. Quick test:"
    python3 -c "from logilinux import *; print(get_version())"
    exit 0
fi

# Create / use a venv so we don't pollute the system Python
VENV_DIR="${SCRIPT_DIR}/.venv"
if [ ! -d "${VENV_DIR}" ]; then
    echo "Creating Python venv in ${VENV_DIR}..."
    python3 -m venv "${VENV_DIR}"
fi
source "${VENV_DIR}/bin/activate"

# Ensure pybind11 is installed in the venv
if ! python3 -c "import pybind11" 2>/dev/null; then
    echo "Installing pybind11 in venv..."
    pip3 install pybind11
fi

echo "Using: $(python3 --version) at $(which python3)"

# ── Install the package in editable mode ────────────────────────────────────
echo ""
echo "=== Installing logilinux Python package ==="
pip3 install -e .

# ── Verify ───────────────────────────────────────────────────────────────────
echo ""
echo "=== Verification ==="
python3 -c "
from logilinux import *
print('       version:', get_version())
print('   DeviceTypes:', DeviceType.DIALPAD, DeviceType.MX_KEYPAD)
print('DialpadButton:', DialpadButton.TOP_LEFT, DialpadButton.BOTTOM_RIGHT)
print('MXKeypadButton:', MXKeypadButton.GRID_0, MXKeypadButton.P1_LEFT)
print()
print('✓ logilinux installed and importable')
"

echo ""
echo "=== Done ==="
echo ""
echo "To activate the venv and run the keypad example:"
echo "  source ${VENV_DIR}/bin/activate"
echo "  sudo env \"PATH=\$PATH\" python -m logilinux.mx_keypad_example"
echo ""
echo "To run a quick script (editable install so changes apply immediately):"
echo "  source ${VENV_DIR}/bin/activate"
echo "  python -c \"from logilinux import *; print('OK')\""
