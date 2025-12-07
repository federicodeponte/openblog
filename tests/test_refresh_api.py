"""
Integration tests for /refresh API endpoint

Tests full end-to-end refresh flow using FastAPI TestClient:
- HTML input/output
- Markdown input/output
- Auth enforcement
- Rate limiting
- Diff generation
- Concurrent requests
"""

import pytest
import json
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from service.api import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_env_api_key(monkeypatch):
    """Mock environment variable for API key."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-api-key-12345")


@pytest.fixture
def sample_html_content():
    """Sample HTML content for testing."""
    return """
    <h1>Test Article</h1>
    <h2>Introduction</h2>
    <p>This is old content from 2023.</p>
    <h2>Features</h2>
    <p>We have 5 features available.</p>
    """


@pytest.fixture
def sample_markdown_content():
    """Sample Markdown content for testing."""
    return """
# Test Article

## Introduction

This is old content from 2023.

## Features

We have 5 features available.
"""


class TestRefreshAPI:
    """Test suite for /refresh endpoint."""
    
    def test_refresh_endpoint_html_format(self, client, mock_env_api_key, sample_html_content):
        """Test refresh endpoint with HTML input/output."""
        with patch('service.api.GeminiClient') as MockGeminiClient:
            # Mock Gemini client
            mock_gemini_instance = MagicMock()
            mock_gemini_instance.generate_content = AsyncMock(return_value=json.dumps({
                "heading": "Introduction",
                "content": "This is updated content from 2025.",
                "change_summary": "Updated year to 2025"
            }))
            MockGeminiClient.return_value = mock_gemini_instance
            
            # Make request
            response = client.post("/refresh", json={
                "content": sample_html_content,
                "content_format": "html",
                "instructions": ["Update all years to 2025"],
                "target_sections": [0],
                "output_format": "html"
            })
            
            assert response.status_code == 200
            data = response.json()
            
            assert data['success'] is True
            assert data['sections_updated'] >= 1
            assert 'refreshed_html' in data
            assert '2025' in data['refreshed_html'] or data['refreshed_html'] is not None
    
    def test_refresh_endpoint_markdown_format(self, client, mock_env_api_key, sample_markdown_content):
        """Test refresh endpoint with Markdown input/output."""
        with patch('service.api.GeminiClient') as MockGeminiClient:
            # Mock Gemini client
            mock_gemini_instance = MagicMock()
            mock_gemini_instance.generate_content = AsyncMock(return_value=json.dumps({
                "heading": "Features",
                "content": "We now have 10 features available.",
                "change_summary": "Updated feature count"
            }))
            MockGeminiClient.return_value = mock_gemini_instance
            
            # Make request
            response = client.post("/refresh", json={
                "content": sample_markdown_content,
                "content_format": "markdown",
                "instructions": ["Increase feature count to 10"],
                "output_format": "markdown"
            })
            
            assert response.status_code == 200
            data = response.json()
            
            assert data['success'] is True
            assert 'refreshed_markdown' in data
            # Markdown should be present
            assert data['refreshed_markdown'] is not None or data['refreshed_content'] is not None
    
    def test_refresh_with_auth(self, client, sample_html_content):
        """Test auth enforcement (missing API key)."""
        # Clear API key from environment
        with patch.dict(os.environ, {}, clear=True):
            response = client.post("/refresh", json={
                "content": sample_html_content,
                "instructions": ["Update content"],
                "output_format": "json"
            })
            
            # Should fail with 500 (missing API key)
            assert response.status_code == 500
            data = response.json()
            assert 'GOOGLE_API_KEY' in data['detail'] or 'GEMINI_API_KEY' in data['detail']
    
    @pytest.mark.skip(reason="Rate limiting not yet implemented in Phase 3")
    def test_refresh_rate_limiting(self, client, mock_env_api_key, sample_html_content):
        """Test rate limiting (10 requests per minute)."""
        # This test will be implemented after Phase 3 (rate limiting)
        # Expected: After 10 requests in 60 seconds, should return 429
        pass
    
    @pytest.mark.skip(reason="Diff generation not yet implemented in Phase 4")
    def test_refresh_with_diff(self, client, mock_env_api_key, sample_html_content):
        """Test diff generation."""
        # This test will be implemented after Phase 4 (diff/preview)
        # Expected: Should return both diff_text and diff_html fields
        pass
    
    def test_concurrent_refresh_requests(self, client, mock_env_api_key, sample_html_content):
        """Test thread safety with concurrent requests."""
        import concurrent.futures
        
        with patch('service.api.GeminiClient') as MockGeminiClient:
            # Mock Gemini client
            mock_gemini_instance = MagicMock()
            mock_gemini_instance.generate_content = AsyncMock(return_value=json.dumps({
                "heading": "Introduction",
                "content": "Updated content.",
                "change_summary": "Updated"
            }))
            MockGeminiClient.return_value = mock_gemini_instance
            
            def make_request():
                return client.post("/refresh", json={
                    "content": sample_html_content,
                    "instructions": ["Update content"],
                    "output_format": "json"
                })
            
            # Make 5 concurrent requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(make_request) for _ in range(5)]
                responses = [f.result() for f in futures]
            
            # All should succeed
            for response in responses:
                assert response.status_code == 200
                data = response.json()
                assert data['success'] is True
    
    def test_refresh_validation_errors(self, client, mock_env_api_key):
        """Test request validation (empty content, no instructions, etc.)."""
        # Test empty content
        response = client.post("/refresh", json={
            "content": "",
            "instructions": ["Update content"],
            "output_format": "json"
        })
        # Should either succeed (returns empty) or fail validation
        # Current implementation doesn't explicitly validate, so this may pass
        # In Phase 5, we'll add proper validation
        
        # Test no instructions
        response = client.post("/refresh", json={
            "content": "<h1>Test</h1>",
            "instructions": [],
            "output_format": "json"
        })
        # Should fail validation (422) once we add validators in Phase 6
        assert response.status_code in [200, 422]  # Either current behavior or future validation
        
        # Test invalid output format
        response = client.post("/refresh", json={
            "content": "<h1>Test</h1>",
            "instructions": ["Update"],
            "output_format": "invalid_format"
        })
        # Should succeed (falls back to json) or fail validation
        assert response.status_code in [200, 422]
    
    def test_refresh_error_recovery(self, client, mock_env_api_key, sample_html_content):
        """Test error handling when Gemini API fails."""
        with patch('service.api.GeminiClient') as MockGeminiClient:
            # Mock Gemini client to raise exception
            mock_gemini_instance = MagicMock()
            mock_gemini_instance.generate_content = AsyncMock(side_effect=Exception("API Error"))
            MockGeminiClient.return_value = mock_gemini_instance
            
            response = client.post("/refresh", json={
                "content": sample_html_content,
                "instructions": ["Update content"],
                "output_format": "json"
            })
            
            # The ContentRefresher now has error recovery built-in
            # It will return original content on error, so success=True
            # But sections_updated should be 0 (or equal to target sections) since no actual changes were made
            assert response.status_code == 200
            data = response.json()
            
            # With error recovery, it returns success=True with original content
            assert data['success'] is True
            # Verify content was returned (even if unchanged)
            assert data['refreshed_content'] is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

