import os
import tempfile

os.environ.pop("SMS_DRIVER", None)

from django.core.exceptions import ImproperlyConfigured  # noqa: E402

from plio.settings import *  # noqa: E402,F401,F403


worker = os.environ.get("PYTEST_XDIST_WORKER", "master")
# Redis DB 0 belongs to the running application (docker-compose stack); tests
# must never land there or the per-test flushdb wipes the app's cache and
# channel layer. Serial runs take DB 1, xdist workers count up from 2.
redis_db = 1 if worker == "master" else int(worker.replace("gw", "")) + 2
if redis_db > 15:
    raise ImproperlyConfigured(
        "xdist worker {} maps to Redis DB {}, beyond the default 16 databases "
        "(0-15). Run with at most 14 workers (-n 14) or raise `databases` in "
        "the Redis config.".format(worker, redis_db)
    )
redis_url = "redis://{}:{}/{}".format(
    REDIS_HOSTNAME,  # noqa: F405
    REDIS_PORT,  # noqa: F405
    redis_db,
)

CACHES["default"]["LOCATION"] = redis_url  # noqa: F405
CHANNEL_LAYERS["default"]["CONFIG"]["hosts"] = [redis_url]  # noqa: F405
# Django 4.2+: STORAGES replaces DEFAULT_FILE_STORAGE (mutually exclusive)
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
MEDIA_ROOT = os.path.join(tempfile.gettempdir(), "plio-tests-{}".format(worker))
SMS_DRIVER = None
