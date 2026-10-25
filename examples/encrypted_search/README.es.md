# Búsqueda Encriptada con Yeny

<p align="left">
  <b>🌐 Language / Idioma:</b> &nbsp;
  <a href="README.md">English</a> &nbsp;|&nbsp;
  <strong>Español</strong>
</p>

> Búsqueda de texto completo sobre columnas MySQL cifradas con Fernet — con ~15 líneas
> de código específico de Yeny. *(Ejemplo reproducible: índice ciego de
> trigramas + HMAC, consultado con texto plano.)*

Este ejemplo demuestra cómo Yeny puede indexar y buscar en una tabla MySQL que
contiene campos cifrados. **La integración completa con Yeny vive en
`playground.py`.** Para entender el ejemplo, solo necesitas leer:

1. **`playground.py`** — apunta Yeny a una tabla, elige columnas, busca.
2. **`preprocessor.py`** — el plug-in opcional que hace que los campos *cifrados*
   sean buscables (índice ciego: trigramas → HMAC determinista).

Los archivos restantes solo preparan o muestran datos:

| archivo | rol |
|---------|-----|
| `database.py` | helper pequeño: `.env`, DDL de la tabla, inserciones, descifrado para visualización |
| `seed_controlled_data.py` | inserta 10 leads fáciles de encontrar (Aries Meza, Real Madrid, …) |
| `generate_noise.py` | opcional: volumen masivo determinista (`--records 100000`) |

