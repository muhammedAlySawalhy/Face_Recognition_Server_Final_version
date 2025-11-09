# Define ARGs at the top (available to all stages)
ARG PYTHON_VERSION=3.10
ARG DEBIAN_VERSION=bookworm
ARG SERVICE_NAME=server_manager_service
#----------------------------------------------------------------------------------#
# First Stage - Installer Stage
# This stage is responsible for downloading all required Python packages without installing them.
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION} AS installer

ARG SERVICE_NAME

RUN pip install --upgrade pip
# Set the working directory
WORKDIR /install
COPY ./${SERVICE_NAME}/requirements.txt requirements.txt 
# Download packages only
RUN pip download -vv -r requirements.txt -d /install/packages
#----------------------------------------------------------------------------------#
# Second Stage - Base Builder Stage
# This stage sets up the base environment for building the application, including installing system dependencies and creating a virtual environment.
# It copies the downloaded packages from the installer stage and installs them into the virtual environment.
# It also prepares the environment for further stages by installing common utilities.
# This stage is used to create a reusable base image for building the application.
# It does not include any service-specific dependencies, which are handled in the final stage.
#----------------------------------------------------------------------------------#
FROM installer AS base_builder
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
    apt-get update && apt-get install -y --no-install-recommends \
build-essential \
libpq-dev \
git \
curl \
&& apt-get clean \
            && apt-get autoremove -y \
            && rm -rf /var/lib/apt/lists/*
WORKDIR /build
RUN python -m venv --copies /build/.venv
RUN /build/.venv/bin/pip install --upgrade pip
RUN /build/.venv/bin/pip install --upgrade setuptools
COPY ./requirements-common.txt /tmp/requirements-common.txt
RUN /build/.venv/bin/pip install -v --no-cache-dir -r /tmp/requirements-common.txt
RUN /build/.venv/bin/pip list
#----------------------------------------------------------------------------------#
# Third Stage - Services Builder Stage
# This stage builds the application services by installing service-specific dependencies.
# It copies the virtual environment from the base builder stage and installs the service-specific requirements.
# This stage is used to create the final application image that includes all necessary dependencies for running the services.
# It ensures that the application is built with the correct dependencies and is ready for deployment.
#----------------------------------------------------------------------------------#
FROM base_builder AS service_builder
WORKDIR /build
RUN /build/.venv/bin/pip install -v --no-index --find-links=/install/packages -r /install/requirements.txt
RUN /build/.venv/bin/pip list
#----------------------------------------------------------------------------------#
# Final Stage - Runner Stage
# This stage creates the final application image that includes all necessary dependencies for running the services.
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION} AS runner
ARG SERVICE_NAME
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY --from=service_builder /build/.venv /build/.venv
ENV PATH="/build/.venv/bin:$PATH"
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*
# Copy the service files
COPY ./${SERVICE_NAME}/ /app/
COPY ./common_utilities /app/common_utilities
COPY ./config /app/config
# Create user and set permissions BEFORE switching user
RUN addgroup --system --gid 1000 run_user && \
    adduser --system --uid 1000 run_user --ingroup run_user && \
    chown -R run_user:run_user /app && \
    chmod -R 755 /app && \
    chmod +x /app/run_server_manager.sh && \
    rm -f /app/requirements.txt

# Switch to non-root user
USER run_user
ENTRYPOINT [ "/app/run_server_manager.sh" ]
