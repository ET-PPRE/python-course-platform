####################################
# -1) Bring in a small Docker CLI binary to let celery talk with sandbox
####################################
FROM docker:27-cli AS dcli

####################################
# 0) SANDBOX STAGE (pure sandbox) #
####################################
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS sandbox

WORKDIR /app
COPY sandbox-requirements.txt ./

RUN uv venv .venv

# Install *only* the sandbox extras—no app deps, no dev deps
RUN uv pip install --no-cache-dir -r sandbox-requirements.txt

# Make the sandbox venv active on PATH. PATH is per-image and per-container. so it doesnot collide with dev path
ENV PATH="/app/.venv/bin:$PATH"

# uv will be the entry point to this container, so any script will use `uv` before [cmd]. eg: uv run python <script>
ENTRYPOINT ["uv"]
CMD ["run", "python"]   

####################################
# 1) BASE IMAGE ( install deps )  #
####################################

# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base

# Install the project into `/app`
WORKDIR /app

# Use persistent APT cache mounts for faster rebuilds
RUN --mount=type=cache,target=/var/lib/apt/lists \
    --mount=type=cache,target=/var/cache/apt \
    apt-get update -qq && \
    apt-get install -y -qq --no-install-recommends git make && \
    rm -rf /var/lib/apt/lists/*

# Install Git to dynamically clone the git repo
#RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copy only what's needed for dependency installation
COPY uv.lock pyproject.toml ./

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

####################################
# 2) DEVELOPMENT IMAGE ( hot‑reload ) #
####################################

FROM base AS dev

COPY --from=dcli /usr/local/bin/docker /usr/local/bin/docker

# Now install dev‑dependencies as well
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Copy start-django for migrations + runserver
COPY start-django.sh /app/start-django.sh
RUN chmod +x /app/start-django.sh

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT ["/app/start-django.sh"]

# Uses `--host 0.0.0.0` to allow access from outside the container
CMD ["runserver", "0.0.0.0:8000"]

####################################
# 3) PRODUCTION IMAGE ( lean )     #
####################################

FROM base AS prod

# Copy in docker CLI from the small dcli stage
COPY --from=dcli /usr/local/bin/docker /usr/local/bin/docker

# Install podman-docker so the docker CLI can talk to Podman socket
RUN --mount=type=cache,target=/var/lib/apt/lists \
    --mount=type=cache,target=/var/cache/apt \
    apt-get update -qq && \
    apt-get install -y --no-install-recommends podman-docker && \
    rm -rf /var/lib/apt/lists/*

# Only install runtime deps (not dev)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Put venv on path
ENV PATH="/app/.venv/bin:$PATH"

# For celery/grader: make sure logs & tmp are safe inside container
ENV UV_CACHE_DIR=/tmp/.cache/uv
ENV DJANGO_LOG_DIR=/tmp/logs
ENV GRADER_HOST_DIR=/grader
ENV GRADER_BIND_DIR=/var/tmp/grader

WORKDIR /app/src

# Default entrypoint/command will be set per service in docker-compose
ENTRYPOINT []
CMD ["gunicorn", "project.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
