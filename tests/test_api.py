import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


class TestHealthEndpoint:
    """Test the /health endpoint."""

    def test_health_returns_200(self):
        """Health check should return 200 status code."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_ok_status(self):
        """Health check should return OK status in JSON."""
        response = client.get("/health")
        assert response.json() == {"status": "ok"}


class TestQueryEndpoint:
    """Test the /query endpoint."""

    def test_query_valid_request_returns_200(self):
        """Valid query should return 200 status code."""
        response = client.post("/query", json={"query": "test question"})
        assert response.status_code == 200

    def test_query_valid_request_returns_required_fields(self):
        """Valid query should return both query and context_extrait fields."""
        response = client.post("/query", json={"query": "test question"})
        data = response.json()
        assert "query" in data
        assert "context_extrait" in data

    def test_query_valid_request_returns_correct_query(self):
        """Valid query should echo back the input query."""
        query_text = "what is this document about?"
        response = client.post("/query", json={"query": query_text})
        data = response.json()
        assert data["query"] == query_text

    def test_query_valid_request_returns_context_string(self):
        """Valid query should return context_extrait as a string."""
        response = client.post("/query", json={"query": "test question"})
        data = response.json()
        assert isinstance(data["context_extrait"], str)

    def test_query_missing_query_field_returns_422(self):
        """Query without 'query' field should return 422 (validation error)."""
        response = client.post("/query", json={})
        assert response.status_code == 422

    def test_query_malformed_json_returns_422(self):
        """Malformed JSON should return 422 (validation error)."""
        response = client.post(
            "/query",
            content="not json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_query_null_query_returns_422(self):
        """Query with null value should return 422 (validation error)."""
        response = client.post("/query", json={"query": None})
        assert response.status_code == 422


class TestReindexEndpoint:
    """Test the /reindex endpoint."""

    def test_reindex_returns_200(self):
        """Reindex should return 200 status code."""
        response = client.post("/reindex")
        assert response.status_code == 200

    def test_reindex_returns_status_field(self):
        """Reindex response should contain 'status' field."""
        response = client.post("/reindex")
        data = response.json()
        assert "status" in data
        assert isinstance(data["status"], str)


class TestUploadEndpoint:
    """Test the /upload endpoint."""

    def test_upload_invalid_format_returns_400_or_success_false(self):
        """Uploading non-PDF file should return error response."""
        response = client.post(
            "/upload",
            files={"file": ("test.txt", b"not a pdf", "text/plain")}
        )
        assert response.status_code == 200  # FastAPI returns 200 but success=False
        data = response.json()
        assert data.get("success") is False

    def test_upload_missing_file_returns_422(self):
        """Upload without file should return 422."""
        response = client.post("/upload")
        assert response.status_code == 422


class TestIntegration:
    """Integration tests for the API."""

    def test_health_then_query_flow(self):
        """Should be able to call health check then query."""
        health_response = client.get("/health")
        assert health_response.status_code == 200

        query_response = client.post("/query", json={"query": "test"})
        assert query_response.status_code == 200

    def test_reindex_then_query_flow(self):
        """Should be able to reindex then query."""
        reindex_response = client.post("/reindex")
        assert reindex_response.status_code == 200

        query_response = client.post("/query", json={"query": "test"})
        assert query_response.status_code == 200
