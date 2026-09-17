import copy

import pytest

from scripts.prepare_staging_task import render_task


SECRET = (
    "arn:aws:secretsmanager:ap-south-1:111766607077:secret:plio/staging/database-ABC123"
)
IMAGE = (
    "111766607077.dkr.ecr.ap-south-1.amazonaws.com/plio-backend-staging@sha256:"
    + "a" * 64
)


@pytest.fixture
def task():
    return {
        "family": "plio-backend-staging",
        "revision": 254,
        "containerDefinitions": [
            {
                "name": "plio-backend-staging",
                "environment": [
                    {"name": k, "value": v}
                    for k, v in {
                        "APP_ENV": "staging",
                        "DB_NAME": "plio_staging",
                        "DB_HOST": "plio-small-v1.ct2k2vwmh0ce.ap-south-1.rds.amazonaws.com",
                        "REDIS_HOSTNAME": "redis-plio-staging.otbdjd.0001.aps1.cache.amazonaws.com",
                        "AWS_STORAGE_BUCKET_NAME": "plio-staging-assets",
                        "AWS_ACCESS_KEY_ID": "old-test-key",
                        "AWS_SECRET_ACCESS_KEY": "old-test-secret",
                        "DB_PASSWORD": "old-test-password",
                        "SECRET_KEY": "preserve-test-secret",
                    }.items()
                ],
                "secrets": [
                    {"name": "AWS_SESSION_TOKEN", "valueFrom": "old-test-reference"}
                ],
            }
        ],
    }


def test_render_removes_credentials_and_pins_staging_resources(task):
    original = copy.deepcopy(task)
    result = render_task(task, SECRET, IMAGE)
    container = result["containerDefinitions"][0]
    env = {e["name"]: e["value"] for e in container["environment"]}
    assert "AWS_ACCESS_KEY_ID" not in env
    assert "AWS_SECRET_ACCESS_KEY" not in env
    assert "DB_PASSWORD" not in env
    assert env["SECRET_KEY"] == "preserve-test-secret"
    assert env["SMS_DRIVER"] == "disabled"
    assert env["FRONTEND_URL"] == "https://staging-app.plio.in"
    assert container["secrets"] == [
        {"name": "DB_USER", "valueFrom": SECRET + ":username::"},
        {"name": "DB_PASSWORD", "valueFrom": SECRET + ":password::"},
    ]
    assert container["image"] == IMAGE
    assert result["taskRoleArn"].endswith(":role/plio-backend-staging-app")
    assert result["executionRoleArn"].endswith(":role/plio-backend-staging-execution")
    assert "revision" not in result
    assert task == original


@pytest.mark.parametrize(
    "field,value",
    [
        ("APP_ENV", "production"),
        ("DB_NAME", "plio_production"),
        ("AWS_STORAGE_BUCKET_NAME", "plio-prod-assets"),
        ("DB_HOST", "other-database"),
        ("REDIS_HOSTNAME", "other-cache"),
    ],
)
def test_rejects_production_configuration(task, field, value):
    for entry in task["containerDefinitions"][0]["environment"]:
        if entry["name"] == field:
            entry["value"] = value
    with pytest.raises(ValueError):
        render_task(task, SECRET, IMAGE)


def test_rejects_production_task_secret_image_and_hidden_environment(task):
    with pytest.raises(ValueError):
        render_task(dict(task, family="plio-backend-production"), SECRET, IMAGE)
    with pytest.raises(ValueError):
        render_task(task, SECRET.replace("/staging/", "/production/"), IMAGE)
    with pytest.raises(ValueError):
        render_task(
            task,
            SECRET,
            IMAGE.replace("plio-backend-staging", "plio-backend-production"),
        )
    with pytest.raises(ValueError):
        render_task(task, SECRET, IMAGE.split("@sha256:")[0] + ":latest")
    task["containerDefinitions"][0]["environmentFiles"] = [
        {"value": "test-file", "type": "s3"}
    ]
    with pytest.raises(ValueError):
        render_task(task, SECRET, IMAGE)
