"""Command-line interface for running the Yeny benchmarks.

The public command intentionally exposes only a small set of options. It is
designed to be easy to reproduce on a local machine without installing
benchmark-specific dependencies.

Example::

    python -m benchmarks run --profile tiny
    python -m benchmarks run --profile small --engine core
    python -m benchmarks report benchmarks/results/<run>.json
    python -m benchmarks validate benchmarks/results/<run>.json
    python -m benchmarks aggregate benchmarks/results/*.json --output summary.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from .aggregate import AggregateError, aggregate_results, load_run, write_aggregate
from .config import BenchmarkRunConfig, load_profiles
from .memory import MemoryUnavailableError
from .reporting import render_markdown_report, render_results_table
from .results import validate_result, write_report
from .runner import BenchmarkExecutionError, run_benchmarks



def build_parser() -> argparse.ArgumentParser:
    """Create the benchmark argument parser.

    Returns:
        Configured top-level parser with the ``run``, ``report``, and
        ``validate`` subcommands.
    """
    profiles = load_profiles()
    parser = argparse.ArgumentParser(
        prog="python -m benchmarks",
        description="Run small, reproducible Yeny benchmarks.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run",
        help="Benchmark index construction, search, persistence, and mmap.",
    )
    run_parser.add_argument(
        "--profile",
        choices=tuple(profiles),
        default="tiny",
        help="Dataset profile to generate (default: tiny).",
    )
    run_parser.add_argument(
        "--engine",
        choices=("both", "core", "lite"),
        default="both",
        help="Engine selection (default: both).",
    )
    run_parser.add_argument(
        "--warmups",
        type=int,
        default=3,
        help="Warm-up searches per query (default: 3).",
    )
    run_parser.add_argument(
        "--repetitions",
        type=int,
        default=10,
        help="Measured searches per query (default: 10).",
    )
    run_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Result directory (default: benchmarks/results).",
    )
    run_parser.add_argument(
        "--require-memory",
        action="store_true",
        help=(
            "Abort with exit code 3 when no RSS measurement mechanism "
            "is available on this host."
        ),
    )

    report_parser = subparsers.add_parser(
        "report",
        help="Render a Markdown report next to a saved run JSON.",
    )
    report_parser.add_argument(
        "result",
        type=Path,
        help="Path to a yeny-benchmark-*.json file.",
    )

    validate_parser = subparsers.add_parser(
        "validate",
        help="Check a saved run JSON against the result contract.",
    )
    validate_parser.add_argument(
        "result",
        type=Path,
        help="Path to a yeny-benchmark-*.json file.",
    )

    aggregate_parser = subparsers.add_parser(
        "aggregate",
        help=(
            "Combine compatible run JSON files into one Markdown and JSON "
            "summary per environment group."
        ),
    )
    aggregate_parser.add_argument(
        "results",
        type=Path,
        nargs="+",
        help="Paths to yeny-benchmark-*.json files.",
    )
    aggregate_parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help=(
            "Markdown summary path. A sibling '<name>.aggregate.json' "
            "trace file is written too. Neither file is overwritten."
        ),
    )
    return parser



def _selected_engines(selection: str) -> Sequence[str]:
    """Expand the CLI engine selection into concrete engine names."""
    return ("core", "lite") if selection == "both" else (selection,)


def _load_result(path: Path) -> dict:
    """Read one saved benchmark result from disk.

    Args:
        path: JSON result file produced by ``python -m benchmarks run``.

    Returns:
        Parsed result dictionary.

    Raises:
        ValueError: If the file cannot be read or is not a JSON object.
    """
    try:
        with path.open("r", encoding="utf-8") as stream:
            payload = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _report_command(path: Path) -> int:
    """Render the Markdown report for one saved result.

    Args:
        path: JSON result file.

    Returns:
        ``0`` on success, ``4`` when the result cannot be read, validated,
        or written without overwriting.
    """
    try:
        result = _load_result(path)
        validate_result(result)
        target = write_report(render_markdown_report(result), path)
    except ValueError as exc:
        print(f"Report error: {exc}", file=sys.stderr)
        return 4
    except OSError as exc:
        print(f"Report error: {exc}", file=sys.stderr)
        return 4
    print(f"Markdown report: {target}")
    return 0


def _validate_command(path: Path) -> int:
    """Validate one saved result against the structural contract.

    Args:
        path: JSON result file.

    Returns:
        ``0`` when the result is valid, ``4`` otherwise.
    """
    try:
        validate_result(_load_result(path))
    except ValueError as exc:
        print(f"Validation error: {exc}", file=sys.stderr)
        return 4
    print(f"Valid benchmark result: {path}")
    return 0


def _aggregate_command(args: argparse.Namespace) -> int:
    """Aggregate compatible saved results into Markdown and JSON summaries.

    Args:
        args: Parsed ``aggregate`` subcommand arguments.

    Returns:
        ``0`` on success, ``4`` when a result cannot be read, fails
        validation, is incompatible with the others, or an output file
        would be overwritten.
    """
    try:
        results = [load_run(path) for path in args.results]
        aggregate = aggregate_results(
            results,
            sources=[str(path) for path in args.results],
        )
        markdown_path, json_path = write_aggregate(aggregate, args.output)
    except AggregateError as exc:
        print(f"Aggregation error: {exc}", file=sys.stderr)
        return 4
    except OSError as exc:
        print(f"Aggregation error: {exc}", file=sys.stderr)
        return 4
    print(f"Markdown summary: {markdown_path}")
    print(f"Aggregate JSON: {json_path}")
    if aggregate["warnings"]:
        print(f"Warnings: {len(aggregate['warnings'])} (see summary)")
    return 0


def _run_command(args: argparse.Namespace) -> int:

    """Execute one benchmark run from parsed CLI arguments.

    Args:
        args: Parsed ``run`` subcommand arguments.

    Returns:
        ``0`` on success, ``1`` for execution errors, ``2`` for invalid
        configuration, and ``3`` when required memory measurement is
        unavailable.
    """
    config = BenchmarkRunConfig(
        profile=args.profile,
        engines=tuple(_selected_engines(args.engine)),
        warmups=args.warmups,
        repetitions=args.repetitions,
        output_dir=args.output,
        require_memory=args.require_memory,
    )

    try:
        result, output_path = run_benchmarks(
            config,
            progress=lambda message: print(message, flush=True),
        )
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except MemoryUnavailableError as exc:
        print(f"Benchmark error: {exc}", file=sys.stderr)
        return 3
    except (BenchmarkExecutionError, OSError) as exc:
        print(f"Benchmark error: {exc}", file=sys.stderr)
        return 1

    print()
    print(render_results_table(result))
    print()
    print(f"JSON result: {output_path}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Run the benchmark command-line interface.

    Args:
        argv: Optional argument list without the executable name. When
            ``None``, arguments are read from ``sys.argv``.

    Returns:
        Process exit code: ``0`` on success, ``1`` for execution errors,
        ``2`` for invalid benchmark configuration, ``3`` when a required
        capability is unavailable, and ``4`` for result/report errors.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return _run_command(args)
    if args.command == "report":
        return _report_command(args.result)
    if args.command == "validate":
        return _validate_command(args.result)
    if args.command == "aggregate":
        return _aggregate_command(args)
    parser.error(f"Unknown command: {args.command}")
    return 2

