// python/logilinux_py.cpp - pybind11 bindings for LogiLinux
#include <pybind11/pybind11.h>
#include <pybind11/functional.h>
#include <pybind11/stl.h>
#include <pybind11/chrono.h>

#include <logilinux/logilinux.h>
#include <logilinux/events.h>
#include <logilinux/device.h>
#include <logilinux/mx_keypad.h>

// Include the internal header so we can bind the full MXKeypadDevice API
#include "../../lib/src/devices/mx_keypad_device.h"

namespace py = pybind11;
using namespace LogiLinux;

// Trampoline class to allow Python to override Device methods if ever needed
class PyDevice : public Device {
public:
    using Device::Device;

    const DeviceInfo &getInfo() const override {
        PYBIND11_OVERRIDE_PURE(const DeviceInfo&, Device, getInfo);
    }

    DeviceType getType() const override {
        PYBIND11_OVERRIDE_PURE(DeviceType, Device, getType);
    }

    bool hasCapability(DeviceCapability cap) const override {
        PYBIND11_OVERRIDE_PURE(bool, Device, hasCapability, cap);
    }

    void setEventCallback(EventCallback callback) override {
        PYBIND11_OVERRIDE_PURE(void, Device, setEventCallback, callback);
    }

    void startMonitoring() override {
        PYBIND11_OVERRIDE_PURE(void, Device, startMonitoring);
    }

    void stopMonitoring() override {
        PYBIND11_OVERRIDE_PURE(void, Device, stopMonitoring);
    }

    bool isMonitoring() const override {
        PYBIND11_OVERRIDE_PURE(bool, Device, isMonitoring);
    }

    bool grabExclusive(bool grab) override {
        PYBIND11_OVERRIDE_PURE(bool, Device, grabExclusive, grab);
    }
};

