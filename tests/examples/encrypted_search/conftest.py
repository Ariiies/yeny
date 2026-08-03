"""Shared fixtures for the encrypted-search example tests.

The example is a set of STANDALONE SCRIPTS (no package), so tests add the
example directory to ``sys.path`` and import the modules directly
(``import preprocessor``), exactly like ``python playground.py`` does.
"""
import os
import sys

import pytest

EXAMPLE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "examples", "encrypted_search")
)

if EXAMPLE_DIR not in sys.path:
    sys.path.insert(0, EXAMPLE_DIR)


@pytest.fixture
def secrets(monkeypatch):
    """Provide deterministic demo secrets and reset the lazy key caches.

    preprocessor.py builds its Fernet/HMAC keys lazily from env vars, so
    tests can inject secrets without any .env file — they just need the
    caches reset afterwards.
    """
    import preprocessor

    monkeypatch.setenv("ENCRYPTION_SECRET", "unit-test-encryption-secret")
    monkeypatch.setenv("TOKEN_HMAC_SECRET", "unit-test-hmac-secret")
    preprocessor._fernet_instance = None
    preprocessor._token_hmac_secret = None
    preprocessor._blind_token_cached.cache_clear()
    yield
    preprocessor._fernet_instance = None
    preprocessor._token_hmac_secret = None
    preprocessor._blind_token_cached.cache_clear()
