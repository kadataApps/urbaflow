FROM ghcr.io/osgeo/gdal:ubuntu-small-3.7.1

COPY --from=ghcr.io/astral-sh/uv:0.11.11 /uv /uvx /bin/

ENV VIRTUAL_ENV=/opt/venv
ENV USER="urbaflow-user"
ENV UV_PROJECT_ENVIRONMENT=$VIRTUAL_ENV

# Create non root user
RUN useradd -m -r ${USER} && \
    chown ${USER} /home/${USER}

WORKDIR /home/${USER}

# Install system dependencies
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive  apt-get install -y \
    alien \
    build-essential \
    gcc \
    libaio1 \
    libpq-dev \
    python3-dev \
    python3.10-venv \
    tzdata \
    wget \
    && rm -rf /var/lib/apt/lists/*
## adding python3-dev + gcc fix error installing with arm64
ENV TZ=UTC

# Create and "activate" venv by prepending it to PATH then install python dependencies
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY urbaflow/pyproject.toml urbaflow/uv.lock ./urbaflow/
RUN cd urbaflow && uv sync --locked --no-dev --no-install-project


# Add source
COPY --chown=${USER}:${USER} urbaflow/ ./urbaflow
RUN cd urbaflow && uv sync --locked --no-dev

# Make library importable
ENV PYTHONPATH=/home/${USER}/urbaflow

RUN mkdir -p /home/${USER}/.prefect /home/${USER}/logs /home/${USER}/urbaflow/temp \
    && chown ${USER}:${USER} /home/${USER}/.prefect /home/${USER}/logs /home/${USER}/urbaflow/temp

USER ${USER}
WORKDIR /home/${USER}/urbaflow

# Default command for production
CMD ["python", "urbaflow/main.py"]
