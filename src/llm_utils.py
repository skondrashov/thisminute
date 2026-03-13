"""Shared LLM utilities for thisminute.

Single source of truth for: Anthropic client, model IDs, response parsing.
"""

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# --- Model IDs (change here to update everywhere) ---
HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"

# Singleton client instance
_client = None
_client_checked = False


def get_anthropic_client():
    """Get shared Anthropic client, or None if unavailable.

    Caches the client instance so we don't re-create it on every call.
    """
    global _client, _client_checked
    if _client_checked:
        return _client
    _client_checked = True

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None
    try:
        import anthropic
        _client = anthropic.Anthropic(api_key=api_key, timeout=60.0)
        return _client
    except ImportError:
        logger.warning("anthropic package not installed")
        return None
    except Exception as e:
        logger.warning("Failed to create Anthropic client: %s", e)
        return None


def strip_code_fences(text: str) -> str:
    """Strip markdown code fences from LLM response text."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return text


def parse_llm_json(text: str, expected_type: str = "auto"):
    """Parse JSON from an LLM response, stripping code fences.

    Args:
        text: Raw LLM response text
        expected_type: "list", "dict", or "auto"

    Returns:
        Parsed object, or None if parsing fails or type doesn't match.
    """
    text = strip_code_fences(text)
    try:
        obj = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None

    if expected_type == "auto":
        return obj
    if expected_type == "list":
        if isinstance(obj, list):
            return obj
        if isinstance(obj, dict):
            return [obj]
        return None
    if expected_type == "dict":
        return obj if isinstance(obj, dict) else None
    return obj


def parse_json_field(val, default=None):
    """Safely parse a JSON string field that may already be decoded."""
    if default is None:
        default = []
    if isinstance(val, type(default)):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            pass
    return default
