"""Configuration models for the Yeny benchmark suite.

The module validates both deterministic dataset profiles and the small set of
options accepted by the benchmark runner. Configuration errors are reported
before any benchmark process starts.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple


DEFAULT_PROFILES_PATH = Path(__file__).with_name("profiles.json")
DEFAULT_REFERENCE_HASHES_PATH = Path(__file__).with_name(
    "reference_hashes.json"
)
DEFAULT_OUTPUT_DIR = Path(__file__).with_name("results")
PROJECT_SRC_DIR = Path(__file__).resolve().parents[1] / "src"

# Expected frozen versions. ``query_set_version`` intentionally mirrors
# ``benchmarks.queries.QUERY_SET_VERSION``; importing it here would create a
# module cycle, and a dedicated test keeps both values synchronized.
EXPECTED_GENERATOR_VERSION = "lexical_zipf_v1"
EXPECTED_QUERY_SET_VERSION = "queries_v1"


@dataclass(frozen=True)
class BenchmarkProfile:
    """Validated configuration for one deterministic corpus.

    Attributes:
        name: Stable profile name exposed by the CLI.
        documents: Number of documents to generate.
        vocabulary_size: Nominal number of available terms.
        min_document_tokens: Minimum generated document length.
        mode_document_tokens: Most likely generated document length.
        max_document_tokens: Maximum generated document length.
        zipf_exponent: Exponent controlling the token frequency distribution.
        duplicate_rate: Fraction of intentional exact duplicates.
        seed: Seed used by the profile-local random generator.
        generator_version: Version of the corpus generation algorithm.
    """

    name: str
    documents: int
    vocabulary_size: int
    min_document_tokens: int
    mode_document_tokens: int
    max_document_tokens: int
    zipf_exponent: float
    duplicate_rate: float
    seed: int
    generator_version: str = "lexical_zipf_v1"

    @classmethod
    def from_mapping(
        cls,
        name: str,
        values: Mapping[str, Any],
        *,
        generator_version: str = "lexical_zipf_v1",
    ) -> "BenchmarkProfile":
        """Build and validate a profile loaded from JSON.

        Args:
            name: Profile identifier.
            values: Raw profile fields loaded from JSON.
            generator_version: Dataset generator contract version.

        Returns:
            Validated immutable benchmark profile.

        Raises:
            ValueError: If a required field is missing or invalid.
        """
        required = {
            "documents",
            "vocabulary_size",
            "min_document_tokens",
            "mode_document_tokens",
            "max_document_tokens",
            "zipf_exponent",
            "duplicate_rate",
            "seed",
        }
        missing = sorted(required.difference(values))
        if missing:
            raise ValueError(
                f"Profile {name!r} is missing fields: {', '.join(missing)}"
            )

        profile = cls(
            name=name,
            documents=_as_int(values["documents"], "documents"),
            vocabulary_size=_as_int(
                values["vocabulary_size"], "vocabulary_size"
            ),
            min_document_tokens=_as_int(
                values["min_document_tokens"], "min_document_tokens"
            ),
            mode_document_tokens=_as_int(
                values["mode_document_tokens"], "mode_document_tokens"
            ),
            max_document_tokens=_as_int(
                values["max_document_tokens"], "max_document_tokens"
            ),
            zipf_exponent=_as_float(
                values["zipf_exponent"], "zipf_exponent"
            ),
            duplicate_rate=_as_float(
                values["duplicate_rate"], "duplicate_rate"
            ),
            seed=_as_int(values["seed"], "seed"),
            generator_version=generator_version,
        )
        profile.validate()
        return profile

    def validate(self) -> None:
        """Validate all profile constraints.

        Raises:
            ValueError: If the profile cannot produce a meaningful corpus.
        """
        if not self.name.strip():
            raise ValueError("Profile name cannot be empty")
        if self.documents <= 0:
            raise ValueError("documents must be greater than zero")
        if self.vocabulary_size < 8:
            raise ValueError("vocabulary_size must be at least 8")
        if not (
            1
            <= self.min_document_tokens
            <= self.mode_document_tokens
            <= self.max_document_tokens
        ):
            raise ValueError(
                "document token bounds must satisfy "
                "1 <= min <= mode <= max"
            )
        if self.zipf_exponent <= 0:
            raise ValueError("zipf_exponent must be greater than zero")
        if not 0 <= self.duplicate_rate < 1:
            raise ValueError("duplicate_rate must be in the range [0, 1)")


@dataclass(frozen=True)
class BenchmarkRunConfig:
    """Validated options for one benchmark invocation.

    Attributes:
        profile: Dataset profile name.
        engines: Engine keys to run in isolated processes.
        warmups: Unmeasured search calls per query.
        repetitions: Measured calls per normal query.
        output_dir: Optional result directory. ``None`` uses
            ``benchmarks/results``.
        require_memory: When ``True``, the run aborts unless at least one
            RSS measurement mechanism exists on this host.
    """

    profile: str = "tiny"
    engines: Tuple[str, ...] = ("core", "lite")
    warmups: int = 3
    repetitions: int = 10
    output_dir: Optional[Path] = None
    require_memory: bool = False

    def validate(self) -> None:
        """Validate the run before launching subprocesses.

        Raises:
            ValueError: If the profile, engines, counts, or output path are
                invalid.
        """
        if self.profile not in load_profiles():
            raise ValueError(f"Unknown benchmark profile: {self.profile}")
        if not self.engines:
            raise ValueError("At least one engine is required")
        if len(set(self.engines)) != len(self.engines):
            raise ValueError("Engine names cannot be repeated")
        unknown_engines = sorted(set(self.engines).difference({"core", "lite"}))
        if unknown_engines:
            raise ValueError(
                f"Unknown benchmark engines: {', '.join(unknown_engines)}"
            )
        if self.warmups < 0:
            raise ValueError("warmups cannot be negative")
        if self.repetitions <= 0:
            raise ValueError("repetitions must be greater than zero")
        self.resolved_output_dir()

    def resolved_output_dir(self) -> Path:
        """Resolve and protect the result directory.

        Returns:
            Absolute result directory.

        Raises:
            ValueError: If the selected directory is ``src/`` or one of its
                descendants.
        """
        selected = self.output_dir or DEFAULT_OUTPUT_DIR
        resolved = selected.expanduser().resolve()
        source = PROJECT_SRC_DIR.resolve()
        if resolved == source or source in resolved.parents:
            raise ValueError("Benchmark output cannot be written inside src/")
        return resolved

    def to_dict(self) -> Dict[str, Any]:
        """Return the run configuration as a JSON-compatible dictionary.

        Returns:
            Dictionary containing all effective user-visible options.
        """
        payload = asdict(self)
        payload["engines"] = list(self.engines)
        payload["output_dir"] = str(self.resolved_output_dir())
        return payload


def _as_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    return value


def _as_float(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number")
    return float(value)


def load_profiles(
    path: Optional[Path] = None,
) -> Dict[str, BenchmarkProfile]:
    """Load all benchmark profiles from a JSON file.

    Args:
        path: Optional alternate profiles file.

    Returns:
        Ordered mapping from profile name to validated profile.

    Raises:
        OSError: If the profiles file cannot be read.
        ValueError: If the schema or any profile is invalid.
    """
    profile_path = path or DEFAULT_PROFILES_PATH
    with profile_path.open("r", encoding="utf-8") as stream:
        payload = json.load(stream)

    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported profiles schema_version")

    generator_version = payload.get(
        "generator_version", "lexical_zipf_v1"
    )
    raw_profiles = payload.get("profiles")
    if not isinstance(raw_profiles, dict) or not raw_profiles:
        raise ValueError("profiles must be a non-empty object")

    return {
        name: BenchmarkProfile.from_mapping(
            name,
            _profile_mapping(name, values),
            generator_version=generator_version,
        )
        for name, values in raw_profiles.items()
    }


def _profile_mapping(
    name: str,
    values: Any,
) -> Mapping[str, Any]:
    if not isinstance(values, Mapping):
        raise ValueError(f"Profile {name!r} must be an object")
    return values


def _require_sha256(value: Any, field: str) -> str:
    """Validate one lowercase hexadecimal SHA-256 digest."""
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError(f"{field} must be a 64-character lowercase hex hash")
    return value


def load_reference_hashes(
    path: Optional[Path] = None,
) -> Dict[str, Dict[str, str]]:
    """Load the frozen dataset/query hashes for every known profile.

    The reference file is the deterministic contract of the benchmark
    campaign: every official environment must reproduce exactly these
    hashes. A mismatch must be investigated, never silenced by editing the
    reference.

    Args:
        path: Optional alternate reference hashes file.

    Returns:
        Mapping from profile name to ``dataset_sha256`` and
        ``queries_sha256`` digests.

    Raises:
        OSError: If the reference file cannot be read.
        ValueError: If the schema, versions, profiles, or hash formats are
            invalid or incomplete.
    """
    reference_path = path or DEFAULT_REFERENCE_HASHES_PATH
    with reference_path.open("r", encoding="utf-8") as stream:
        payload = json.load(stream)

    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported reference_hashes schema_version")
    if payload.get("generator_version") != EXPECTED_GENERATOR_VERSION:
        raise ValueError("Unsupported reference_hashes generator_version")
    if payload.get("query_set_version") != EXPECTED_QUERY_SET_VERSION:
        raise ValueError("Unsupported reference_hashes query_set_version")

    raw_profiles = payload.get("profiles")
    if not isinstance(raw_profiles, Mapping) or not raw_profiles:
        raise ValueError("reference_hashes profiles must be an object")

    known = set(load_profiles())
    provided = set(raw_profiles)
    if provided != known:
        missing = sorted(known.difference(provided))
        unknown = sorted(provided.difference(known))
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if unknown:
            details.append(f"unknown: {', '.join(unknown)}")
        raise ValueError(
            f"reference_hashes profiles do not match profiles.json "
            f"({'; '.join(details)})"
        )

    reference: Dict[str, Dict[str, str]] = {}
    for name, values in raw_profiles.items():
        if not isinstance(values, Mapping):
            raise ValueError(
                f"reference_hashes profile {name!r} must be an object"
            )
        reference[name] = {
            "dataset_sha256": _require_sha256(
                values.get("dataset_sha256"),
                f"{name}.dataset_sha256",
            ),
            "queries_sha256": _require_sha256(
                values.get("queries_sha256"),
                f"{name}.queries_sha256",
            ),
        }
    return reference
