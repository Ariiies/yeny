"""Tests that preserve Yeny-style documentation in benchmark modules."""

import ast
from pathlib import Path

import pytest


BENCHMARKS_DIR = Path(__file__).parents[2] / "benchmarks"


@pytest.mark.unit
def test_every_benchmark_python_module_has_docstring():
    modules = sorted(BENCHMARKS_DIR.rglob("*.py"))

    assert modules
    for module in modules:
        tree = ast.parse(module.read_text(encoding="utf-8"))
        assert ast.get_docstring(tree), f"Missing module docstring: {module}"


@pytest.mark.unit
def test_public_benchmark_symbols_have_docstrings():
    for module in sorted(BENCHMARKS_DIR.rglob("*.py")):
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
            ):
                continue
            if node.name.startswith("_"):
                continue
            assert ast.get_docstring(node), (
                f"Missing public docstring: {module}:{node.name}"
            )
