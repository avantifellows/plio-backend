from django.core.exceptions import RequestDataTooBig
from django.http.request import RawPostDataException
from request_logging.middleware import LoggingMiddleware


class SafeBodyLoggingMiddleware(LoggingMiddleware):
    """
    django-request-logging reads `request.body` unconditionally on request
    entry. Since Django 4.0, an upload exceeding DATA_UPLOAD_MAX_MEMORY_SIZE
    reaches middleware with its stream already consumed, so that read raises
    RawPostDataException and turns the intended 400 into a 500. Guard the
    read; logging proceeds with a placeholder body.
    """

    def __call__(self, request):
        try:
            cached_request_body = request.body
        except (RawPostDataException, RequestDataTooBig):
            cached_request_body = b"<request body unavailable>"
        response = self.get_response(request)
        self.process_request(request, response, cached_request_body)
        self.process_response(request, response)
        return response
