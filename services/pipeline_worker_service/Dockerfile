# Define ARGs at the top (available to all stages)
ARG CUDA_VERSION=11.8.0
ARG UBUNTU_VERSION=22.04
ARG PYTHON_VERSION=3.10
ARG DEBIAN_VERSION=bookworm
ARG SERVICE_NAME=pipeline_worker_service
#----------------------------------------------------------------------------------#
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION} AS installer
ARG SERVICE_NAME
# Set the working directory
WORKDIR /install
COPY ./${SERVICE_NAME}/requirements.txt .
RUN pip install --upgrade pip
# Download packages only
RUN pip download -v -r requirements.txt -d /install/packages
#----------------------------------------------------------------------------------#
FROM installer AS  base_builder

ARG PYTHON_VERSION
RUN set -eux; \
    if [ -f /etc/apt/sources.list ]; then \
        sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list; \
    fi; \
    if ls /etc/apt/sources.list.d/*.list >/dev/null 2>&1; then \
        sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/*.list; \
    fi; \
    if ls /etc/apt/sources.list.d/*.sources >/dev/null 2>&1; then \
        sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/*.sources; \
    fi; \
    apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
# Set the working directory
WORKDIR /build
# create a virtual environment
RUN python${PYTHON_VERSION} -m venv --copies /build/.venv

RUN /build/.venv/bin/pip install --upgrade pip
# NOW copy git requirements
COPY ./requirements-common.txt /install/requirements-common.txt

RUN /build/.venv/bin/pip install -v --no-index --find-links=/install/packages -r /install/requirements.txt && /build/.venv/bin/pip list
FROM base_builder AS builder

# Install the packages from the downloaded files

RUN /build/.venv/bin/pip install -v --upgrade -r /install/requirements-common.txt && /build/.venv/bin/pip list
# FR App Base Image For All Services - USE DEBIAN BOOKWORM CUDA IMAGE
FROM nvidia/cuda:${CUDA_VERSION}-runtime-ubuntu${UBUNTU_VERSION} AS runner
ARG SERVICE_NAME
# Install Python 3.10 and dependencies in the runtime stage
RUN apt-get update && apt-get install -y \
    software-properties-common \
    # && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y \
    python3.10 \
    python3.10-dev \
    python3.10-venv \
    libglib2.0-0 \
    libgl1-mesa-glx \
    cuda-nvrtc-11-8 \
    cuda-nvrtc-dev-11-8 \
    curl \
    wget \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Create symlinks for python
RUN ln -sf /usr/bin/python3.10 /usr/bin/python3
RUN ln -sf /usr/bin/python3.10 /usr/bin/python

# Create app directory and subdirectories
WORKDIR /app

# Copy ONLY the virtual environment (not system Python libraries)
COPY --from=builder /build/.venv /build/.venv

# Create user BEFORE setting permissions
RUN addgroup --system --gid 1000 run_user &&\
    adduser --system --uid 1000 --ingroup run_user run_user

# Fix virtual environment permissions for run_user
RUN chown -R run_user:run_user /build/.venv

# Set PATH to use the virtual environment
ENV PATH="/build/.venv/bin:$PATH"

#3-Pipeline Worker Service
COPY ${SERVICE_NAME} /app
COPY ./common_utilities /app/common_utilities
COPY ./config /app/config
RUN rm -f requirements.txt

# Set ownership of app directory
RUN chown -R run_user:run_user /app && \
    chmod -R 755 /app

RUN echo 'root:123' | chpasswd
USER run_user

# Default entrypoint
CMD ["/app/run_pipeline_worker.sh"]
