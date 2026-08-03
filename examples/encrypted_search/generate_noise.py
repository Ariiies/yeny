"""Utility script: fill the table with deterministic synthetic leads ("noise").

    python generate_noise.py --records 100000 --seed 20260801

The noise surrounds the controlled targets with realistic volume so the
demo behaves like a real table.  Every value comes from a local
``random.Random(seed)`` — the same ``(records, seed)`` pair always
produces exactly the same rows, so re-running just tops up what is
missing (duplicates are skipped by reference).

~10% of rows get ``created_at = NULL`` to exercise Lucis' universal
shard.  This file is NOT needed to understand Lucis — it only creates
bulk data.
"""
import argparse
import os
import random
import time
from datetime import datetime, timedelta

import database

# ── Catalogues (kept rich on purpose: variety makes the demo realistic) ─────

_NAMES = [
    "luis", "ramon", "ariel", "pedro", "maria", "juan", "ana", "carlos",
    "sandra", "sofia", "diego", "laura", "miguel", "pablo", "isabel", "manuel",
    "rosa", "alberto", "elena", "javier", "antonio", "beatriz", "martin", "sergio",
    "adrian", "paula", "esteban", "nicolas", "camila", "andres", "gloria", "federico",
    "marta", "emilio", "teresa", "alicia", "roberto", "francisco", "olga", "ruben",
    "raul", "ismael", "julia", "claudia", "ignacio", "valentina", "lola", "valeria",
    "santiago", "fernando", "victor", "alex", "camilo", "marcela", "monica", "gabriel",
    "adriana", "lorena", "cristian", "mauricio", "julian", "nuria", "micaela",
    "alejandro", "marina", "sebastian", "natalia", "fabiola", "german", "jimena",
    "ramona", "ignacia", "yolanda", "oscar", "pilar", "rocio", "jose", "susana",
    "andrea", "hector", "david", "emilia", "omar", "cesar", "lina", "rodrigo",
    "cristina", "henry", "zoe", "mia", "liam", "oliver", "noah", "emma", "amelia",
    "isabella", "lucas", "eva", "ivan", "ximena", "renata", "edmundo", "leonor",
    "enrique", "marisol", "graciela", "patricio", "daniela", "tomas", "veronica",
    "gerardo", "arnaldo", "silvana", "celeste", "erika", "hugo",
    "consuelo", "rodolfo", "esperanza", "jorge", "dolores", "alfredo", "miriam",
    "augusto", "rebeca", "ernesto", "guadalupe", "rafael", "perpetua", "joaquin",
    "florencia", "armando", "concepcion", "leandro", "macarena", "gonzalo", "paloma",
    "ezequiel", "eugenia", "horacio", "marcelo", "cintia", "nestor",
    "ariadna", "dario", "vanesa", "facundo", "noelia", "matias", "romina",
    "belen", "carla", "diana", "edith", "fatima", "gisela", "hilda", "irene",
    "jacinta", "karla", "libertad", "mariana", "nadia", "ofelia", "prisca", "quirina",
    "rafaela", "soledad", "talia", "ursula", "wendy", "yareli",
    "zaira", "abigail", "blanca", "celia", "delia", "estela", "fernanda", "griselda",
    "hortensia", "iliana", "josefina", "karina", "liliana", "magdalena", "norma",
    "osvaldo", "perla", "quintina", "sabrina", "tatiana", "ulises", "viviana",
    "wilmer", "yadira", "zoraida", "aldair", "brayan", "cleiver", "deison", "eerik",
    "farid", "gilberto", "humberto", "ivo", "jenifer", "kenji", "leila", "mauro",
    "nacho", "oriol", "pau", "quintin", "remi", "sven", "thiago", "ulf", "vlad",
    "waldo", "xavi", "yago", "zaid", "amet", "bora", "cemal", "demir", "emre",
    "ferhat", "gokhan", "haluk", "ibrahim", "jamal", "kadir", "levent", "mehmet",
    "nabil", "polat", "rafiq", "salim", "tariq", "umar", "yusuf", "zein",
    "abebe", "bekele", "chidi", "desmond", "ekene", "femi", "gbenga", "habib",
    "ifeoma", "jide", "kunle", "leke", "musa", "ngozi", "obiora", "pius", "rotimi",
    "sade", "taiwo", "uche", "wole", "yemi", "zara", "akira", "daiki", "fumio",
    "goro", "haruki", "isamu", "jiro", "kazuo", "makoto", "naoto", "osamu",
    "ryoji", "satoshi", "takeshi", "yuichi", "yuki", "hiroshi", "keiko", "mizuki",
    "ananya", "bharat", "chandra", "deepak", "firoz", "gaurav", "hitesh", "indira",
    "jayesh", "kavya", "lakshmi", "manish", "nisha", "priya", "rahul", "sunita",
    "vikram", "yash", "amara", "caleb", "finn", "grace", "hunter",
    "jade", "kai", "leo", "maya", "nate", "paige", "quinn", "riley", "sawyer",
    "tyler", "uma", "vince", "willow", "xena", "yara", "zane",
]

