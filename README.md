# Cuba News (RSS de Periódico Cubano)

Aplicación web sencilla (FastAPI + SQLite + Jinja2) que muestra las noticias más recientes de Cuba usando **únicamente** el RSS oficial de Periódico Cubano:

- https://www.periodicocubano.com/feed/

No usa IA, OpenAI ni APIs de pago.

## Requisitos

- Python 3.10+ (recomendado)

## Instalación

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Variables de entorno

Copia el ejemplo y ajusta si lo necesitas:

```bash
cp .env.example .env
```

Variables:

- `DATABASE_URL` (por defecto: `sqlite:///./news.db`)

## Ejecutar localmente

Comando esperado:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 10000
```

Luego abre:

- http://localhost:10000/

## Cómo funciona la actualización automática (scheduler)

- En el arranque:
  - Se crean las tablas en SQLite si no existen.
  - Si la base de datos está vacía, se hace una **carga inicial** desde el RSS.
- En segundo plano:
  - Un scheduler (APScheduler) consulta el RSS **cada 30 minutos**.
  - Inserta solo noticias nuevas (la URL es única, evita duplicados).

## Estructura del proyecto

- `app/main.py`: inicializa FastAPI, monta estáticos, arranque/parada del scheduler.
- `app/routes/news.py`: página principal (búsqueda + paginación).
- `app/services/rss_service.py`: descarga/parseo del RSS y guardado en DB.
- `app/services/scheduler.py`: job cada 30 minutos.
- `app/database/database.py`: conexión a SQLite y `init_db()`.
- `app/models/news.py`: modelo SQLAlchemy `News`.
- `app/templates/index.html`: template Jinja2.
- `app/static/css/style.css`: estilos.

## Despliegue en Render (gratis)

1. Crea un **Web Service** desde este repo.
2. Runtime: **Python**.
3. Build command:

   ```bash
   pip install -r requirements.txt
   ```

4. Start command:

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 10000
   ```

5. SQLite persistente (recomendado):
   - En Render, añade un **Persistent Disk** (por ejemplo montado en `/var/data`).
   - Configura la variable de entorno:

     ```bash
     DATABASE_URL=sqlite:////var/data/news.db
     ```

Sin disco persistente, Render puede borrar el archivo SQLite en despliegues/reinicios.
