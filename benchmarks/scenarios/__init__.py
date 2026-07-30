"""Isolated measurement scenarios for the Lucis benchmark suite.

Each module implements one persistence boundary: standard JSON/SQLite
round-trips through the public ``Lucis`` facade, and engine-level ``.lcs``
serialization with memory-mapped loading. Scenario functions receive an
indexed instance (or a fresh-instance constructor) and return measurement
dictionaries ready for the result document.
"""
