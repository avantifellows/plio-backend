from django.http.request import RawPostDataException
from request_logging.middleware import LoggingMiddleware


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
