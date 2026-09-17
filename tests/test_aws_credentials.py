"""Credential-chain regression: no live AWS calls or real credentials."""

import boto3
import pytest
from botocore.utils import ContainerMetadataFetcher
from django.test import override_settings
from storages.backends.s3 import S3Storage

from users.services import SnsService


@pytest.mark.parametrize("provider", ["environment", "container"])
def test_sns_and_storage_use_sdk_credentials_with_session_token(
    provider, monkeypatch, tmp_path
):
    for name in (
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_PROFILE",
        "AWS_DEFAULT_PROFILE",
        "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
        "AWS_CONTAINER_CREDENTIALS_FULL_URI",
        "AWS_ROLE_ARN",
        "AWS_WEB_IDENTITY_TOKEN_FILE",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(tmp_path / "no-credentials"))
    monkeypatch.setenv("AWS_CONFIG_FILE", str(tmp_path / "no-config"))
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")
    monkeypatch.setattr(boto3, "DEFAULT_SESSION", None)

    if provider == "environment":
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-access")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret")
        monkeypatch.setenv("AWS_SESSION_TOKEN", "test-token")
        expected_method = "env"
    else:
        monkeypatch.setenv(
            "AWS_CONTAINER_CREDENTIALS_FULL_URI", "http://127.0.0.1/credentials"
        )
        monkeypatch.setattr(
            ContainerMetadataFetcher,
            "retrieve_full_uri",
            lambda *a, **kw: {
                "AccessKeyId": "test-access",
                "SecretAccessKey": "test-secret",
                "Token": "test-token",
                "Expiration": "2099-01-01T00:00:00Z",
            },
        )
        expected_method = "container-role"

    with override_settings(
        AWS_REGION="ap-south-1",
        AWS_S3_REGION_NAME="ap-south-1",
        AWS_ACCESS_KEY_ID="",
        AWS_SECRET_ACCESS_KEY="",
        AWS_SESSION_TOKEN=None,
        AWS_STORAGE_BUCKET_NAME="test-bucket",
    ):
        clients = [SnsService().client, S3Storage().connection.meta.client]
        for client in clients:
            credentials = client._request_signer._credentials
            assert credentials.method == expected_method
            frozen = credentials.get_frozen_credentials()
            assert frozen.access_key == "test-access"
            assert frozen.token == "test-token"
