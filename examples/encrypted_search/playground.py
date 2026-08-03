"""Lucis playground — full-text search over Fernet-encrypted MySQL columns.

    python playground.py

READ THIS FIRST.  The whole point of this example fits in one idea:

    point Lucis at your table, pick your columns, search.

Everything below the "LUCIS SETUP" banner is the COMPLETE Lucis
integration — the rest of the file is just an interactive menu, and the
other files (database.py, seed_*.py, generate_noise.py) only prepare and
display data.  The encrypted-search magic itself is one pluggable
function: see preprocessor.py (READ THIS SECOND).

Adapting this to your own table is usually just editing .env:

    TABLE_NAME / ID_COLUMN / TEXT_COLUMNS / DATE_COLUMN  (mapping)
    USE_ENCRYPTED_PREPROCESSOR=false                     (plain-text tables)
    LUCIS_INDEX_NAME                                     (change per table!)
"""
import os
import time
from datetime import datetime

from lucis import Lucis

import database
import preprocessor as crypto
from preprocessor import preprocessor

# ------------------------------------------------------------
# CONFIGURATION — defaults come from .env, edit freely here
# ------------------------------------------------------------
database.load_env()  # reads .env next to this file; real env vars win

DB_URL = database.require_env("DATABASE_URL")

# Table mapping — point these at YOUR table:
TABLE_NAME = os.getenv("TABLE_NAME", "leads")
ID_COLUMN = os.getenv("ID_COLUMN", "id")
TEXT_COLUMNS = os.getenv("TEXT_COLUMNS", "name,email,number,ip").split(",")
DATE_COLUMN = os.getenv("DATE_COLUMN", "created_at") or None  # empty → no sharding

# Lucis settings:
INDEX_NAME = os.getenv("LUCIS_INDEX_NAME", "encrypted_leads")
ENGINE = os.getenv("LUCIS_ENGINE", "lite")
MEMORY_LIMIT_MB = int(os.getenv("LUCIS_MEMORY_LIMIT_MB", "512"))
STORAGE_DIR = os.getenv("LUCIS_STORAGE_DIR", "./lucis_data")

# Preprocessor: set USE_ENCRYPTED_PREPROCESSOR=false for plain-text tables
# → Lucis then uses its built-in tokenizer and preprocessor.py is unused.
USE_ENCRYPTED_PREPROCESSOR = (
    os.getenv("USE_ENCRYPTED_PREPROCESSOR", "true").lower() == "true"
)
ACTIVE_PREPROCESSOR = preprocessor if USE_ENCRYPTED_PREPROCESSOR else None

# Optional background services (both easy to disable):
ENABLE_WORKER = os.getenv("ENABLE_WORKER", "true").lower() == "true"
ENABLE_HEALTH_MONITOR = os.getenv("ENABLE_HEALTH_MONITOR", "true").lower() == "true"
WORKER_INTERVAL_SECONDS = int(os.getenv("WORKER_INTERVAL_SECONDS", "60"))
HEALTH_INTERVAL_SECONDS = int(os.getenv("HEALTH_INTERVAL_SECONDS", "60"))


# ------------------------------------------------------------
# LUCIS SETUP
# This is the complete Lucis integration used by this example.
# ------------------------------------------------------------
def load_or_build_index():
    """Load the persisted index, or build it from the MySQL table.

    Prints how long loading/building took and how many documents the
    index holds — local observations, not benchmarks.
    """
    # Path 1 — an index with this name already exists on disk → autoload.
    load_start = time.perf_counter()
    luc = Lucis(
        name=INDEX_NAME,
        engine=ENGINE,
        preprocessor=ACTIVE_PREPROCESSOR,
        memory_limit_mb=MEMORY_LIMIT_MB,
        storage_dir=STORAGE_DIR,
    )
    load_s = time.perf_counter() - load_start
    if luc._is_indexed:
        print(
            f"Index '{INDEX_NAME}' loaded: {luc.total_docs:,} documents "
            f"in {load_s:.2f}s"
        )
        return luc

    # Path 2 — no saved index → build it straight from the table.
    # Lucis reads the columns read-only and concatenates TEXT_COLUMNS
    # into one searchable document per row; DATE_COLUMN drives the
    # optional temporal sharding (NULL dates → universal shard 9999_99).
    print("No saved index found — building from table "
          f"'{TABLE_NAME}' ({', '.join(TEXT_COLUMNS)})…")
    build_start = time.perf_counter()
    luc = Lucis.from_alchemy_table(
        table_name=TABLE_NAME,
        id_column=ID_COLUMN,
        text_column=TEXT_COLUMNS,
        date_column=DATE_COLUMN,
        url=DB_URL,
        name=INDEX_NAME,
        engine=ENGINE,
        preprocessor=ACTIVE_PREPROCESSOR,
        memory_limit_mb=MEMORY_LIMIT_MB,
        storage_dir=STORAGE_DIR,
    )
    build_s = time.perf_counter() - build_start
    print(
        f"Index built and persisted: {luc.total_docs:,} documents "
        f"in {build_s:.2f}s"
    )
    return luc


