from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_health_ok(client: AsyncClient):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body
    assert body["demo_mode"] is True


async def test_me_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/me")
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] == "unauthorized"
    assert "title" in body and "detail" in body


async def test_vault_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/vault")
    assert resp.status_code == 401


async def test_verify_public_endpoint_no_auth_needed_but_chain_unavailable(client: AsyncClient):
    resp = await client.get("/api/v1/verify/1")
    # No SEPOLIA_RPC_URL configured in this sandbox -> 503, not 401: confirms
    # the route is genuinely public (no auth dependency), per section 8.2.
    assert resp.status_code == 503
    body = resp.json()
    assert body["code"] == "chain_not_configured"


async def test_unknown_route_returns_rfc7807_shape(client: AsyncClient):
    resp = await client.get("/api/v1/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert set(body.keys()) == {"type", "title", "detail", "code"}


async def test_jobs_require_cron_secret(client: AsyncClient):
    resp = await client.post("/api/v1/jobs/sync-events")
    assert resp.status_code == 401

    resp2 = await client.post("/api/v1/jobs/sync-events", headers={"X-Cron-Secret": "dev-cron-secret"})
    assert resp2.status_code == 200
