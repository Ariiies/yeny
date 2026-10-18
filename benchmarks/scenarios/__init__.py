"""Isolated measurement scenarios for the Yeny benchmark suite.

Each module implements one persistence boundary: standard JSON/SQLite
round-trips through the public ``Yeny`` facade, and engine-level ``.yny``
serialization with memory-mapped loading. Scenario functions receive an
indexed instance (or a fresh-instance constructor) and return measurement
dictionaries ready for the result document.
"""
