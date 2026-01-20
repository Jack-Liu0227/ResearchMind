"""
Session ID helpers.

Centralizes session ID generation so every service uses the same format.
"""

import random
import string
import time
from typing import Optional


def generate_session_id() -> str:
    """Generate a session_id in the unified format: session_{timestamp}_{random_id}."""
    timestamp = int(time.time() * 1000)
    random_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"session_{timestamp}_{random_id}"


def ensure_session_id(session_id: Optional[str]) -> str:
    """Return a valid session_id, generating one if missing."""
    return session_id or generate_session_id()
