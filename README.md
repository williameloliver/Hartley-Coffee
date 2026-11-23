# Hartley Coffee — aplicación web con base de datos relacional

Esta versión conserva la interfaz y la lógica de Hartley Coffee, pero sustituye `localStorage` como almacenamiento principal por una API Flask conectada a una base de datos relacional.

## Arquitectura

- **Frontend:** HTML, CSS y JavaScript (interfaz original Hartley Coffee).
- **Backend:** Python + Flask (API REST).
- **ORM:** Flask-SQLAlchemy.
- **Base de datos local:** SQLite.
- **Base de datos de producción:** PostgreSQL mediante `DATABASE_URL`.
- **Servidor de producción:** Gunicorn (compatible con Render).

## Modelo relacional

| Tabla | Propósito |
|---|---|
| `products` | Catálogo de cafés, extras y combos |
| `combo_components` | Relación entre un combo y sus productos componentes |
| `sales` | Ventas registradas, precio histórico, cantidad y fecha |
| `expenses` | Gastos, categoría, descripción y monto |
| `inventory` | Estado de inventario y notas de la jornada |
| `extra_stock` | Stock inicial/final de cada producto extra |

Relaciones principales:
- `sales.product_id` → `products.id`
- `combo_components.combo_id` → `products.id`
- `combo_components.component_product_id` → `products.id`
- `extra_stock.product_id` → `products.id`

## Ejecutar localmente

Requiere Python 3.10 o superior.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
python app.py
```

Abrir: http://127.0.0.1:5000

Por defecto, SQLite crea `hartley_coffee.db` automáticamente en el directorio de ejecución.

## API para demostrar la integración

- `GET /api/state` — lee el estado desde las tablas relacionales.
- `PUT /api/state` — valida y persiste el estado mediante una transacción.
- `GET /api/schema` — informa las tablas utilizadas y el motor activo.
- `GET /health` — verifica que el servidor y la conexión a la base respondan.

La interfaz consulta `GET /api/state` al iniciar. Cuando se registra una venta, gasto, producto o cambio de inventario, envía el estado actualizado al backend mediante `PUT /api/state`. El backend distribuye los datos entre las tablas relacionales; no guarda un único JSON como registro de negocio.

## Despliegue en Render + PostgreSQL

1. Sube esta carpeta a un repositorio GitHub.
2. Crea una base PostgreSQL en un proveedor administrado (por ejemplo, Neon o Render).
3. Copia la cadena de conexión PostgreSQL (`DATABASE_URL`).
4. En Render crea un **Web Service** conectado al repositorio.
5. Configura:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
   - Environment Variable: `DATABASE_URL` = cadena de conexión PostgreSQL.
6. Despliega y abre la URL pública.
7. Verifica `/health` y `/api/schema`.

**Importante:** no uses SQLite en un hosting efímero para producción, porque el archivo puede perderse al reiniciar o redeplegar. Usa PostgreSQL administrado y mantén `DATABASE_URL` como variable privada del servidor.

## Pruebas rápidas

Con la aplicación ejecutándose:

```bash
curl http://127.0.0.1:5000/health
curl http://127.0.0.1:5000/api/schema
curl http://127.0.0.1:5000/api/state
```

Luego registra un producto y una venta desde la interfaz y vuelve a consultar `/api/state`. También puedes revisar las tablas desde el panel SQL del proveedor PostgreSQL.

## Seguridad y alcance académico

- Las consultas y escrituras se realizan mediante SQLAlchemy, evitando concatenar SQL con datos del usuario.
- El servidor valida la estructura básica de los datos y las referencias entre productos, combos y ventas.
- Las escrituras se confirman en una transacción; ante un error se ejecuta `rollback`.
- La conexión de producción se configura mediante una variable de entorno y no se publica en el frontend.
- Esta entrega es una demostración académica de gestión de cafetería. Antes de un uso comercial real, agrega autenticación, autorización por roles, protección CSRF, límites de solicitudes, migraciones de esquema y copias de seguridad.

## Nota sobre los datos de demostración

La aplicación inicia con productos de ejemplo cuando la base está vacía. Las ventas, gastos e inventario que registres después se guardan en la base de datos del servidor y podrán consultarse desde otro dispositivo que abra la misma URL.