_LASTNAMES = [
    "garcia", "valdez", "perez", "vargas", "hernandez", "picasso", "cervon",
    "slim", "valencia", "allen", "rodriguez", "gonzalez", "martinez", "lopez",
    "sanchez", "ramirez", "dominguez", "guerra", "mendoza", "romero", "silva",
    "castillo", "cortez", "prieto", "santos", "ortiz", "suarez", "munoz",
    "rios", "marin", "arias", "carrillo", "fernandez", "avila", "contreras",
    "flores", "ferrer", "cabrera", "medina", "pineda", "delgado", "camacho",
    "ibanez", "salazar", "rosales", "noguera", "mora", "trevino", "soto",
    "tapia", "aguilar", "herrera", "montes", "carrasco", "zapata", "cordero",
    "villanueva", "merino", "beltran", "marquez", "barrera", "nunez", "gallo",
    "ortega", "santana", "sierra", "ibarra", "palacios", "quintero", "salinas",
    "salcedo", "tolentino", "urbina", "valle", "yanez", "zuniga", "arriaga",
    "blanco", "diaz", "espinoza", "fuentes", "granado", "izquierdo", "jasper",
    "khan", "liu", "nguyen", "patel", "singh", "okonkwo", "nakamura", "okafor",
    "petrov", "volkov", "muller", "bauer", "hoffmann", "novak", "fischer",
    "andersson", "johansson", "lindqvist", "persson", "nilsson", "eriksson",
    "dupont", "morin", "girard", "bonnet", "dubois", "lefevre",
    "rossi", "ferrari", "ricci", "conti", "bianchi", "esposito", "greco",
    "oliveira", "costa", "ferreira", "alves", "carvalho",
    "lima", "souza", "nascimento", "azevedo", "barbosa", "melo", "cavalcanti",
    "morales", "reyes", "ramos", "paredes", "velarde",
    "trujillo", "saavedra", "covarrubias", "palomino", "tarazona", "huaman",
    "acosta", "bermudez", "cano", "duarte", "escalante", "figueroa", "gallego",
    "hidalgo", "infante", "juarez", "lara", "macias", "navarrete", "ocampo",
    "pacheco", "quiroga", "rendon", "sepulveda", "tejada", "ugarte", "vega",
    "zambrano", "acevedo", "bustos", "cifuentes", "davila", "escalona", "franco",
    "guevara", "hoyos", "jaramillo", "lagos", "montoya", "naranjo", "ojeda",
    "pulido", "quispe", "rojas", "serrano", "terrones", "uribe", "vergara",
    "zamora", "arango", "barragan", "cuadros", "enriquez", "gallardo", "iglesias",
    "lozano", "maldonado", "narvaez", "osorio", "pena", "rengifo", "solano",
    "triana", "valbuena", "zuluaga", "albrecht", "bergmann", "cunha", "diniz",
    "fonseca", "guimaraes", "lacerda", "macedo", "nobre", "pires", "queiroz",
    "ribeiro", "tavares", "ventura", "xavier", "yunes", "abreu", "branco",
    "cardoso", "dantas", "evangelista", "gomes", "leal", "miranda", "neto",
    "porto", "queiroga", "rego", "saraiva", "teixeira", "vasconcellos",
    "yamamoto", "suzuki", "tanaka", "watanabe", "ito", "kobayashi", "saito",
    "kato", "yoshida", "yamada", "sasaki", "inoue", "kimura", "hayashi",
    "shimizu", "yamazaki", "mori", "abe", "ikeda", "hashimoto",
    "ahmed", "ali", "hassan", "hussein", "ismail", "karim",
    "mahmoud", "mustafa", "rahman", "said", "sharif", "yilmaz",
    "aydin", "celik", "demir", "kaya", "arslan", "sahin", "ozturk",
    "sharma", "verma", "joshi", "tiwari", "mishra", "shukla", "pandey",
    "gupta", "kapoor", "malhotra", "mehra", "nair", "iyer", "pillai",
    "smith", "johnson", "williams", "brown", "jones", "davis", "miller",
    "wilson", "moore", "taylor", "anderson", "thomas", "jackson", "white",
    "harris", "martin", "thompson", "robinson", "clark", "lewis",
    "kowalski", "nowak", "wisniewski", "wojcik", "kowalczyk", "kaminski",
    "adamczyk", "dudek", "pawlak", "malinowski", "krawczyk", "wieczorek",
    "ionescu", "popescu", "moldovan", "constantin", "dumitru", "stoica",
    "nkosi", "dlamini", "khumalo", "zulu", "mthembu", "ndlovu", "mokoena",
    "mensah", "asante", "boateng", "owusu", "acheampong", "amoah", "frimpong",
]