def search(luc, query, since=None, until=None):
    """Run a plain-text query and print the matching rows, decrypted."""
    start = time.perf_counter()
    response = luc.search(query, top_k=10, since=since, until=until)
    ms = (time.perf_counter() - start) * 1000

    shards = getattr(response, "shards_searched", None)
    shard_note = f" (shards {shards}/{response.total_shards})" if shards else ""
    print(f"\n{response.total_results} result(s) in {ms:.1f} ms{shard_note}:")
    for hit in response.results:
        # The index only stores tokens — fetch the row by id and decrypt
        # it here, for display only (no-op on plain-text columns).
        lead = database.get_decrypted_lead(hit.doc_id, columns=TEXT_COLUMNS)
        shard_note = f"  (shard: {hit.shard_key})" if hit.shard_key else ""
        if lead:
            display = " | ".join(lead[col] for col in TEXT_COLUMNS)
            print(f"  {hit.rank}. [{hit.score:.4f}] {display}{shard_note}")
        else:
            print(f"  {hit.rank}. [{hit.score:.4f}] doc_id={hit.doc_id} (not in table)")
    print()


# ------------------------------------------------------------
# Everything below is just the interactive menu around the two
# functions above — no Lucis knowledge required beyond this point.
# ------------------------------------------------------------

def _add_lead():
    """Prompt for one value per TEXT_COLUMN and insert the row.

    Works for the example's leads schema and for your own table: the
    ``reference`` column is filled automatically when the table has one,
    and ENCRYPTED_COLUMNS are encrypted on insert by database.py.
    """
    row = {}
    if "reference" in database.table_columns():
        row["reference"] = f"manual-{int(time.time())}"
    for column in TEXT_COLUMNS:
        value = input(f"  {column}: ").strip()
        if not value:
            print("  All fields are required.\n")
            return
        row[column] = value
    if DATE_COLUMN:
        raw = input(f"  {DATE_COLUMN} (YYYY-MM-DD, empty = NULL → universal shard): ").strip()
        if raw:
            try:
                row[DATE_COLUMN] = datetime.strptime(raw, "%Y-%m-%d")
            except ValueError:
                print("  Invalid date — not inserted.\n")
                return
        else:
            row[DATE_COLUMN] = None
    database.insert_leads([row])
    print(f"  Row added. The worker picks it up within ~{WORKER_INTERVAL_SECONDS}s.\n")


def _show_versions(luc):
    versions = luc.list_versions()
    current = luc.storage.get_alias(INDEX_NAME)
    print(f"\n{len(versions)} version(s):")
    for version in versions:
        mark = " ← active" if version == current else ""
        short = version.split("__v")[1] if "__v" in version else version
        print(f"   • {short}{mark}")
    print()


def main():
    subtitle = (
        "search over encrypted columns"
        if USE_ENCRYPTED_PREPROCESSOR
        else f"full-text search on '{TABLE_NAME}' (plaintext preprocessor off)"
    )
    print(f"\nLucis Playground — {subtitle}")
    print("─" * 60)
    if USE_ENCRYPTED_PREPROCESSOR:
        for warning in crypto.warn_if_demo_secrets():
            print(f"  ⚠ {warning}")

    if TABLE_NAME == "leads":
        database.ensure_table()  # the example's own table: auto-create
    elif not database.table_exists():
        print(
            f"\nTable '{TABLE_NAME}' does not exist in the configured database.\n"
            "  Create it first (or fix TABLE_NAME in .env) and retry.\n"
        )
        return
    if database.count_leads() == 0:
        print(
            f"\nTable '{TABLE_NAME}' is empty.\n"
            "  → python seed_controlled_data.py     (9 easy-to-find leads)\n"
            "  → python generate_noise.py --records 1000   (optional volume)\n"
        )
        return

    luc = load_or_build_index()

    # OPTIONAL: background sync — comment out or set ENABLE_WORKER=false
    worker = None
    if ENABLE_WORKER:
        worker = luc.create_worker(
            interval=WORKER_INTERVAL_SECONDS, source_url=DB_URL
        )
        worker.start()
        print(f"Worker started (re-syncs every {WORKER_INTERVAL_SECONDS}s)")

    # OPTIONAL: health monitor — comment out or set ENABLE_HEALTH_MONITOR=false
    monitor = None
    if ENABLE_HEALTH_MONITOR:
        monitor = luc.health_monitor(
            worker=worker,
            interval=HEALTH_INTERVAL_SECONDS,
            benchmark_query="test",
            ram_warning_mb=MEMORY_LIMIT_MB,
        )
        monitor.start()
        print(f"Health monitor started (every {HEALTH_INTERVAL_SECONDS}s)")

    try:
        while True:
            print("─" * 60)
            print("[0] Exit  [1] Versions  [2] Search  [3] Add row  [4] Stats  [5] Health")
            option = input(">>> ").strip()

            if option == "0":
                break
            elif option == "1":
                _show_versions(luc)
            elif option == "2":
                query = input(f"Query ({', '.join(TEXT_COLUMNS)} — any combo): ").strip()
                if not query:
                    continue
                since = input("   Optional since (YYYY-MM-DD): ").strip() or None
                until = input("   Optional until (YYYY-MM-DD): ").strip() or None
                search(luc, query, since, until)
            elif option == "3":
                _add_lead()
            elif option == "4":
                stats = worker.stats if worker else {"cycles": 0, "rebuilds": 0}
                print(
                    f"\nDocs: {luc.total_docs:,} | DB rows: {database.count_leads():,} "
                    f"| Versions: {len(luc.list_versions())} "
                    f"| Worker cycles: {stats['cycles']} | rebuilds: {stats['rebuilds']}\n"
                )
            elif option == "5":
                print(luc.health_check(worker=worker, benchmark_query="test"))
            else:
                print("Invalid option\n")
    except (EOFError, KeyboardInterrupt):
        pass  # piped input ended or Ctrl+C — shut down cleanly
    finally:
        if monitor:
            monitor.stop()
            monitor.print_summary()
        if worker:
            worker.stop()
        print("\nBye!\n")


if __name__ == "__main__":
    main()
