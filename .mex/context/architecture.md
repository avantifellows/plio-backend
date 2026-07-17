---
name: architecture
description: How the major pieces of this project connect and flow. Load when working on system design, integrations, or understanding how components interact.
triggers:
  - "architecture"
  - "system design"
  - "how does X connect to Y"
  - "integration"
  - "flow"
edges:
  - target: context/stack.md
    condition: when specific technology details are needed
  - target: context/decisions.md
    condition: when understanding why the architecture is structured this way
last_updated: 2026-07-11
---

# Architecture

## System Overview

Request arrives → tenant middleware (`organizations/middleware.py`, OrganizationTenantMiddleware)
reads the `Organization` header (falling back to DEFAULT_TENANT_SHORTCODE) and switches the
Postgres connection to that workspace's schema → OAuth2 authentication resolves the Bearer
token → DRF ViewSet + serializer handle the resource → frequently-read entities
(plio/video/item/question/image/user) are served from Redis when cached, with tenant-scoped
keys from `plio/cache.py` → response serialized back. Heavier reads (plio metrics, report
downloads) run raw SQL from `plio/queries.py` against the current schema, post-processed with
pandas. Separately, Django Channels keeps a WebSocket per user (`users/consumers.py`) and
pushes the serialized user object on updates via Redis channel layers.

## Key Components

- **plio** (project package AND core app) — settings/urls/asgi live in `plio/settings.py`, `plio/urls.py`; the app also owns Video, Plio, Item, Question, Image models, their viewsets, `plio/cache.py` (Redis key map + invalidation helpers), and `plio/queries.py` (raw SQL for metrics/reports)
- **entries** — runtime learner data: Session, SessionAnswer, Event; high write volume during playback
- **users** — custom User model (email/mobile based, optional unique_id + auth_org), roles, org membership, OTP flow, external-auth token endpoint, WebSocket consumer
- **organizations** — Organization (tenant: shortcode, schema_name, api_key) + Domain models and the tenant middleware
- **experiments / tags / etl** — A/B experiment scaffolding, polymorphic tagging, BigQuery sync job registry (guarded by ETLPermissions)

## External Dependencies

- **PostgreSQL** (postgres:11 in docker) — one schema per workspace via django-tenants; public schema holds shared apps
- **Redis** (redis:5 in docker) — entity cache (django-redis) and channel layer for WebSockets (channels_redis)
- **AWS S3** — question image storage via django-storages/boto3 (`AWS_STORAGE_BUCKET_NAME`)
- **AWS SNS** — outbound OTP SMS when `SMS_DRIVER=sns`
- **Google OAuth2** — social login exchanged for internal OAuth tokens at `/auth/convert-token/`
- **Sentry** — error monitoring (staging/production); **BigQuery** — analytics sync via the etl app

## What Does NOT Exist Here

- No frontend rendering — the Vue SPA (plio-frontend repo) is the only consumer besides embeds; this service is API + Django admin only
- No background job queue (no celery) — ETL sync is driven through the bigquery-jobs registry, everything else is request-cycle
- No hard deletes — django-safedelete intercepts deletion across models
