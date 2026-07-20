# ---- Development Stage ----
FROM python:3.12-slim AS development
WORKDIR /app
RUN adduser --disabled-password --gecos '' terramorph
RUN apt-get update && apt-get install -y curl unzip apt-transport-https ca-certificates gnupg && rm -rf /var/lib/apt/lists/*
# Install Terraform for fmt support
RUN curl -fsSL https://releases.hashicorp.com/terraform/1.9.5/terraform_1.9.5_linux_amd64.zip -o /tmp/tf.zip \
    && unzip /tmp/tf.zip -d /usr/local/bin/ \
    && rm /tmp/tf.zip \
    && chmod +x /usr/local/bin/terraform
# Install gcloud CLI for bulk export
RUN curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" > /etc/apt/sources.list.d/google-cloud-sdk.list \
    && apt-get update && apt-get install -y google-cloud-cli && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/data && chown terramorph:terramorph /app/data
USER terramorph
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ---- Production Stage ----
FROM python:3.12-slim AS production
WORKDIR /app
RUN adduser --disabled-password --gecos '' terramorph
RUN apt-get update && apt-get install -y curl unzip apt-transport-https ca-certificates gnupg && rm -rf /var/lib/apt/lists/*
# Install Terraform for fmt support
RUN curl -fsSL https://releases.hashicorp.com/terraform/1.9.5/terraform_1.9.5_linux_amd64.zip -o /tmp/tf.zip \
    && unzip /tmp/tf.zip -d /usr/local/bin/ \
    && rm /tmp/tf.zip \
    && chmod +x /usr/local/bin/terraform
# Install gcloud CLI for bulk export
RUN curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" > /etc/apt/sources.list.d/google-cloud-sdk.list \
    && apt-get update && apt-get install -y google-cloud-cli && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
RUN mkdir -p /app/data && chown terramorph:terramorph /app/data
USER terramorph
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
