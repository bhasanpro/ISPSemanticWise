# ISPSemanticWise Dockerfile
# Multi-stage build for production using uv

# ==========================================
# BASE STAGE
# ==========================================
FROM python:3.11-slim as base

# System dependencies for Oracle (cx_Oracle) and other libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libaio1 \
    libaio-dev \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Oracle Instant Client (for cx_Oracle)
ARG ORACLE_INSTANT_CLIENT_VERSION=21.12.0.0.0
RUN mkdir -p /opt/oracle && \
    cd /opt/oracle && \
    curl -sL -o instantclient.zip https://download.oracle.com/otn_software/linux/instantclient/${ORACLE_INSTANT_CLIENT_VERSION}/instantclient-basic-linux.x64-${ORACLE_INSTANT_CLIENT_VERSION}.zip && \
    unzip instantclient.zip && \
    rm instantclient.zip && \
    cd /opt/oracle/instantclient_* && \
    echo /opt/oracle/instantclient_* > /etc/ld.so.conf.d/oracle-instantclient.conf && \
    ldconfig

ENV LD_LIBRARY_PATH=/opt/oracle/instantclient_21_12:$LD_LIBRARY_PATH
ENV ORACLE_HOME=/opt/oracle/instantclient_21_12

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Set working directory
WORKDIR /app

# Copy dependency files
COPY requirements.txt requirements-dev.txt ./

# Install dependencies with uv (much faster than pip)
RUN uv pip install --system --no-cache -r requirements.txt

# ==========================================
# DEVELOPMENT STAGE
# ==========================================
FROM base as development

# Install dev dependencies with uv
RUN uv pip install --system --no-cache -r requirements-dev.txt

# Copy source code
COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/
COPY tests/ ./tests/
COPY pyproject.toml .
COPY README.md .

# Expose port
EXPOSE 8000

# Default command
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ==========================================
# PRODUCTION BUILD STAGE
# ==========================================
FROM base as builder

# Copy source
COPY src/ ./src/
COPY config/ ./config/
COPY pyproject.toml .
COPY README.md .

# Install package with uv
RUN uv pip install --system --no-cache -e .

# ==========================================
# PRODUCTION STAGE
# ==========================================
FROM python:3.11-slim as production

# System dependencies for runtime (Oracle client already in base)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libaio1 \
    && rm -rf /var/lib/apt/lists/*

# Copy Oracle Instant Client from base
COPY --from=base /opt/oracle /opt/oracle
COPY --from=base /etc/ld.so.conf.d/oracle-instantclient.conf /etc/ld.so.conf.d/
RUN ldconfig

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application
COPY --from=builder /app/src ./src
COPY --from=builder /app/config ./config

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]