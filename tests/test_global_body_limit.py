"""The global request-body cap must reject oversized bodies on any endpoint.

Pinned because SafeBodyLoggingMiddleware guards the request.body read: it may
only swallow RawPostDataException (stream already consumed), never
RequestDataTooBig -- swallowing the latter would let oversized JSON and
multi-file multipart bodies bypass DATA_UPLOAD_MAX_MEMORY_SIZE entirely.
"""
import pytest
from django.conf import settings


@pytest.mark.django_db
def test_oversized_json_body_is_rejected_globally(client):
    payload = '{"pad": "' + "x" * settings.DATA_UPLOAD_MAX_MEMORY_SIZE + '"}'
    response = client.post(
        "/api/v1/plios/", data=payload, content_type="application/json"
    )
    assert response.status_code == 400
