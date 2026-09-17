"""Render a private ECS registration file offline; never call AWS or deploy."""

import argparse
import json
from pathlib import Path
import re


ACCOUNT = "111766607077"
REGION = "ap-south-1"
FAMILY = "plio-backend-staging"
REMOVED_FIELDS = {
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_SECURITY_TOKEN",
    "AWS_PROFILE",
    "AWS_DEFAULT_PROFILE",
    "AWS_SHARED_CREDENTIALS_FILE",
    "AWS_CONFIG_FILE",
    "BOTO_CONFIG",
    "AWS_ROLE_ARN",
    "AWS_WEB_IDENTITY_TOKEN_FILE",
    "AWS_CONTAINER_CREDENTIALS_FULL_URI",
    "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
    "AWS_CONTAINER_AUTHORIZATION_TOKEN",
    "AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE",
    "DB_USER",
    "DB_PASSWORD",
    "FRONTEND_URL",
    "SMS_DRIVER",
}
# Only RegisterTaskDefinition input fields; describe-only metadata is omitted.
REGISTER_FIELDS = {
    "family",
    "taskRoleArn",
    "executionRoleArn",
    "networkMode",
    "containerDefinitions",
    "volumes",
    "placementConstraints",
    "requiresCompatibilities",
    "cpu",
    "memory",
    "pidMode",
    "ipcMode",
    "proxyConfiguration",
    "inferenceAccelerators",
    "ephemeralStorage",
    "runtimePlatform",
    "enableFaultInjection",
}


def render_task(source, secret_arn, image):
    source = source.get("taskDefinition", source)
    if source.get("family") != FAMILY:
        raise ValueError("Refusing a non-staging task definition")
    if not re.fullmatch(
        rf"arn:aws:secretsmanager:{REGION}:{ACCOUNT}:secret:plio/staging/database-[A-Za-z0-9]{{6}}",
        secret_arn,
    ):
        raise ValueError("Expected the staging database secret ARN")
    if not re.fullmatch(
        rf"{ACCOUNT}\.dkr\.ecr\.{REGION}\.amazonaws\.com/{FAMILY}@sha256:[a-f0-9]{{64}}",
        image,
    ):
        raise ValueError("Expected a staging ECR image pinned by digest")
    task = json.loads(
        json.dumps({k: v for k, v in source.items() if k in REGISTER_FIELDS})
    )
    containers = task.get("containerDefinitions", [])
    if len(containers) != 1 or containers[0].get("name") != FAMILY:
        raise ValueError("Unexpected containers; review manually")
    container = containers[0]
    if container.get("environmentFiles"):
        raise ValueError("Environment files require manual credential review")
    environment = {
        entry["name"]: entry["value"] for entry in container.get("environment", [])
    }
    protected = {
        "APP_ENV",
        "DB_NAME",
        "DB_HOST",
        "REDIS_HOSTNAME",
        "AWS_STORAGE_BUCKET_NAME",
    }
    if any(entry["name"] in protected for entry in container.get("secrets", [])):
        raise ValueError("Secret-backed target routing requires manual review")
    if (
        environment.get("APP_ENV") != "staging"
        or environment.get("DB_NAME") != "plio_staging"
    ):
        raise ValueError("Unexpected application environment or database")
    if environment.get("AWS_STORAGE_BUCKET_NAME") != "plio-staging-assets":
        raise ValueError("Unexpected upload bucket")
    if (
        environment.get("DB_HOST")
        != "plio-small-v1.ct2k2vwmh0ce.ap-south-1.rds.amazonaws.com"
    ):
        raise ValueError("Unexpected database host")
    if (
        environment.get("REDIS_HOSTNAME")
        != "redis-plio-staging.otbdjd.0001.aps1.cache.amazonaws.com"
    ):
        raise ValueError("Unexpected staging cache")
    for name in REMOVED_FIELDS:
        environment.pop(name, None)
    environment.update(
        FRONTEND_URL="https://staging-app.plio.in", SMS_DRIVER="disabled"
    )
    container["environment"] = [
        {"name": k, "value": v} for k, v in sorted(environment.items())
    ]
    container["secrets"] = [
        entry
        for entry in container.get("secrets", [])
        if entry["name"] not in REMOVED_FIELDS
    ] + [
        {"name": "DB_USER", "valueFrom": secret_arn + ":username::"},
        {"name": "DB_PASSWORD", "valueFrom": secret_arn + ":password::"},
    ]
    container["image"] = image
    task["taskRoleArn"] = f"arn:aws:iam::{ACCOUNT}:role/plio-backend-staging-app"
    task[
        "executionRoleArn"
    ] = f"arn:aws:iam::{ACCOUNT}:role/plio-backend-staging-execution"
    return task


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--db-secret-arn", required=True)
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    task = render_task(
        json.loads(args.input.read_text()), args.db_secret_arn, args.image
    )
    # Task files can still contain unrelated existing secrets. Never print them
    # or overwrite a file; create with owner-only permissions atomically.
    import os

    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as output:
        json.dump(task, output, indent=2)
        output.write("\n")


if __name__ == "__main__":
    main()
