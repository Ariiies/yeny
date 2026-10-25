"""Blind-index preprocessor for Yeny — the only crypto file in this example.

READ THIS SECOND (after playground.py).

Yeny concatenates the selected columns at the SQL level
(``CONCAT_WS(' ', name, email, number, ip)``), so ``preprocessor()``
receives ONE string whose fragments are a mix of Fernet ciphertext
(``name`` / ``email`` / ``number``) and plain text (``ip``).  A search
query ("aries hotmail 612") goes through the exact same function — that
is what makes searching over encrypted fields work.

Pipeline (per fragment):

1. Try to decrypt it with Fernet.
      - ciphertext fragments  → become plaintext
      - anything else         → passes through unchanged (ip, user query)
2. Normalize: lowercase, then strip ``@``, ``+``, ``.`` and inner spaces.
3. Generate character trigrams (n=3) with Yeny' own tokenizer.
4. Blind every trigram with a deterministic HMAC-SHA256 (truncated).
5. Return the flat list of blind tokens — the index never sees plaintext.

Because normalization removes ``@ + .`` and spaces, these are equivalent:

    ariesmeza@hotmail.com   ==  ariesmezahotmailcom
    +52 612 169 6226        ==  526121696226
    127.168.192.4           ==  1271681924

Two INDEPENDENT secrets are used (set them in .env):

- ``ENCRYPTION_SECRET`` → derives the Fernet key (protects data at rest).
- ``TOKEN_HMAC_SECRET`` → keys the blind-token HMAC (protects the index).

Keys are built lazily on first use, so this module can be imported
without any environment set (handy for tests); a clear error is raised
only if a secret is actually needed and missing.
"""
import base64
import functools
import hashlib
import hmac
import os

from cryptography.fernet import Fernet
from yeny.utils.nlp import CharNgramTokenizer

TRIGRAM_N = 3

#: Hex chars kept from each HMAC digest (16 hex = 64 bits).  Changing
#: this changes every token → indexes are not compatible across values.
HMAC_HEX_LENGTH = 16


# ── Secrets → keys (lazy, built once) ────────────────────────────────────────

_fernet_instance = None
_token_hmac_secret = None


def _read_secret(env_name):
    value = os.environ.get(env_name, "").strip()
    if not value:
        raise RuntimeError(
            f"{env_name} is not set. Copy .env.example to .env and fill it "
            f"in (see README §Configuration)."
        )
    return value


def _get_fernet():
    """Fernet cipher derived from ENCRYPTION_SECRET (built on first use)."""
    global _fernet_instance
    if _fernet_instance is None:
        digest = hashlib.sha256(_read_secret("ENCRYPTION_SECRET").encode()).digest()
        _fernet_instance = Fernet(base64.urlsafe_b64encode(digest))
    return _fernet_instance


def _get_token_secret():
    """Independent HMAC secret for blinding trigrams."""
    global _token_hmac_secret
    if _token_hmac_secret is None:
        _token_hmac_secret = _read_secret("TOKEN_HMAC_SECRET")
    return _token_hmac_secret


def warn_if_demo_secrets():
    """Return warning strings when the .env still uses placeholder secrets."""
    warnings = []
    for name in ("ENCRYPTION_SECRET", "TOKEN_HMAC_SECRET"):
        if os.environ.get(name, "").startswith("replace-with-"):
            warnings.append(f"{name} is still the .env.example placeholder.")
    if (
        os.environ.get("ENCRYPTION_SECRET")
        and os.environ.get("ENCRYPTION_SECRET") == os.environ.get("TOKEN_HMAC_SECRET")
    ):
        warnings.append("ENCRYPTION_SECRET and TOKEN_HMAC_SECRET must be DIFFERENT.")
    return warnings


# ── Fernet helpers (used by database.py and the seed scripts) ────────────────


def encrypt_text(value: str) -> str:
    """Encrypt a plaintext value → ASCII Fernet ciphertext."""
    return _get_fernet().encrypt(value.encode()).decode("ascii")


def decrypt_text(value: str) -> str:
    """Decrypt Fernet ciphertext → plaintext (raises on bad input)."""
    return _get_fernet().decrypt(value.encode()).decode()


def try_decrypt(value: str) -> str:
    """Best-effort decrypt: return the input unchanged when it is NOT valid
    Fernet ciphertext (that is how plaintext columns and user queries pass
    through the pipeline untouched)."""
    try:
        return decrypt_text(value)
    except Exception:
        return value


# ── Blind tokens ─────────────────────────────────────────────────────────────


@functools.lru_cache(maxsize=None)
def _blind_token_cached(secret: str, token: str) -> str:
    # Cached: a few trigrams ("com", "mai"…) dominate bulk indexing.
    return hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()[
        :HMAC_HEX_LENGTH
    ]


def blind_token(token: str) -> str:
    """Map a normalized trigram to its deterministic blind token."""
    return _blind_token_cached(_get_token_secret(), token)


# ── The Yeny preprocessor ───────────────────────────────────────────────────

_trigram_tokenizer = CharNgramTokenizer(n=TRIGRAM_N)


def normalize(value: str) -> str:
    """Canonical form shared by indexing and querying.

    >>> normalize("Aries.Meza@Hotmail.COM")
    'ariesmezahotmailcom'
    """
    return (
        value.lower()
        .replace("@", "")
        .replace("+", "")
        .replace(".", "")
        .replace(" ", "")
    )


def preprocessor(text: str) -> list:
    """Yeny-compatible preprocessor: ``str -> list[str]`` of blind tokens.

    Pass this function to ``Yeny(preprocessor=...)`` — the SAME function
    is used while indexing and while searching, so a plaintext query
    produces the same tokens that were stored from decrypted fields.
    """
    tokens = []
    for fragment in text.split():
        plain = try_decrypt(fragment)      # 1. decrypt if ciphertext
        clean = normalize(plain)           # 2. normalize
        if not clean:
            continue
        for trigram in _trigram_tokenizer(clean):   # 3. char trigrams
            tokens.append(blind_token(trigram))     # 4. blind HMAC
    return tokens
