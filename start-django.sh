#!/usr/bin/env sh
set -e

# switch into the Django project root
cd /app/src

# Run migrations
echo "→ Applying migrations…"
uv run manage.py migrate

#    - $HOST      : container network interface (default 0.0.0.0)
#    - $PORT      : container port       (default 8000)
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8000}

echo "→ Django running inside container on ${HOST}:${PORT}"
echo "   → mapped to your host at http://localhost:${PORT}" 

# Exec into the dev server
exec uv run manage.py runserver "${HOST}:${PORT}"       # to hit production server, replace the port 8001 manually in browser