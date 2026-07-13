import os
import tempfile

os.environ.pop("SMS_DRIVER", None)

from plio.settings import *  # noqa: E402,F401,F403


worker = os.environ.get("PYTEST_XDIST_WORKER", "master")
redis_db = 0 if worker == "master" else int(worker.replace("gw", "")) + 1
redis_url = "redis://{}:{}/{}".format(
    REDIS_HOSTNAME,  # noqa: F405
    REDIS_PORT,  # noqa: F405
    redis_db,
)

CACHES["default"]["LOCATION"] = redis_url  # noqa: F405
CHANNEL_LAYERS["default"]["CONFIG"]["hosts"] = [redis_url]  # noqa: F405
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
MEDIA_ROOT = os.path.join(tempfile.gettempdir(), "plio-tests-{}".format(worker))
SMS_DRIVER = None
