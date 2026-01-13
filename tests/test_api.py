"""
Basic API tests for Take My Dictation.
"""
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test the root endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Take My Dictation API"
        assert data["status"] == "running"


@pytest.mark.asyncio
async def test_health_check():
    """Test the health check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/admin/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_stats_endpoint():
    """Test the stats endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/admin/stats")
        assert response.status_code == 200
        data = response.json()
        assert "recordings" in data
        assert "transcriptions" in data
        assert "summaries" in data
