# ---- Development Stage ----
FROM python:3.12-slim AS development
ARG INSTALL_GCLOUD=true
WORKDIR /app
RUN adduser --disabled-password --gecos '' terramorph
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl unzip ca-certificates \
    && rm -rf /var/lib/apt/lists/*
# Install Terraform (85MB - required for fmt)
RUN curl -fsSL https://releases.hashicorp.com/terraform/1.9.5/terraform_1.9.5_linux_amd64.zip -o /tmp/tf.zip \
    && unzip /tmp/tf.zip -d /usr/local/bin/ \
    && rm /tmp/tf.zip
# Install gcloud CLI (optional - only needed for Bulk Export mode)
RUN if [ "$INSTALL_GCLOUD" = "true" ]; then \
    curl -fsSL https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz \
    | tar -xz -C /opt \
    && /opt/google-cloud-sdk/install.sh --quiet --usage-reporting false --path-update true \
    && /opt/google-cloud-sdk/bin/gcloud components install beta --quiet \
    && /opt/google-cloud-sdk/bin/gcloud components remove bq gsutil --quiet 2>/dev/null || true \
    && rm -rf /opt/google-cloud-sdk/.install/.backup \
    && find /opt/google-cloud-sdk -name "*.pyc" -delete \
    && find /opt/google-cloud-sdk -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true; \
    fi
ENV PATH="/opt/google-cloud-sdk/bin:${PATH}"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/data && chown terramorph:terramorph /app/data
USER terramorph
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ---- Production Stage ----
FROM python:3.12-slim AS production
ARG INSTALL_GCLOUD=true
WORKDIR /app
RUN adduser --disabled-password --gecos '' terramorph
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl unzip ca-certificates \
    && rm -rf /var/lib/apt/lists/*
# Install Terraform
RUN curl -fsSL https://releases.hashicorp.com/terraform/1.9.5/terraform_1.9.5_linux_amd64.zip -o /tmp/tf.zip \
    && unzip /tmp/tf.zip -d /usr/local/bin/ \
    && rm /tmp/tf.zip
# Install gcloud CLI (optional)
RUN if [ "$INSTALL_GCLOUD" = "true" ]; then \
    curl -fsSL https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz \
    | tar -xz -C /opt \
    && /opt/google-cloud-sdk/install.sh --quiet --usage-reporting false --path-update true \
    && /opt/google-cloud-sdk/bin/gcloud components install beta --quiet \
    && /opt/google-cloud-sdk/bin/gcloud components remove bq gsutil --quiet 2>/dev/null || true \
    && rm -rf /opt/google-cloud-sdk/.install/.backup \
    && find /opt/google-cloud-sdk -name "*.pyc" -delete \
    && find /opt/google-cloud-sdk -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true; \
    fi
ENV PATH="/opt/google-cloud-sdk/bin:${PATH}"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
RUN mkdir -p /app/data && chown terramorph:terramorph /app/data
USER terramorph
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
