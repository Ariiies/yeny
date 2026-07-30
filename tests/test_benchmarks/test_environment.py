"""Tests for benchmark environment metadata collection."""

import json
import sys

import pytest

from benchmarks import environment


@pytest.mark.unit
def test_environment_is_json_serializable():
    payload = environment.collect_environment()

    encoded = json.dumps(payload)

    assert json.loads(encoded)["python_version"]


@pytest.mark.unit
def test_environment_reports_required_keys():
    payload = environment.collect_environment()

    expected = {
        "python_version",
        "python_implementation",
        "python_executable",
        "lucis_version",
        "platform",
        "system",
        "release",
        "machine",
        "processor",
        "cpu_model",
        "logical_cpu_count",
        "total_ram_bytes",
        "psutil_version",
        "psutil_available",
        "memory_mechanisms",
        "perf_counter_resolution_seconds",
        "git_commit",
        "git_dirty",
    }
    assert expected.issubset(payload)


@pytest.mark.unit
def test_environment_reports_positive_values_when_available():
    payload = environment.collect_environment()

    assert payload["logical_cpu_count"] > 0
    assert payload["perf_counter_resolution_seconds"] > 0
    if sys.platform.startswith("linux"):
        assert payload["cpu_model"]
        assert payload["total_ram_bytes"] > 0
    if payload["psutil_available"]:
        assert payload["psutil_version"]
        assert "psutil" in payload["memory_mechanisms"]


@pytest.mark.unit
def test_cpu_model_uses_linux_cpuinfo(monkeypatch):
    monkeypatch.setattr(environment.platform, "system", lambda: "Linux")
    monkeypatch.setattr(
        environment,
        "_linux_cpu_model",
        lambda: "Test CPU 9000",
    )

    assert environment.cpu_model() == "Test CPU 9000"


@pytest.mark.unit
def test_cpu_model_uses_windows_identifier(monkeypatch):
    monkeypatch.setattr(environment.platform, "system", lambda: "Windows")
    monkeypatch.setattr(
        environment.platform,
        "processor",
        lambda: "  WindowsCPU 1.0  ",
    )

    assert environment.cpu_model() == "WindowsCPU 1.0"


@pytest.mark.unit
def test_cpu_model_falls_back_to_processor_identifier(monkeypatch):
    monkeypatch.setattr(environment.platform, "system", lambda: "Windows")
    monkeypatch.setattr(environment.platform, "processor", lambda: "")
    monkeypatch.setattr(
        environment.os,
        "environ",
        {"PROCESSOR_IDENTIFIER": "IdentifierCPU 2.0"},
    )

    assert environment.cpu_model() == "IdentifierCPU 2.0"


@pytest.mark.unit
def test_cpu_model_uses_macos_sysctl(monkeypatch):
    monkeypatch.setattr(environment.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        environment,
        "_macos_cpu_model",
        lambda: "Apple M-test",
    )

    assert environment.cpu_model() == "Apple M-test"


@pytest.mark.unit
def test_cpu_model_absence_is_none(monkeypatch):
    monkeypatch.setattr(environment.platform, "system", lambda: "OtherOS")
    monkeypatch.setattr(environment.platform, "processor", lambda: "")

    assert environment.cpu_model() is None


@pytest.mark.unit
def test_total_ram_prefers_psutil(monkeypatch):
    class FakeVirtualMemory:
        total = 16 * 1024**3

    monkeypatch.setattr(
        environment.psutil,
        "virtual_memory",
        lambda: FakeVirtualMemory(),
    )

    assert environment.total_ram_bytes() == 16 * 1024**3


@pytest.mark.unit
def test_total_ram_falls_back_to_linux_meminfo(monkeypatch, tmp_path):
    monkeypatch.setattr(environment, "psutil", None)
    monkeypatch.setattr(environment.platform, "system", lambda: "Linux")
    meminfo = tmp_path / "meminfo"
    meminfo.write_text(
        "MemTotal:        8192000 kB\nMemFree:         1024000 kB\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        environment,
        "_linux_total_ram_bytes",
        lambda: 8192000 * 1024,
    )

    assert environment.total_ram_bytes() == 8192000 * 1024


@pytest.mark.unit
def test_total_ram_absence_is_none_not_zero(monkeypatch):
    monkeypatch.setattr(environment, "psutil", None)
    monkeypatch.setattr(environment.platform, "system", lambda: "OtherOS")

    assert environment.total_ram_bytes() is None
    assert environment.total_ram_bytes() != 0


@pytest.mark.unit
def test_psutil_version_absence_is_none(monkeypatch):
    monkeypatch.setattr(environment, "psutil", None)

    assert environment.psutil_version() is None


@pytest.mark.unit
def test_linux_cpu_model_reads_proc_cpuinfo(monkeypatch, tmp_path):
    from pathlib import Path

    cpuinfo = tmp_path / "cpuinfo"
    cpuinfo.write_text(
        "processor\t: 0\nmodel name\t: Virtual CPU Xeon\n\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        environment,
        "Path",
        lambda value: (
            cpuinfo if value == "/proc/cpuinfo" else Path(value)
        ),
    )

    assert environment._linux_cpu_model() == "Virtual CPU Xeon"

