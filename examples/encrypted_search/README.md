# Encrypted Search with Lucis

> Full-text search over Fernet-encrypted MySQL columns — with ~15 lines
> of Lucis-specific code.  *(Reproducible example: blind index of
> trigrams + HMAC, queried with plain text.)*

This example demonstrates how Lucis can index and search a MySQL table
containing encrypted fields.  **The complete Lucis integration lives in
`playground.py`.**  To understand the example, read only:

1. **`playground.py`** — point Lucis at a table, pick columns, search.
2. **`preprocessor.py`** — the optional plug-in that makes *encrypted*
   fields searchable (blind index: trigrams → deterministic HMAC).

The remaining files only prepare or display data:

| file | role |
|------|------|
| `database.py` | small helper: `.env`, table DDL, inserts, decrypt-for-display |
| `seed_controlled_data.py` | inserts 10 easy-to-find leads (Aries Meza, Real Madrid, …) |
| `generate_noise.py` | optional: deterministic bulk volume (`--records 100000`) |

Prefer a visual overview? Jump to the [visual walkthrough: Lucis in 3
steps](#10-visual-walkthrough-lucis-in-3-steps).

---

## 1. The complete Lucis integration

This is the whole thing — copied from `playground.py`:

```python
from lucis import Lucis
from preprocessor import preprocessor   # only for encrypted fields

# Path 1 — a saved index already exists → autoload (mmap, fast).
luc = Lucis(
    name="encrypted_leads",
    engine="lite",
    preprocessor=preprocessor,
    memory_limit_mb=512,
    storage_dir="./lucis_data",
)

# Path 2 — no saved index → build it straight from the table.
if not luc._is_indexed:
    luc = Lucis.from_alchemy_table(
        table_name="leads",
        id_column="id",
        text_column=["name", "email", "number", "ip"],  # cross-field
        date_column="created_at",                       # temporal shards
        url=DB_URL,
        name="encrypted_leads",
        engine="lite",
        preprocessor=preprocessor,
    )

results = luc.search("aries hotmail 612")
```

**That is all the Lucis-specific code there is.**  Everything else in the
example encrypts seed data, generates volume, or prints results.

---

## 2. Quick start

Requires Python 3.10+ and a reachable MySQL 8.x.

**Linux / macOS**

```bash
cd examples/encrypted_search

python -m venv .venv
source .venv/bin/activate
pip install "../..[encrypted-search-example]"

cp .env.example .env        # then edit DATABASE_URL + secrets
```

**Windows (PowerShell)**

```powershell
cd examples/encrypted_search
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install "../..[encrypted-search-example]"
Copy-Item .env.example .env
```

Create the database (once — the example never runs `CREATE DATABASE`):

```sql
CREATE DATABASE lucis_encrypted_search
CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Then:

```bash
python seed_controlled_data.py      # 10 controlled leads (encrypted)
python generate_noise.py --records 100000 --seed 20260801 # optional; useful for testing scale
python playground.py                # builds the index, opens the menu
```


No CLI, no subcommands, no package install of the example itself —
just scripts.

---

## 3. Configuration via `.env`

`.env` is the main configuration point — adapt the playground to other
tables **without touching code** (real environment variables always win;
only this folder's `.env` is read, never a repo-root one):

```dotenv
DATABASE_URL=mysql+pymysql://lucis_user:change-me@localhost:3306/lucis_encrypted_search

# Table mapping — point these at YOUR table
TABLE_NAME=leads
ID_COLUMN=id
TEXT_COLUMNS=name,email,number,ip
DATE_COLUMN=created_at        # leave empty to disable temporal sharding

# Lucis
LUCIS_INDEX_NAME=encrypted_leads    # change it per table! (autoload key)
LUCIS_ENGINE=lite
LUCIS_MEMORY_LIMIT_MB=512
LUCIS_STORAGE_DIR=./lucis_data

# Plain-text table? → no encrypted preprocessor needed
USE_ENCRYPTED_PREPROCESSOR=true

# Two INDEPENDENT secrets (only used when the preprocessor is on)
ENCRYPTION_SECRET=replace-with-a-long-example-secret
TOKEN_HMAC_SECRET=replace-with-a-different-long-secret

# Optional background services
ENABLE_WORKER=true
ENABLE_HEALTH_MONITOR=true
```

> **Important:** `LUCIS_INDEX_NAME` is the autoload key.  When you point
> the playground at a *different* table, give it a *different* index name
> (and optionally a different storage dir), or Lucis will happily load
> the previously saved index.

---

## 4. Use your own table

**Scenario A — this example's encrypted table** (default `.env`): nothing
to change.

**Scenario B — plain-text table, no encryption:**

```dotenv
TABLE_NAME=products
ID_COLUMN=id
TEXT_COLUMNS=name,description,sku
DATE_COLUMN=created_at
USE_ENCRYPTED_PREPROCESSOR=false
LUCIS_INDEX_NAME=products_idx
```

**Scenario C — table without a date column:**

```dotenv
TABLE_NAME=customers
TEXT_COLUMNS=name,email,phone
DATE_COLUMN=
USE_ENCRYPTED_PREPROCESSOR=false
LUCIS_INDEX_NAME=customers_idx
```

**Scenario D — your own encrypted table:** keep
`USE_ENCRYPTED_PREPROCESSOR=true`, adjust `TEXT_COLUMNS`, set your two
secrets, and — if your ciphertext isn't Fernet — tweak the decrypt step
inside `preprocessor.py` (it's the first function in the file).
Note: rows inserted with *different* secrets are not interoperable —
wipe and reseed when changing secrets.

---

## 5. How the blind index works

Lucis does **not** search ciphertext (ciphertext is unsearchable).
During indexing, Lucis concatenates the row's `TEXT_COLUMNS` with spaces
and hands that string to `preprocessor()`:

```text
MySQL row:  name(Fernet) email(Fernet) number(Fernet) ip(plain) created_at
                │
                ▼  preprocessor() — same function for indexing and querying
   1. try to decrypt each fragment (Fernet)   → plaintext or passthrough
   2. normalize (lowercase; strip @ + . and inner spaces)
   3. char trigrams (n=3)
   4. HMAC-SHA256(token)[:16] — deterministic blind token
                │
                ▼
Lucis inverted index  →  .lcs binaries + SQLite metadata (mmap loading)
```

A plain-text query ("luis hotmail 612") is never valid Fernet, so it
flows through steps 2–4 and produces the *same* blind tokens → match.
The index only ever stores blind tokens; rows are fetched by id and
decrypted **only for display**.

Normalization makes surface forms equivalent:
`luis.aries@example.com` ≡ `luisariesexamplecom`,
`+52 612 169 6226` ≡ `526121696226`, `127.168.192.4` ≡ `1271681924`.

---

## 6. Insert controlled data (`seed_controlled_data.py`)

```bash
python seed_controlled_data.py
```

Inserts 9 leads with stable references (`target-luis-aries`, …) and
**fixed** dates (three are `NULL` → universal shard `9999_99`).
Re-running is safe: duplicates are skipped by reference.

---

## 7. Optional noise (`generate_noise.py`)

```bash
python generate_noise.py --records 100000 --seed 20260801
```

- Deterministic: same seed → same rows (`noise-000000001`, …), so
  re-running only tops up what's missing.
- ~10 % of rows have `created_at = NULL` (universal-shard testing).
- Streams from a generator in batches — millions of rows, bounded RAM.
- Not needed to understand Lucis; it only creates volume.

---

## 8. Run the playground (`playground.py`)

```bash
python playground.py
```

- Loads the saved index — or builds it from the table on first run —
  printing how many documents were loaded/indexed and how long it took
  (local observation, not a benchmark):
  `Index 'encrypted_leads' loaded: 1,009 documents in 0.09s`
- If the table is empty, it tells you exactly which seed script to run.
- Menu: **exit · versions · search (with optional since/until) · add
  lead · stats · health**.
- Worker and health monitor start only if `ENABLE_WORKER` /
  `ENABLE_HEALTH_MONITOR` are `true` — both are clearly marked OPTIONAL
  in the code.

---

## 9. Expected output

Searching `aries`:

```text
2 result(s) in 2.0 ms (shards 75/75):
  1. [0.2174] Aries Meza | ariesmeza@hotmail.com | +526121696226 | 127.168.192.2  (shard: 2026_02)
  2. [0.1429] Aries Lucis | aries.lucis@lucis.dev | +521551998877 | 127.168.192.0  (shard: 9999_99)
```

Queries that find `target-luis-aries` (normalization at work):
`aries` · `Aries Meza` · `ariesmeza` · `hotmail 612` · `hotmail.com` ·
`6121696226` · `+52 612 169 6226`.

Queries that find `target-autos-usados`:
`autos usados` · `autos.usados@hdm.honda.com` · `127.168.192.8`.

---

## 10. Visual walkthrough: Lucis in 3 steps

If you understand examples more easily through images, this walkthrough
shows the complete flow: prepare the data, build or load the index, and
search the encrypted fields.

### Step 1 — Prepare the data

After configuring `.env` and creating the database, in the venv install lucis example ([Check Quickstart](#2-quick-start)) and run the seed scripts:

The first image shows the seed command. The second confirms that the
database contains the example data.

![Seed the controlled data](assets/example_1.png)

![Confirm that the database was updated](assets/example_7.png)

### Step 2 — Build or load the Lucis index

Run the playground:

```bash
python playground.py
```

On the first run, Lucis builds the index from the database, so startup can
take longer. On later runs, Lucis loads the saved index and starts faster.

![Build the Lucis index](assets/example_2.png)

![Load the saved index](assets/example_3.png)

### Step 3 — Search

Use the search option in the playground to search the encrypted fields with
plain text. You can also provide date filters to limit the search to the
relevant temporal shards.

![Search encrypted fields](assets/example_4.png)

![Use date filters](assets/example_5.png)

The final screen shows the playground's resource and health information.
The timings are local observations, not benchmarks.

![View resource and health information](assets/example_6.png)


## 11. Worker & health monitor (optional)

`ENABLE_WORKER=true` starts a Lucis `IndexWorker` that re-syncs the index
when the table changes (interval from `.env`) — insert a lead from the
menu and watch it become searchable.  `ENABLE_HEALTH_MONITOR=true` prints
RAM / latency snapshots on exit.  Both sit *after* the main integration
in `playground.py` and are trivial to disable.  Their numbers are local
observations, **not benchmarks**.

---

## 12. Security & limitations

- Two **independent** secrets: `ENCRYPTION_SECRET` (Fernet, data at rest)
  and `TOKEN_HMAC_SECRET` (blinds index tokens).  Never reuse one for the
  other; never commit them (`.env` is git-ignored).
- The index stores blind tokens, not plaintext — but deterministic HMAC
  **leaks equality** (frequency/dictionary analysis is possible).  This
  example is *not* a complete cryptographic design for arbitrary threat
  models; keys are SHA-256-derived for reproducibility — use a real KDF
  and a KMS/HSM in production.
- Normalization is destructive (great recall, possible collisions).
- Timings printed by the example are local observations, not benchmarks.
- MySQL-oriented (other SQLAlchemy engines plausible, untested here).
- `src/lucis/` is **not** modified — Lucis is consumed as a package.

---

## 13. Cleanup

```sql
-- MySQL
DROP TABLE IF EXISTS leads;          -- or: TRUNCATE TABLE leads;
```

```bash
rm -rf lucis_data                    # index artifacts (.lcs + metadata)
```

Your `.env` stays untouched.  Nothing outside this folder is affected.
