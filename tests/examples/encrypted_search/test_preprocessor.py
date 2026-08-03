"""Unit tests for preprocessor.py — the blind-index pipeline (no MySQL)."""
import hashlib
import hmac

import pytest

import preprocessor as pp


@pytest.mark.unit
class TestNormalize:
    def test_email_equivalence(self):
        """The documented contract: dotted/@ forms collapse to one stream."""
        assert (
            pp.normalize("luis.aries@example.com")
            == pp.normalize("luisariesexamplecom")
            == "luisariesexamplecom"
        )

    def test_phone_symbols_removed(self):
        assert pp.normalize("+52 612 169 6226") == "526121696226"

    def test_ip_dots_removed(self):
        assert pp.normalize("127.168.192.4") == "1271681924"

    def test_lowercase_and_spaces(self):
        assert pp.normalize("LuIs ArIeS") == "luisaries"

    def test_empty_after_clean(self):
        assert pp.normalize("@+. ") == ""


@pytest.mark.unit
class TestFernet:
    def test_roundtrip(self, secrets):
        ciphertext = pp.encrypt_text("Luis Aries")
        assert ciphertext != "Luis Aries"
        assert pp.decrypt_text(ciphertext) == "Luis Aries"

    def test_try_decrypt_passthrough(self, secrets):
        assert pp.try_decrypt("127.168.192.4") == "127.168.192.4"
        assert pp.try_decrypt("luis aries") == "luis aries"

    def test_try_decrypt_ciphertext(self, secrets):
        assert pp.try_decrypt(pp.encrypt_text("secret")) == "secret"

    def test_missing_secret_raises_clear_error(self, monkeypatch):
        monkeypatch.delenv("ENCRYPTION_SECRET", raising=False)
        pp._fernet_instance = None
        with pytest.raises(RuntimeError, match="ENCRYPTION_SECRET"):
            pp.encrypt_text("x")

    def test_key_derivation_matches_legacy_contract(self, secrets):
        """Fernet key == urlsafe_b64(sha256(secret)) — same derivation the
        original scripts used, kept for compatibility."""
        import base64

        from cryptography.fernet import Fernet

        manual = Fernet(
            base64.urlsafe_b64encode(
                hashlib.sha256(b"unit-test-encryption-secret").digest()
            )
        )
        token = pp.encrypt_text("interop")
        assert manual.decrypt(token.encode()).decode() == "interop"


@pytest.mark.unit
class TestBlindToken:
    def test_deterministic(self, secrets):
        assert pp.blind_token("lui") == pp.blind_token("lui")

    def test_matches_hmac_contract(self, secrets):
        expected = hmac.new(
            b"unit-test-hmac-secret", b"lui", hashlib.sha256
        ).hexdigest()[: pp.HMAC_HEX_LENGTH]
        assert pp.blind_token("lui") == expected
        assert len(expected) == 16

    def test_secret_change_changes_tokens(self, secrets, monkeypatch):
        token_a = pp.blind_token("lui")
        monkeypatch.setenv("TOKEN_HMAC_SECRET", "another-secret")
        pp._token_hmac_secret = None
        assert pp.blind_token("lui") != token_a


@pytest.mark.unit
class TestPreprocessor:
    def test_encrypted_fragment_matches_plain_query(self, secrets):
        """Core property: indexing ciphertext and querying plaintext yield
        the same blind tokens."""
        tokens_from_index = pp.preprocessor(
            pp.encrypt_text("luisaries1998@hotmail.com")
        )
        tokens_from_query = pp.preprocessor("luisaries1998@hotmail.com")
        assert tokens_from_index == tokens_from_query
        assert tokens_from_index

    def test_plaintext_column_passthrough(self, secrets):
        assert pp.preprocessor("127.168.192.4") == pp.preprocessor("1271681924")

    def test_mixed_concat_ws_text(self, secrets):
        """Simulates CONCAT_WS output: ciphertext + plaintext mixed."""
        text = f"{pp.encrypt_text('Luis Aries')} 127.168.192.2"
        tokens = pp.preprocessor(text)
        expected = pp.preprocessor("luisaries") + pp.preprocessor("127.168.192.2")
        assert tokens == expected
        # Word-separated queries hit by trigram overlap:
        assert set(pp.preprocessor("Luis Aries")) <= set(tokens)

    def test_surface_variants(self, secrets):
        joined = pp.preprocessor("luisaries")
        assert pp.preprocessor("luis.aries") == joined
        assert pp.preprocessor("Luis.Aries") == joined
        assert set(pp.preprocessor("luis aries")) <= set(joined)

    def test_empty_input(self, secrets):
        assert pp.preprocessor("") == []
        assert pp.preprocessor("   ") == []

    def test_public_signature(self):
        """The pipeline must stay a plain (str) -> list[str] function."""
        import inspect

        assert list(inspect.signature(pp.preprocessor).parameters) == ["text"]


@pytest.mark.unit
class TestDemoSecretWarnings:
    def test_placeholder_warning(self, monkeypatch):
        monkeypatch.setenv("ENCRYPTION_SECRET", "replace-with-a-long-example-secret")
        monkeypatch.setenv("TOKEN_HMAC_SECRET", "replace-with-a-different-long-secret")
        assert len(pp.warn_if_demo_secrets()) == 2

    def test_identical_secrets_warn(self, monkeypatch):
        monkeypatch.setenv("ENCRYPTION_SECRET", "same-secret")
        monkeypatch.setenv("TOKEN_HMAC_SECRET", "same-secret")
        warnings = pp.warn_if_demo_secrets()
        assert any("DIFFERENT" in w for w in warnings)

    def test_real_secrets_no_warning(self, secrets):
        assert pp.warn_if_demo_secrets() == []