_DOMAINS = [
    "gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "protonmail.com",
    "icloud.com", "mail.com", "lucis.dev", "mycompany.com", "startup.io",
    "company.co", "corp.net", "webmail.co", "fastmail.com", "zoho.com",
    "aol.com", "inbox.com", "yandex.com", "hushmail.com", "gmx.com",
    "tutanota.com", "mail.ru", "qq.com", "163.com", "aliyun.com",
    "posteo.de", "seznam.cz", "freenet.de", "bigpond.com",
    "me.com", "bellsouth.net", "earthlink.net", "virgilio.it", "libero.it",
    "orange.fr", "wanadoo.fr", "btinternet.com", "att.net", "verizon.net",
    "protonmail.ch", "mailbox.org",
    "techie.com", "engineer.com", "consultant.com", "programmer.net",
    "coder.dev", "admin.net", "root.dev", "sysadmin.co",
    "agency.co", "studio.io", "design.co", "creative.net", "brand.co", "marketing.io",
    "salesforce.com", "hubspot.com", "mailchimp.com", "zendesk.com", "freshdesk.com",
    "noreply.com", "no-reply.com", "example.com", "test.com", "demo.com", "sample.com",
]

_COUNTRY_CODES = ["+1", "+44", "+34", "+52", "+521", "+91", "+39", "+49", "+33", "+55"]

_DATE_START = datetime(2020, 1, 1)
_DATE_END = datetime(2026, 2, 28)


# ── Field generators (all take the RNG explicitly — global random untouched) ─


def _num_suffix(rng):
    style = rng.choice(["short", "medium", "long", "year", "none"])
    if style == "short":
        return str(rng.randint(1, 99))
    if style == "medium":
        return str(rng.randint(100, 9999))
    if style == "long":
        return str(rng.randint(10000, 999999))
    if style == "year":
        return str(rng.randint(1970, 2005))
    return ""


def random_name(rng):
    first = rng.choice(_NAMES).title()
    last = rng.choice(_LASTNAMES).title()
    if rng.random() < 0.3:
        return f"{first} {rng.choice(_NAMES).title()} {last}"
    return f"{first} {last}"


def random_email(rng):
    name, last = rng.choice(_NAMES), rng.choice(_LASTNAMES)
    sep, num, initial = rng.choice([".", "_", "-", ""]), _num_suffix(rng), name[0]
    template = rng.randint(0, 5)
    user = [
        f"{name}{sep}{last}{num}",
        f"{last}{sep}{name}{num}",
        f"{initial}{sep}{last}{num}",
        f"{name}{sep}{initial}{num}",
        f"{name}{num}",
        f"{last}{num}",
    ][template]
    return f"{user}@{rng.choice(_DOMAINS)}"


def random_phone(rng):
    digits = "".join(str(rng.randint(0, 9)) for _ in range(10))
    return f"{rng.choice(_COUNTRY_CODES)}{digits}"


def random_ip(rng):
    return (
        f"{rng.randint(1, 254)}.{rng.randint(0, 255)}."
        f"{rng.randint(0, 255)}.{rng.randint(1, 254)}"
    )


def random_date(rng):
    delta = _DATE_END - _DATE_START
    return _DATE_START + timedelta(days=rng.randrange(delta.days))


# ── Row generator (lazy — streams millions of rows with bounded RAM) ─────────


def generate(count, seed, null_date_ratio=0.10):
    """Yield ``count`` deterministic row dicts (noise-000000001, …)."""
    rng = random.Random(seed)
    for i in range(1, count + 1):
        yield {
            "reference": f"noise-{i:09d}",
            "name": random_name(rng),
            "email": random_email(rng),
            "number": random_phone(rng),
            "ip": random_ip(rng),
            "created_at": (
                random_date(rng) if rng.random() > null_date_ratio else None
            ),
        }


# ── Script entry point ────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Insert deterministic synthetic leads into the example table."
    )
    parser.add_argument("--records", type=int, default=100_000,
                        help="how many noise rows to generate (default: 100000)")
    parser.add_argument("--seed", type=int, default=None,
                        help="RNG seed (default: RANDOM_SEED from .env)")
    parser.add_argument("--batch-size", type=int, default=None,
                        help="rows per INSERT batch (default: BATCH_SIZE from .env)")
    args = parser.parse_args()

    database.load_env()
    seed = args.seed if args.seed is not None else int(os.getenv("RANDOM_SEED", "20260801"))
    batch_size = args.batch_size or int(os.getenv("BATCH_SIZE", "1000"))

    database.ensure_table()

    step = max(batch_size * 20, 10_000)

    def report(inserted, skipped):
        done = inserted + skipped
        if done % step < batch_size or done == args.records:
            print(f"  {done:>10,} / {args.records:,} rows ({done / args.records * 100:5.1f}%)")

    print(f"Generating {args.records:,} noise leads (seed={seed})…")
    start = time.perf_counter()
    inserted, skipped = database.insert_leads(
        generate(args.records, seed), batch_size=batch_size, progress=report
    )
    elapsed = time.perf_counter() - start
    print(
        f"Done: {inserted:,} inserted, {skipped:,} already existed, in {elapsed:.1f}s "
        f"(table now holds {database.count_leads():,} rows)."
    )
    print("Rebuild the index (restart playground.py) to search the new rows.")


if __name__ == "__main__":
    main()
