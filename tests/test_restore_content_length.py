"""Chunked-proxied requests (no Content-Length) must keep their DRF data.

Pinned because Cloudflare forwards request bodies to the origin with
`Transfer-Encoding: chunked`, i.e. without a Content-Length header. Django's
ASGI stack buffers such bodies correctly, but DRF's `Request._load_stream`
treats a missing Content-Length as "no body" and parses every such request
as empty — every POST through the proxy silently loses its payload while
direct requests keep working. RestoreContentLengthMiddleware closes that gap;
these specs pin both the failure mode and the repair at the ASGI seam.
"""
import io
from unittest import mock

from django.core.handlers.asgi import ASGIRequest
from rest_framework.parsers import FormParser, JSONParser
from rest_framework.request import Request

from plio.middleware import RestoreContentLengthMiddleware

FORM_BODY = b"mobile=1234567890"


def asgi_post_without_content_length(body=FORM_BODY):
    """An ASGI request as daphne delivers it for a chunked POST: full body
    buffered, no content-length header in the scope."""
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/otp/request/",
        "query_string": b"",
        "headers": [(b"content-type", b"application/x-www-form-urlencoded")],
    }
    return ASGIRequest(scope, io.BytesIO(body))


def drf_data(django_request):
    return Request(
        django_request, parsers=[FormParser(), JSONParser()]
    ).data


def test_drf_drops_chunked_body_without_middleware():
    # The failure mode being fixed: body is buffered and readable, yet DRF
    # parses it as empty because the header is missing.
    request = asgi_post_without_content_length()
    assert request.body == FORM_BODY
    assert drf_data(request) == {}


def test_middleware_restores_content_length_for_chunked_body():
    request = asgi_post_without_content_length()
    middleware = RestoreContentLengthMiddleware(lambda req: req)
    middleware(request)
    assert request.META["CONTENT_LENGTH"] == str(len(FORM_BODY))
    assert drf_data(request).dict() == {"mobile": "1234567890"}


def test_middleware_leaves_declared_content_length_untouched():
    request = asgi_post_without_content_length()
    request.META["CONTENT_LENGTH"] = "7"
    middleware = RestoreContentLengthMiddleware(lambda req: req)
    with mock.patch.object(
        type(request), "body", new_callable=mock.PropertyMock
    ) as body_read:
        middleware(request)
    body_read.assert_not_called()
    assert request.META["CONTENT_LENGTH"] == "7"


def test_middleware_ignores_bodyless_requests():
    request = asgi_post_without_content_length(body=b"")
    middleware = RestoreContentLengthMiddleware(lambda req: req)
    middleware(request)
    assert "CONTENT_LENGTH" not in request.META


def test_middleware_survives_consumed_stream():
    # SafeBodyLoggingMiddleware's contract: a stream consumed upstream
    # (oversized upload already rejected) must not turn into a 500 here.
    request = asgi_post_without_content_length()
    request._read_started = True  # simulates a consumed stream
    middleware = RestoreContentLengthMiddleware(lambda req: req)
    middleware(request)
    assert "CONTENT_LENGTH" not in request.META
