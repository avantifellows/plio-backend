"""Regression coverage for the production ASGI static-file boundary."""

import importlib

from asgiref.sync import async_to_sync
from asgiref.testing import ApplicationCommunicator
from django.core.management import call_command
from django.test import override_settings


async def _request(application, path, method="GET"):
    communicator = ApplicationCommunicator(
        application,
        {
            "type": "http",
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "root_path": "",
            "headers": [(b"host", b"testserver")],
            "client": ("127.0.0.1", 54321),
            "server": ("testserver", 80),
        },
    )
    await communicator.send_input(
        {"type": "http.request", "body": b"", "more_body": False}
    )

    response_start = await communicator.receive_output(timeout=5)
    response_body = bytearray()
    while True:
        event = await communicator.receive_output(timeout=5)
        if event["type"] != "http.response.body":
            continue
        response_body.extend(event.get("body", b""))
        if not event.get("more_body", False):
            break
    await communicator.wait()

    return (
        response_start["status"],
        {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in response_start["headers"]
        },
        bytes(response_body),
    )


def test_asgi_application_serves_collected_static_and_falls_through(db, tmp_path):
    """Exercise the deployed ProtocolTypeRouter, not Django's test client."""
    source_root = tmp_path / "source"
    source_root.mkdir()
    assets = {
        "fixture.js": b"window.__static_fixture__ = true;\n",
        "fixture.css": b"body { color: rgb(1, 2, 3); }\n",
    }
    for filename, contents in assets.items():
        (source_root / filename).write_bytes(contents)

    static_root = tmp_path / "collected"
    asgi_module = importlib.import_module("plio.asgi")
    original_application = asgi_module.application
    original_django_asgi_app = asgi_module.django_asgi_app
    original_static_http_app = asgi_module.static_http_app

    with override_settings(
        DEBUG=False,
        ALLOWED_HOSTS=["testserver"],
        STATIC_ROOT=str(static_root),
        STATIC_URL="/static/",
        STATICFILES_DIRS=[str(source_root)],
    ):
        call_command("collectstatic", interactive=False, verbosity=0)
        assert all((static_root / filename).is_file() for filename in assets)

        try:
            # Re-import after collection so ServeStatic indexes this test's
            # collected tree while DEBUG remains disabled.
            asgi_module = importlib.reload(asgi_module)
            application = asgi_module.application

            for filename, contents in assets.items():
                status, headers, body = async_to_sync(_request)(
                    application, "/static/{}".format(filename)
                )
                expected_type = (
                    "text/javascript" if filename.endswith(".js") else "text/css"
                )
                assert status == 200
                assert body == contents
                assert headers["content-type"].startswith(
                    "{}; charset=".format(expected_type)
                )
                assert headers["content-type"].endswith('"utf-8"')
                assert headers["x-content-type-options"] == "nosniff"
                assert headers["cache-control"] == "max-age=60, public"
                assert headers["content-length"] == str(len(contents))
                assert headers["etag"]
                assert headers["last-modified"]

                head_status, head_headers, head_body = async_to_sync(_request)(
                    application, "/static/{}".format(filename), method="HEAD"
                )
                assert head_status == 200
                assert head_body == b""
                assert head_headers["content-length"] == str(len(contents))
                assert head_headers["etag"] == headers["etag"]

            missing_status, _, _ = async_to_sync(_request)(
                application, "/static/does-not-exist.css"
            )
            assert missing_status == 404

            traversal_status, _, traversal_body = async_to_sync(_request)(
                application, "/static/%2e%2e/manage.py"
            )
            assert traversal_status == 404
            assert b"#!/usr/bin/env" not in traversal_body

            repository_status, _, _ = async_to_sync(_request)(application, "/manage.py")
            assert repository_status == 404

            # This request must reach Django's unchanged HTTP application.
            api_status, api_headers, api_body = async_to_sync(_request)(
                application, "/api/v1/plios/"
            )
            assert api_status == 401
            assert api_headers["content-type"].startswith("application/json")
            assert api_body
        finally:
            # Do not leave the module-level application pointed at the
            # temporary test root for later ASGI/WebSocket tests.
            asgi_module.application = original_application
            asgi_module.django_asgi_app = original_django_asgi_app
            asgi_module.static_http_app = original_static_http_app
