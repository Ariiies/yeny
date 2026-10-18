"""Command-line entry point for the Yeny benchmark suite.

This module keeps ``python -m benchmarks`` equivalent to calling
``benchmarks.cli.main`` directly.
"""

from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())
