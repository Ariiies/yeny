"""Deterministic synthetic corpora used by the Lucis benchmarks.

Corpora are generated entirely in memory from validated profiles. The module
does not use network access, global random state, or persisted input files.
Every corpus receives a canonical SHA-256 manifest for reproducibility.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import asdict, dataclass
from typing import Dict, List, Sequence

from .config import BenchmarkProfile


@dataclass(frozen=True)
class DatasetManifest:
    """Facts needed to reproduce and identify a generated corpus.

    Attributes:
        profile: Name of the source benchmark profile.
        generator_version: Version of the generation algorithm.
        seed: Random seed used for this corpus.
        documents: Number of generated documents.
        total_tokens: Total whitespace-delimited tokens.
        vocabulary_nominal: Configured vocabulary size.
        vocabulary_observed: Terms that appeared at least once.
        intentional_duplicates: Exact duplicates inserted deliberately.
        sha256: Hash of the canonical ID/text representation.
    """

    profile: str
    generator_version: str
    seed: int
    documents: int
    total_tokens: int
    vocabulary_nominal: int
    vocabulary_observed: int
    intentional_duplicates: int
    sha256: str

    def to_dict(self) -> Dict[str, object]:
        """Return the manifest as a JSON-compatible dictionary.

        Returns:
            Dictionary containing every manifest field.
        """
        return asdict(self)


@dataclass(frozen=True)
class GeneratedDataset:
    """Generated documents and their immutable manifest.

    Attributes:
        documents: Ordered mapping from stable document ID to text.
        manifest: Reproducibility metadata for ``documents``.
    """

    documents: Dict[str, str]
    manifest: DatasetManifest


def _alphabetic_suffix(number: int) -> str:
    """Encode a non-negative integer using lowercase letters only."""
    if number < 0:
        raise ValueError("number must be non-negative")

    chars: List[str] = []
    current = number
    while True:
        current, remainder = divmod(current, 26)
        chars.append(chr(ord("a") + remainder))
        if current == 0:
            return "".join(reversed(chars))
        current -= 1


def build_vocabulary(size: int) -> List[str]:
    """Build tokenizer-safe, stable vocabulary terms.

    Args:
        size: Number of unique terms to create.

    Returns:
        Lowercase alphabetic terms accepted by ``WordTokenizer``.

    Raises:
        ValueError: If ``size`` is not greater than zero.
    """
    if size <= 0:
        raise ValueError("size must be greater than zero")
    return [f"token{_alphabetic_suffix(index)}" for index in range(size)]


def _zipf_cumulative_weights(
    size: int,
    exponent: float,
) -> List[float]:
    total = 0.0
    cumulative: List[float] = []
    for rank in range(1, size + 1):
        total += 1.0 / (rank ** exponent)
        cumulative.append(total)
    return cumulative


def _canonical_hash(documents: Dict[str, str]) -> str:
    digest = hashlib.sha256()
    for doc_id, text in documents.items():
        digest.update(doc_id.encode("utf-8"))
        digest.update(b"\t")
        digest.update(text.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _document_length(
    rng: random.Random,
    profile: BenchmarkProfile,
) -> int:
    value = rng.triangular(
        profile.min_document_tokens,
        profile.max_document_tokens,
        profile.mode_document_tokens,
    )
    return max(profile.min_document_tokens, int(round(value)))


def generate_dataset(profile: BenchmarkProfile) -> GeneratedDataset:
    """Generate the exact corpus described by ``profile``.

    A dedicated ``random.Random`` instance keeps generation isolated from the
    application's global random state.

    Args:
        profile: Validated profile controlling size and distribution.

    Returns:
        Generated documents and their reproducibility manifest.

    Raises:
        ValueError: If the profile is invalid.
    """
    profile.validate()
    rng = random.Random(profile.seed)
    vocabulary = build_vocabulary(profile.vocabulary_size)
    cumulative = _zipf_cumulative_weights(
        profile.vocabulary_size,
        profile.zipf_exponent,
    )

    duplicate_count = int(profile.documents * profile.duplicate_rate)
    original_count = profile.documents - duplicate_count
    texts: List[str] = []

    for _ in range(original_count):
        length = _document_length(rng, profile)
        tokens: Sequence[str] = rng.choices(
            vocabulary,
            cum_weights=cumulative,
            k=length,
        )
        texts.append(" ".join(tokens))

    for _ in range(duplicate_count):
        texts.append(texts[rng.randrange(original_count)])

    rng.shuffle(texts)
    width = max(6, len(str(profile.documents - 1)))
    documents = {
        f"doc_{index:0{width}d}": text
        for index, text in enumerate(texts)
    }

    observed_tokens = set()
    total_tokens = 0
    for text in texts:
        tokens = text.split()
        total_tokens += len(tokens)
        observed_tokens.update(tokens)

    manifest = DatasetManifest(
        profile=profile.name,
        generator_version=profile.generator_version,
        seed=profile.seed,
        documents=len(documents),
        total_tokens=total_tokens,
        vocabulary_nominal=profile.vocabulary_size,
        vocabulary_observed=len(observed_tokens),
        intentional_duplicates=duplicate_count,
        sha256=_canonical_hash(documents),
    )
    return GeneratedDataset(documents=documents, manifest=manifest)
