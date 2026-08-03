"""Utility script: insert the controlled, easy-to-find target leads.

    python seed_controlled_data.py

These 10 records (Luis Aries, Aries Lucis, Cristiano Ronaldo, Real Madrid,
Leo Messi, Vinicus Junior, My Chemical Romance, Autos Usados, Admin Publica,
and dev service) exist so you always know **what a search should find**.
Each one carries a stable ``reference`` and a fixed date (or ``None`` →
``NULL`` → universal shard), which keeps the whole example reproducible.

Sensitive fields (name/email/number) are encrypted before they touch the
database; re-running skips duplicates by reference.  This file is small
on purpose — it is auxiliary tooling, not part of the Lucis lesson.
"""
from datetime import datetime

import database

TARGET_LEADS: list[dict] = [
    {
        "reference": "target-aries-meza",
        "name": "Aries Meza",
        "email": "ariesmeza@hotmail.com",
        "number": "+526121696226",
        "ip": "127.168.192.2",
        "created_at": datetime(2026, 2, 19),
    },
    {
        "reference": "target-aries-lucis",
        "name": "Aries Lucis",
        "email": "aries.lucis@lucis.dev",
        "number": "+521551998877",
        "ip": "127.168.192.0",
        "created_at": None,  # → universal shard (9999_99)
    },
    {
        "reference": "target-cristiano-ronaldo",
        "name": "Cristiano Ronaldo",
        "email": "cristiano@futbol.com",
        "number": "+5215587654321",
        "ip": "127.168.192.4",
        "created_at": datetime(2025, 12, 21),
    },
    {
        "reference": "target-real-madrid",
        "name": "Real Madrid",
        "email": "real.madrid@gmail.com",
        "number": "+34912345678",
        "ip": "127.168.192.5",
        "created_at": datetime(2026, 1, 27),
    },
    {
        "reference": "target-leo-messi",
        "name": "Leo Messi",
        "email": "leo.messi@futbol.com",
        "number": "+5215511122233",
        "ip": "127.168.192.9",
        "created_at": None,  # → universal shard (9999_99)
    },
    {
        "reference": "target-vinicus-junior",
        "name": "Vinicus Junior",
        "email": "vinicus.junior@futbol.com",
        "number": "+441234567890",
        "ip": "127.168.192.3",
        "created_at": None,  # → universal shard (9999_99)
    },
    {
        "reference": "target-mcr",
        "name": "My Chemical Romance",
        "email": "mychemicalromance@live.com",
        "number": "+441234000111",
        "ip": "127.168.192.7",
        "created_at": datetime(2026, 1, 15),
    },
    {
        "reference": "target-autos-usados",
        "name": "Autos Usados",
        "email": "autos.usados@hdm.honda.com",
        "number": "+521553332211",
        "ip": "127.168.192.8",
        "created_at": datetime(2025, 12, 19),
    },
    {
        "reference": "target-admin-publica",
        "name": "Admin Publica",
        "email": "administarcion.publica@outlook.com",
        "number": "+521559001122",
        "ip": "127.168.192.6",
        "created_at": datetime(2026, 2, 28),
    },
    {
        "reference": "target-dev-service",
        "name": "dev service",
        "email": "devs@toolsmx.com",
        "number": "+521559001133",
        "ip": "127.168.192.7",
        "created_at": datetime(2026, 2, 28),
        },
]


def main():
    database.load_env()
    database.ensure_table()
    inserted, skipped = database.insert_leads(TARGET_LEADS)
    print(
        f"Controlled data ready: {inserted} inserted, {skipped} already existed "
        f"(table now holds {database.count_leads()} rows)."
    )
    print("Try searching:  luis aries | hotmail 612 | aries lucis | 1271681924")


if __name__ == "__main__":
    main()
