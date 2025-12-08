"""
Gemini REST API Client

Direct REST API calls to Google's Generative Language API.
No SDK dependency - works with any Gemini model.

Supports:
- gemini-3-pro (latest)
- gemini-3-pro-preview
- gemini-2.5-pro
- gemini-2.5-flash
- gemini-2.5-flash-lite
- And all other available models
"""

import logging
import os
import json
from typing import Dict, Any, Optional, List
import requests

logger = logging.getLogger(__name__)


class GeminiRestClient:
    """
    REST API client for Google's Generative Language API.

    No external dependencies beyond requests library.
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-3-pro-preview"):
        """
        Initialize Gemini REST client.

        Args:
            api_key: Google API key (uses GOOGLE_API_KEY env var if not provided)
            model: Model to use (default: gemini-3-pro-preview)
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")

        self.model = model
        self.session = requests.Session()

    def generate_content(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 8000,
        system_instruction: Optional[str] = None,
        response_format: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Generate content using Gemini API.

        Args:
            prompt: User prompt
            temperature: Generation temperature (0-1)
            max_tokens: Maximum tokens in response
            system_instruction: System role instruction
            response_format: Response format (e.g., 'application/json')
            tools: Tools/functions available to the model

        Returns:
            Generated text content

        Raises:
            ValueError: If API returns an error
        """
        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        # Add system instruction if provided
        if system_instruction:
            body["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        # Add response format if specified
        if response_format == "json":
            body["generationConfig"]["responseMimeType"] = "application/json"
        elif response_format:
            body["generationConfig"]["responseMimeType"] = response_format

        # Add tools if provided
        if tools:
            body["tools"] = tools

        # Make API call
        url = f"{self.BASE_URL}/models/{self.model}:generateContent"
        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key}

        try:
            response = self.session.post(url, json=body, headers=headers, params=params, timeout=60)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise ValueError(f"Gemini API error: {e}")

        # Parse response
        data = response.json()

        # Check for errors
        if "error" in data:
            error_msg = data["error"].get("message", "Unknown error")
            logger.error(f"Gemini API error: {error_msg}")
            raise ValueError(f"Gemini API error: {error_msg}")

        # Extract text from response
        if not data.get("candidates"):
            logger.warning(f"No candidates in response. Full response: {data}")
            raise ValueError("No candidates in API response")

        candidate = data["candidates"][0]

        # Check for blocked/empty content
        if candidate.get("finishReason") == "SAFETY":
            raise ValueError("Response blocked by safety filter")

        if not candidate.get("content", {}).get("parts"):
            logger.warning(f"No parts in candidate. Candidate: {candidate}")
            raise ValueError("No content in API response")

        text = candidate["content"]["parts"][0].get("text", "")

        if not text:
            logger.warning(f"Empty text in response. Parts: {candidate.get('content', {}).get('parts')}")
            raise ValueError("Empty response from API")

        # Log token usage
        usage = data.get("usageMetadata", {})
        if usage:
            logger.debug(
                f"Token usage - Input: {usage.get('promptTokenCount', 0)}, "
                f"Output: {usage.get('candidatesTokenCount', 0)}"
            )

        return text

    def generate_content_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        temperature: float = 0.7,
        system_instruction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate structured content (JSON) matching a schema.

        Args:
            prompt: User prompt
            schema: JSON schema for response
            temperature: Generation temperature
            system_instruction: System instruction

        Returns:
            Parsed JSON response as dictionary

        Raises:
            ValueError: If API returns error or invalid JSON
        """
        # Add schema to system instruction
        schema_instruction = f"""You must respond with valid JSON matching this schema:
{json.dumps(schema, indent=2)}

Respond ONLY with valid JSON, no markdown, no explanation."""

        if system_instruction:
            schema_instruction = system_instruction + "\n\n" + schema_instruction

        # Request JSON format
        text = self.generate_content(
            prompt=prompt,
            temperature=temperature,
            system_instruction=schema_instruction,
            response_format="json",
        )

        # Parse JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}\nResponse: {text[:200]}")
            raise ValueError(f"Invalid JSON in response: {e}")

    def get_available_models(self) -> List[str]:
        """
        Get list of available models.

        Returns:
            List of available model names
        """
        url = f"{self.BASE_URL}/models"
        params = {"key": self.api_key}

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            models = [m.get("name", "").replace("models/", "") for m in data.get("models", [])]
            return models
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    def validate_api_key(self) -> bool:
        """
        Test if API key is valid.

        Returns:
            True if API key works, False otherwise
        """
        try:
            models = self.get_available_models()
            return len(models) > 0
        except Exception:
            return False


# Convenience function
def create_gemini_client(
    api_key: Optional[str] = None,
    model: str = "gemini-3-pro-preview",
) -> GeminiRestClient:
    """
    Create a Gemini REST API client.

    Args:
        api_key: Google API key (uses env var if not provided)
        model: Model name (default: gemini-3-pro-preview)

    Returns:
        GeminiRestClient instance
    """
    return GeminiRestClient(api_key=api_key, model=model)