¿Prefieres una descripción visual general? Salta al [recorrido visual: Yeny en 3 pasos](#10-recorrido-visual-yeny-en-3-pasos).

---

## 1. La integración completa con Yeny

Esto es todo — copiado de `playground.py`:

```python
from yeny import Yeny
from yeny.config import YenyOptions, TableSource
from preprocessor import preprocessor   # solo para campos cifrados

OPTIONS = YenyOptions(
    storage_dir="./yeny_data",
    memory_limit_mb=512,
)

# Ruta 1 — ya existe un índice guardado → carga automática (mmap, rápido).
yn = Yeny(
    name="encrypted_leads",
    engine="lite",
    preprocessor=preprocessor,
    options=OPTIONS,
)

# Ruta 2 — no hay índice guardado → construirlo directo desde la tabla.
if not yn.is_indexed:
    yn = Yeny.from_table(
        TableSource(
            table="leads",
            connection_url=DB_URL,
            text_columns=["name", "email", "number", "ip"],
            id_column="id",
            date_column="created_at",
        ),
        name="encrypted_leads",
        engine="lite",
        preprocessor=preprocessor,
        options=OPTIONS,
    )

results = yn.search("aries hotmail 612")
```

**Eso es todo el código específico de Yeny que existe.** Todo lo demás en el
ejemplo cifra datos semilla, genera volumen o imprime resultados.

---

## 2. Inicio rápido

Requiere Python 3.10+ y un MySQL 8.x accesible.

**Linux / macOS**

```bash
cd examples/encrypted_search

python -m venv .venv
source .venv/bin/activate
pip install "../..[encrypted-search-example]"

cp .env.example .env        # luego edita DATABASE_URL + secretos
```

**Windows (PowerShell)**

```powershell
cd examples/encrypted_search
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install "../..[encrypted-search-example]"
Copy-Item .env.example .env
```

Crea la base de datos (una sola vez — el ejemplo nunca ejecuta `CREATE DATABASE`):

```sql
CREATE DATABASE yeny_encrypted_search
CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Luego:

```bash
python seed_controlled_data.py      # 10 leads controlados (cifrados)
python generate_noise.py --records 100000 --seed 20260801 # opcional; útil para probar escala
python playground.py                # construye el índice, abre el menú
```

Sin CLI, sin subcomandos, sin instalación de paquetes para el ejemplo en sí —
solo scripts.

---

## 3. Configuración vía `.env`

`.env` es el punto principal de configuración — adapta el playground a otras
tablas **sin tocar código** (las variables de entorno reales siempre tienen
prioridad; solo se lee el archivo `.env` de esta carpeta, nunca uno en la raíz
del repositorio):

```dotenv
DATABASE_URL=mysql+pymysql://yeny_user:change-me@localhost:3306/yeny_encrypted_search

# Mapeo de tabla — apunta esto a TU tabla
TABLE_NAME=leads
ID_COLUMN=id
TEXT_COLUMNS=name,email,number,ip
DATE_COLUMN=created_at        # déjalo vacío para desactivar la fragmentación temporal

# Yeny
YENY_INDEX_NAME=encrypted_leads    # ¡cámbialo por cada tabla! (clave de autocarga)
YENY_ENGINE=lite
YENY_MEMORY_LIMIT_MB=512
YENY_STORAGE_DIR=./yeny_data

# ¿Tabla en texto plano? → no se necesita preprocesador cifrado
USE_ENCRYPTED_PREPROCESSOR=true

# Dos secretos INDEPENDIENTES (solo se usan cuando el preprocesador está activo)
ENCRYPTION_SECRET=replace-with-a-long-example-secret
TOKEN_HMAC_SECRET=replace-with-a-different-long-secret

# Servicios opcionales en segundo plano
ENABLE_WORKER=true
ENABLE_HEALTH_MONITOR=true
```

> **Importante:** `YENY_INDEX_NAME` es la clave de carga automática. Cuando apuntes
> el playground a una tabla *diferente*, asígnale un nombre de índice *diferente*
> (y opcionalmente un directorio de almacenamiento distinto), o Yeny cargará
> gustosamente el índice previamente guardado.

---

## 4. Usa tu propia tabla

**Escenario A — la tabla cifrada de este ejemplo** (`.env` por defecto): nada
que cambiar.

**Escenario B — tabla en texto plano, sin cifrado:**

```dotenv
TABLE_NAME=products
ID_COLUMN=id
TEXT_COLUMNS=name,description,sku
DATE_COLUMN=created_at
USE_ENCRYPTED_PREPROCESSOR=false
YENY_INDEX_NAME=products_idx
```

**Escenario C — tabla sin columna de fecha:**

```dotenv
TABLE_NAME=customers
TEXT_COLUMNS=name,email,phone
DATE_COLUMN=
USE_ENCRYPTED_PREPROCESSOR=false
YENY_INDEX_NAME=customers_idx
```

**Escenario D — tu propia tabla cifrada:** mantén
`USE_ENCRYPTED_PREPROCESSOR=true`, ajusta `TEXT_COLUMNS`, define tus dos
secretos y — si tu texto cifrado no es Fernet — ajusta el paso de descifrado
dentro de `preprocessor.py` (es la primera función del archivo).
Nota: las filas insertadas con secretos *diferentes* no son interoperables —
borra y vuelve a sembrar al cambiar los secretos.

---

## 5. Cómo funciona el índice ciego

Yeny **no** busca sobre texto cifrado (el texto cifrado no es buscable).
Durante la indexación, Yeny concatena las columnas de `TEXT_COLUMNS` de la fila con espacios
y entrega esa cadena a `preprocessor()`:

```text
Fila MySQL:  name(Fernet) email(Fernet) number(Fernet) ip(plano) created_at
                 │
                 ▼  preprocessor() — la misma función para indexar y consultar
    1. intentar descifrar cada fragmento (Fernet)   → texto plano o passthrough
    2. normalizar (minúsculas; eliminar @ + . y espacios internos)
    3. trigramas de caracteres (n=3)
    4. HMAC-SHA256(token)[:16] — token ciego determinista
                 │
                 ▼
Índice invertido de Yeny  →  binarios .yny + metadatos SQLite (carga por mmap)
```

Una consulta en texto plano ("aries hotmail 612") nunca es Fernet válido, por lo que
fluye a través de los pasos 2–4 y produce los *mismos* tokens ciegos → coincidencia.
El índice solo almacena tokens ciegos; las filas se obtienen por id y se
descifran **únicamente para mostrarlas en pantalla**.

La normalización hace que las formas superficiales sean equivalentes:
`ariesmeza@hotmail.com` ≡ `ariesmezahotmailcom`,
`+52 612 169 6226` ≡ `526121696226`, `127.168.192.4` ≡ `1271681924`.

---

## 6. Insertar datos controlados (`seed_controlled_data.py`)

```bash
python seed_controlled_data.py
```

Inserta 10 leads con referencias estables (`target-aries-meza`, …) y
fechas **fijas** (tres son `NULL` → shard universal `9999_99`).
Reejecutarlo es seguro: los duplicados se omiten por referencia.

---

## 7. Ruido opcional (`generate_noise.py`)

```bash
python generate_noise.py --records 100000 --seed 20260801
```

- Determinista: misma semilla → mismas filas (`noise-000000001`, …), por lo que
  reejecutar solo completa lo que falte.
- ~10 % de las filas tienen `created_at = NULL` (pruebas del shard universal).
- Emite desde un generador en lotes — millones de filas con memoria RAM acotada.
- No es necesario para entender Yeny; solo crea volumen.

---

## 8. Ejecutar el playground (`playground.py`)

```bash
python playground.py
```

- Carga el índice guardado — o lo construye desde la tabla en la primera ejecución —,
  imprimiendo cuántos documentos se cargaron/indexaron y cuánto tiempo tomó
  (observación local, no un benchmark):
  `Index 'encrypted_leads' loaded: 1,009 documents in 0.09s`
- Si la tabla está vacía, te indica exactamente qué script semilla ejecutar.
- Menú: **exit · versions · search (con since/until opcional) · add lead · stats · health**.
- El worker y el monitor de salud se inician solo si `ENABLE_WORKER` /
  `ENABLE_HEALTH_MONITOR` son `true` — ambos están claramente marcados como OPCIONALES
  en el código.

---

## 9. Salida esperada

Buscando `aries`:

```text
2 result(s) in 2.0 ms (shards 75/75):
  1. [0.2174] Aries Meza | ariesmeza@hotmail.com | +526121696226 | 127.168.192.2  (shard: 2026_02)
  2. [0.1429] Aries Yeny | aries.yeny@yeny.dev | +521551998877 | 127.168.192.0  (shard: 9999_99)
```

Consultas que encuentran `target-aries-meza` (normalización en acción):
`aries` · `Aries Meza` · `ariesmeza` · `hotmail 612` · `hotmail.com` ·
`6121696226` · `+52 612 169 6226`.

Consultas que encuentran `target-autos-usados`:
`autos usados` · `autos.usados@hdm.honda.com` · `127.168.192.8`.

---

## 10. Recorrido visual: Yeny en 3 pasos

Si comprendes los ejemplos más fácilmente a través de imágenes, este recorrido
muestra el flujo completo: preparar los datos, construir o cargar el índice y
buscar en los campos cifrados.

### Paso 1 — Preparar los datos

Tras configurar `.env` y crear la base de datos, en el venv instala el ejemplo de yeny ([Consulta Inicio rápido](#2-inicio-rápido)) y ejecuta los scripts semilla:

La primera imagen muestra el comando seed. La segunda confirma que la
base de datos contiene los datos de ejemplo.

![Sembrar los datos controlados](assets/example_1.png)

![Confirmar que la base de datos fue actualizada](assets/example_7.png)

### Paso 2 — Construir o cargar el índice de Yeny

Ejecuta el playground:

```bash
python playground.py
```

En la primera ejecución, Yeny construye el índice desde la base de datos, por lo que el inicio puede
tardar más. En ejecuciones posteriores, Yeny carga el índice guardado e inicia más rápido.

![Construir el índice de Yeny](assets/example_2.png)

![Cargar el índice guardado](assets/example_3.png)

### Paso 3 — Buscar

Usa la opción de búsqueda en el playground para buscar en los campos cifrados con
texto plano. También puedes proporcionar filtros de fecha para limitar la búsqueda a los
shards temporales relevantes.

![Buscar campos cifrados](assets/example_4.png)

![Usar filtros de fecha](assets/example_5.png)

La pantalla final muestra la información de recursos y salud del playground.
Los tiempos son observaciones locales, no benchmarks.

![Ver información de recursos y salud](assets/example_6.png)


## 11. Worker y monitor de salud (opcional)

`ENABLE_WORKER=true` inicia un `IndexWorker` de Yeny que resincroniza el índice
cuando la tabla cambia (intervalo desde `.env`) — inserta un lead desde el
menú y observa cómo se vuelve buscable. `ENABLE_HEALTH_MONITOR=true` imprime
instantáneas de RAM / latencia al salir. Ambos se sitúan *después* de la integración principal
en `playground.py` y son triviales de desactivar. Sus números son observaciones locales,
**no benchmarks**.

---

## 12. Seguridad y limitaciones

- Dos secretos **independientes**: `ENCRYPTION_SECRET` (Fernet, datos en reposo)
  y `TOKEN_HMAC_SECRET` (ciega los tokens del índice). Nunca reutilices uno para el
  otro; nunca los subas al repositorio (`.env` está ignorado en git).
- El índice almacena tokens ciegos, no texto plano — pero el HMAC determinista
  **filtra igualdad** (el análisis de frecuencia o de diccionario es posible). Este
  ejemplo *no* es un diseño criptográfico completo para modelos de amenazas
  arbitrarios; las claves se derivan con SHA-256 por reproducibilidad — usa un KDF
  real y un KMS/HSM en producción.
- La normalización es destructiva (gran exhaustividad, posibles colisiones).
- Los tiempos impresos por el ejemplo son observaciones locales, no benchmarks.
- Orientado a MySQL (otros motores de SQLAlchemy son plausibles, pero no están probados aquí).
- `src/yeny/` **no** se modifica — Yeny se consume como paquete.

---

## 13. Limpieza

```sql
-- MySQL
DROP TABLE IF EXISTS leads;          -- o: TRUNCATE TABLE leads;
```

```bash
rm -rf yeny_data                    # artefactos del índice (.yny + metadatos)
```

Tu `.env` permanece intacto. Nada fuera de esta carpeta se ve afectado.

