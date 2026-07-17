from django.http.request import RawPostDataException
from request_logging.middleware import LoggingMiddleware


class RestoreContentLengthMiddleware:
    """
    Proxies that re-frame requests with `Transfer-Encoding: chunked` strip
    the Content-Length header (Cloudflare does this in front of staging and
    production). Django's ASGI stack still buffers the full body, but DRF's
    `Request._load_stream` treats a missing Content-Length as "no body" and
    silently parses every such request as empty — breaking every POST that
    arrives through the proxy while direct requests keep working. Restore
    the header from the buffered body so DRF sees the data.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.META.get("CONTENT_LENGTH"):
            try:
                body_length = len(request.body)
            except RawPostDataException:
                # Stream already consumed (e.g. an oversized upload rejected
                # upstream) — nothing to restore, and RequestDataTooBig
                # handling must keep working as before.
                body_length = 0
            if body_length:
                request.META["CONTENT_LENGTH"] = str(body_length)
        return self.get_response(request)


class SafeBodyLoggingMiddleware(LoggingMiddleware):
    """
    django-request-logging reads `request.body` unconditionally on request
    entry. Since Django 4.0, an upload exceeding DATA_UPLOAD_MAX_MEMORY_SIZE
    can reach middleware with its stream already consumed, so that read
    raises RawPostDataException and turns the intended 400 into a 500.
    Guard ONLY that case; RequestDataTooBig must keep propagating so
    Django's global body-size rejection (SuspiciousOperation -> 400) still
    protects every endpoint, not just image uploads.
    """

    def __call__(self, request):
        try:
            cached_request_body = request.body
        except RawPostDataException:
            cached_request_body = b"<request body unavailable>"
        response = self.get_response(request)
        self.process_request(request, response, cached_request_body)
        self.process_response(request, response)
        return response
