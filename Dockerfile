FROM ghcr.io/osgeo/gdal:ubuntu-small-3.7.1

ENV VIRTUAL_ENV=/opt/venv
ENV USER="urbaflow-user"

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
RUN python3 -m venv "$VIRTUAL_ENV" && \
    pip install -U \
    pip \
    setuptools \
    wheel

COPY urbaflow/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt


# Add source
COPY urbaflow/ ./urbaflow
RUN pip3 install -e ./urbaflow

# Make library importable
ENV PYTHONPATH=/home/${USER}/urbaflow

RUN mkdir /home/${USER}/.prefect/ \
   && mkdir /home/${USER}/logs \
   && chown -R ${USER} .

USER ${USER}
WORKDIR /home/${USER}/urbaflow

# Default command for production
CMD ["python", "urbaflow/main.py"]
