# Core backend image Dockerfile
# Build context: repository root.

ARG USERNAME=developer
ARG USER_UID=1000
ARG USER_GID=$USER_UID
ARG DOCKER_GID=999

FROM python:3.13.5-slim AS base

ARG USERNAME
ARG USER_UID
ARG USER_GID
ARG DOCKER_GID

ENV VIRTUAL_ENV=/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Make the repo layout importable.
ENV PYTHONPATH="/app:/app/modules"

RUN apt-get update && \
    apt-get install -y git sudo && \
    groupadd --gid $USER_GID $USERNAME && \
    groupadd -g $DOCKER_GID docker && \
    useradd --uid $USER_UID --gid $USER_GID -m -G docker $USERNAME && \
    echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME && \
    chmod 0440 /etc/sudoers.d/$USERNAME && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir $VIRTUAL_ENV; \
    chown -R $USER_UID:$USER_GID $VIRTUAL_ENV

ARG USERHOME=/home/$USERNAME
RUN mkdir -p /root/.vscode-server /root/.cache && \
    mkdir -p $USERHOME/.vscode-server $USERHOME/.cache && \
    chown -R $USERNAME:$USERNAME $USERHOME/.vscode-server $USERHOME/.cache

USER $USERNAME
RUN python3 -m venv $VIRTUAL_ENV

WORKDIR /app

# Install dependencies from the canonical backend requirements.
COPY core/infra/app/requirements.txt ./requirements.txt
RUN $VIRTUAL_ENV/bin/pip install --timeout 120 --resume-retries 5 -r requirements.txt

# Copy module scaffolds and tool/report Docker build contexts.
COPY modules/ ./modules

# Copy core runtime code (API, celery tasks, docker runner).
COPY core/app/ ./core/app/

# Copy core database utilities.
COPY core/database/ ./core/database/

# Copy core infra scaffolding (compose, scripts, etc.).
COPY core/infra/ ./core/infra/

CMD ["uvicorn", "core.app.api:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