PYBIND11_MODULE(_logilinux, m) {
    m.doc() = "Python bindings for LogiLinux - Logitech Creator devices on Linux";

    // ============================
    // Enums
    // ============================
    py::enum_<DeviceType>(m, "DeviceType")
        .value("UNKNOWN", DeviceType::UNKNOWN)
        .value("DIALPAD", DeviceType::DIALPAD)
        .value("MX_KEYPAD", DeviceType::MX_KEYPAD);

    py::enum_<DeviceCapability>(m, "DeviceCapability")
        .value("ROTATION", DeviceCapability::ROTATION)
        .value("BUTTONS", DeviceCapability::BUTTONS)
        .value("HIGH_RES_SCROLL", DeviceCapability::HIGH_RES_SCROLL)
        .value("LCD_DISPLAY", DeviceCapability::LCD_DISPLAY)
        .value("IMAGE_UPLOAD", DeviceCapability::IMAGE_UPLOAD);

    py::enum_<RotationType>(m, "RotationType")
        .value("DIAL", RotationType::DIAL)
        .value("WHEEL", RotationType::WHEEL);

    py::enum_<EventType>(m, "EventType")
        .value("ROTATION", EventType::ROTATION)
        .value("BUTTON_PRESS", EventType::BUTTON_PRESS)
        .value("BUTTON_RELEASE", EventType::BUTTON_RELEASE)
        .value("DEVICE_CONNECTED", EventType::DEVICE_CONNECTED)
        .value("DEVICE_DISCONNECTED", EventType::DEVICE_DISCONNECTED);

    py::enum_<DialpadButton>(m, "DialpadButton")
        .value("TOP_LEFT", DialpadButton::TOP_LEFT)
        .value("TOP_RIGHT", DialpadButton::TOP_RIGHT)
        .value("BOTTOM_LEFT", DialpadButton::BOTTOM_LEFT)
        .value("BOTTOM_RIGHT", DialpadButton::BOTTOM_RIGHT)
        .value("UNKNOWN", DialpadButton::UNKNOWN);

    py::enum_<MXKeypadButton>(m, "MXKeypadButton")
        .value("GRID_0", MXKeypadButton::GRID_0)
        .value("GRID_1", MXKeypadButton::GRID_1)
        .value("GRID_2", MXKeypadButton::GRID_2)
        .value("GRID_3", MXKeypadButton::GRID_3)
        .value("GRID_4", MXKeypadButton::GRID_4)
        .value("GRID_5", MXKeypadButton::GRID_5)
        .value("GRID_6", MXKeypadButton::GRID_6)
        .value("GRID_7", MXKeypadButton::GRID_7)
        .value("GRID_8", MXKeypadButton::GRID_8)
        .value("P1_LEFT", MXKeypadButton::P1_LEFT)
        .value("P2_RIGHT", MXKeypadButton::P2_RIGHT)
        .value("UNKNOWN", MXKeypadButton::UNKNOWN);

    // ============================
    // Structs
    // ============================
    py::class_<DeviceInfo>(m, "DeviceInfo")
        .def_readonly("name", &DeviceInfo::name)
        .def_readonly("device_path", &DeviceInfo::device_path)
        .def_readonly("vendor_id", &DeviceInfo::vendor_id)
        .def_readonly("product_id", &DeviceInfo::product_id)
        .def_readonly("type", &DeviceInfo::type)
        .def("__repr__", [](const DeviceInfo &info) {
            return "<DeviceInfo '" + info.name + "' path=" + info.device_path + ">";
        });

    py::class_<Version>(m, "Version")
        .def_readonly("major", &Version::major)
        .def_readonly("minor", &Version::minor)
        .def_readonly("patch", &Version::patch)
        .def_readonly("string", &Version::string)
        .def("__repr__", [](const Version &v) {
            return "<Version " + std::string(v.string) + ">";
        });

    // ============================
    // Events
    // ============================
    py::class_<Event, EventPtr>(m, "Event")
        .def_readonly("type", &Event::type)
        .def_readonly("timestamp", &Event::timestamp);

    py::class_<RotationEvent, Event, RotationEventPtr>(m, "RotationEvent")
        .def_readonly("rotation_type", &RotationEvent::rotation_type)
        .def_readonly("delta", &RotationEvent::delta)
        .def_readonly("delta_high_res", &RotationEvent::delta_high_res)
        .def_readonly("raw_event_code", &RotationEvent::raw_event_code)
        .def("__repr__", [](const RotationEvent &e) {
            return "<RotationEvent delta=" + std::to_string(e.delta)
                 + " high_res=" + std::to_string(e.delta_high_res) + ">";
        });

    py::class_<ButtonEvent, Event, ButtonEventPtr>(m, "ButtonEvent")
        .def_readonly("button_code", &ButtonEvent::button_code)
        .def_readonly("pressed", &ButtonEvent::pressed)
        .def("__repr__", [](const ButtonEvent &e) {
            return "<ButtonEvent code=" + std::to_string(e.button_code)
                 + " pressed=" + (e.pressed ? "True" : "False") + ">";
        });

    py::class_<DeviceEvent, Event, DeviceEventPtr>(m, "DeviceEvent")
        .def_readonly("device_path", &DeviceEvent::device_path);

    // ============================
    // Device base class
    // ============================
    py::class_<Device, PyDevice, DevicePtr>(m, "Device")
        .def("get_info", &Device::getInfo, py::return_value_policy::reference)
        .def("get_type", &Device::getType)
        .def("has_capability", &Device::hasCapability)
        .def("set_event_callback", &Device::setEventCallback)
        .def("start_monitoring", &Device::startMonitoring)
        .def("stop_monitoring", &Device::stopMonitoring)
        .def("is_monitoring", &Device::isMonitoring)
        .def("grab_exclusive", &Device::grabExclusive);

    // ============================
    // MXKeypadDevice
    // ============================
    py::class_<MXKeypadDevice, Device, std::shared_ptr<MXKeypadDevice>>(m, "MXKeypadDevice")
        .def("initialize", &MXKeypadDevice::initialize)
        .def("has_lcd", &MXKeypadDevice::hasLCD)
        .def("set_key_image", &MXKeypadDevice::setKeyImage,
             "Set JPEG image on a single key (0-8)")
        .def("set_key_color", &MXKeypadDevice::setKeyColor,
             "Set a key to a solid RGB color (may not be implemented)")
        .def("set_screen_image", &MXKeypadDevice::setScreenImage,
             "Set JPEG image across full 434x434 screen")
        .def("set_raw_image", &MXKeypadDevice::setRawImage,
             "Set JPEG image at arbitrary coordinates")
        .def("set_key_gif", &MXKeypadDevice::setKeyGif,
             py::arg("key_index"), py::arg("gif_data"), py::arg("loop") = true)
        .def("set_key_gif_from_file", &MXKeypadDevice::setKeyGifFromFile,
             py::arg("key_index"), py::arg("gif_path"), py::arg("loop") = true)
        .def("stop_key_animation", &MXKeypadDevice::stopKeyAnimation)
        .def("stop_all_animations", &MXKeypadDevice::stopAllAnimations)
        .def("set_screen_gif", &MXKeypadDevice::setScreenGif,
             py::arg("gif_data"), py::arg("loop") = true)
        .def("set_screen_gif_from_file", &MXKeypadDevice::setScreenGifFromFile,
             py::arg("gif_path"), py::arg("loop") = true)
        .def("stop_screen_animation", &MXKeypadDevice::stopScreenAnimation)
        .def_property_readonly_static("SCREEN_WIDTH", [](py::object) {
            return MXKeypadDevice::SCREEN_WIDTH;
        })
        .def_property_readonly_static("SCREEN_HEIGHT", [](py::object) {
            return MXKeypadDevice::SCREEN_HEIGHT;
        })
        .def_property_readonly_static("KEY_SIZE", [](py::object) {
            return MXKeypadDevice::KEY_SIZE;
        })
        .def_property_readonly_static("GAP_SIZE", [](py::object) {
            return MXKeypadDevice::GAP_SIZE;
        });

    // ============================
    // Library - main entry point
    // ============================
    py::class_<Library>(m, "Library")
        .def(py::init<>())
        .def("discover_devices", &Library::discoverDevices)
        .def("find_device", &Library::findDevice,
             py::arg("device_type"))
        .def("find_devices", &Library::findDevices,
             py::arg("device_type"))
        .def_static("get_version", &Library::getVersion);

    // ============================
    // Free helper functions
    // ============================
    m.def("get_dialpad_button", &getDialpadButton);
    m.def("get_dialpad_button_name", &getDialpadButtonName);
    m.def("get_mx_keypad_button", &getMXKeypadButton);
    m.def("get_mx_keypad_button_name", &getMXKeypadButtonName);

    // ============================
    // Version convenience
    // ============================
    m.attr("__version__") = LOGILINUX_VERSION_STRING;
}