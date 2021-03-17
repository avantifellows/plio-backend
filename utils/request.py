from rest_framework.request import Request
from device_detector import SoftwareDetector, DeviceDetector


def get_user_agent_info(request: Request):
    """Get User-Agent information: browser, OS, device"""
    browser_info = request.META["HTTP_USER_AGENT"]

    software_info = SoftwareDetector(browser_info).parse()
    device_info = DeviceDetector(browser_info).parse()

    if "JioPages" in browser_info:
        browser_name = "JioPages"
    else:
        browser_name = software_info.client_name()

    user_agent_info = {
        "os": {"family": device_info.os_name(), "version": device_info.os_version()},
        "device": {
            "family": device_info.device_brand_name(),
            "version": device_info.device_model(),
            "type": device_info.device_type(),
        },
        "browser": {"family": browser_name, "version": software_info.client_version()},
    }

    return user_agent_info
