FROM python:3.11-slim AS base

LABEL org.opencontainers.image.title="pentest-report-builder" \
      org.opencontainers.image.description="Environment to generate Markdown and PDF reports (Python + Pandoc + TeX Live)" \
      org.opencontainers.image.source="https://example.local/your/repo"

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps: Pandoc + LaTeX packages needed by templates
RUN apt-get update && apt-get install -y --no-install-recommends \
        pandoc \
        texlive-latex-base \
        texlive-latex-recommended \
        texlive-latex-extra \
        texlive-fonts-recommended \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work

# Install Python dependencies required for report generation
# Build context is modules/reporting.
COPY reportbuilder/docker/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm -f /tmp/requirements.txt

# Copy reporting scripts and templates into the image
COPY . /work

# Default to a shell; run specific scripts via `docker run ... python ...`
CMD ["bash"]
