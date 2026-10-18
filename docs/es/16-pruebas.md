# Pruebas

Esta guía explica cómo ejecutar la suite de pruebas de Yeny desde una copia local del repositorio.

Si acabas de clonar el proyecto, esta es la página que debes leer primero para validar que todo funciona localmente.

## Estructura de pruebas

```text
tests/
├── conftest.py
├── test_utils/
├── test_core/
├── test_persistence/
└── test_integration/
```

## Qué cubre cada carpeta

- `tests/test_utils`: tokenización, compactación, serialización, paralelización y mmap.
- `tests/test_core`: comportamiento de `CoreEngine` y `LiteEngine`.
- `tests/test_persistence`: guardado, carga, versionado y rollback sobre SQLite.
- `tests/test_integration`: API pública de `Yeny` de extremo a extremo.

## Preparación

Instala las dependencias de test en tu entorno virtual:

```bash
python -m pip install pytest pytest-cov pytest-mock
```

Si quieres ejecutar los tests con la misma versión del intérprete usada por el proyecto, activa primero tu entorno virtual o conda y luego instala ahí las dependencias.

Si vas a editar el proyecto mientras pruebas, instala el paquete en modo editable:

```bash
python -m pip install -e .
```

## Ejecutar todos los tests

```bash
python -m pytest
```

Este comando ejecuta toda la suite bajo `tests/`.

## Ejecutar por área

```bash
# Utilidades
python -m pytest tests/test_utils -v --tb=short

# Motores de búsqueda
python -m pytest tests/test_core -v --tb=short

# Persistencia y rollback
python -m pytest tests/test_persistence -v --tb=short

# Integración de la API pública
python -m pytest tests/test_integration -v --tb=short
```

Si solo quieres validar el nuevo flujo de persistencia y rollback, ejecuta:

```bash
python -m pytest tests/test_persistence -v --tb=short
```

## Ejecutar por marcador

Yeny usa marcadores para separar tests rápidos de integración:

```bash
python -m pytest -m unit
python -m pytest -m integration
```

## Coverage

```bash
python -m pytest --cov=src/yeny --cov-report=html
```

Esto genera un reporte HTML con el detalle de cobertura.

Para ver un resumen rápido en consola:

```bash
python -m pytest --cov=src/yeny --cov-report=term-missing
```

## Qué probar primero

Si acabas de clonar el repo, este es el orden más seguro:

1. `python -m pytest tests/test_utils -v --tb=short`
2. `python -m pytest tests/test_core -v --tb=short`
3. `python -m pytest tests/test_persistence -v --tb=short`
4. `python -m pytest tests/test_integration -v --tb=short`

Si estás corrigiendo un fallo concreto, vuelve a ejecutar solo la carpeta afectada antes de correr la suite completa.

## Notas prácticas

- Los tests de persistencia usan bases SQLite temporales.
- Los tests de integración usan datos pequeños y no requieren servicios externos.
- Si un test falla por un archivo temporal, borra el directorio generado por `tmp_path` y vuelve a ejecutar.
- Los tests de rollback asumen que el backend de SQLite mantiene versiones históricas del mismo índice.

## Cómo ampliar la suite

- Añade casos de borde en `tests/test_utils` para funciones puras.
- Usa `tests/test_persistence` para save/load, versionado y rollback.
- Usa `tests/test_integration` para validar la API pública de `Yeny`.

## Flujo recomendado para contribuidores

1. Ejecuta los tests de la carpeta que vas a tocar.
2. Corrige el fallo más cercano al comportamiento esperado.
3. Vuelve a correr la carpeta afectada.
4. Ejecuta la suite completa antes de abrir un PR o preparar un release.