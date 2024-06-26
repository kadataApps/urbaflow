FROM ghcr.io/osgeo/gdal:ubuntu-small-3.7.1

ENV VIRTUAL_ENV=/opt/venv
ENV USER="urbaflow-user"

# Create non root user
RUN useradd -m -r ${USER} && \
    chown ${USER} /home/${USER}

WORKDIR /home/${USER}

# Install system dependencies
RUN apt-get update
RUN apt-get install -y \
    libpq-dev \
    build-essential \
    alien \
    libaio1 \
    wget \
    python3.10-venv \
    python3-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*
## adding python3-dev + gcc fix error installing with arm64

# Create and "activate" venv by prepending it to PATH then install python dependencies
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY requirements.txt /tmp/requirements.txt

RUN python3 -m venv $VIRTUAL_ENV && \
    pip install -U \
    pip \
    setuptools \
    wheel

RUN pip install -r /tmp/requirements.txt

# Make library importable
ENV PYTHONPATH=/home/${USER}

# Add source
COPY . ./urbaflow
RUN pip3 install -e ./urbaflow
RUN mkdir /home/${USER}/.prefect/

# create log folder
RUN mkdir /home/${USER}/logs

RUN chown -R ${USER} .
USER ${USER}
WORKDIR /home/${USER}/urbaflow
RUN python urbaflow/main.py --install-completion
CMD ["python", "urbaflow/main.py"]


# RUN mkdir /app
# WORKDIR /app/

# RUN pip3 install -r requirements.txt
# ENV PYTHONPATH "${PYTONPATH}:/opt/app"
# COPY ./src .

# RUN python setup.py install

# RUN echo 'eval "$(_PROCESS_COMPLETE=source process)"' >> ~/.bashrc

