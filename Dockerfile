ARG PULL_REPO=docker.io
FROM ${PULL_REPO}/python:3.11-slim

LABEL org.opencontainers.image.authors="dev@shoobx.com"

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked  \
    --mount=type=cache,target=/var/lib/apt,sharing=locked  \
    apt-get update && \
    apt-get upgrade -y vim pipx

ARG APP_USER=shoobx \
    APP_GROUP=shoobx \
    CODE_FOLDER=/shoobx/shoobx.mocks3 \
    USER_ID=2000 \
    GROUP_ID=2000

ENV APP_HOME=/home/$APP_USER
RUN groupadd --gid $GROUP_ID --non-unique $APP_GROUP && \
    useradd --no-log-init --uid $USER_ID --non-unique --gid $GROUP_ID --create-home --shell /bin/bash $APP_USER && \
    echo Created user $USER_ID and group $GROUP_ID

USER $APP_USER
WORKDIR $CODE_FOLDER

ENV PATH="$PATH:$APP_HOME/.local/bin"

ARG PIP_INDEX_URL="https://pypi.org/simple"
ENV PIP_INDEX_URL=$PIP_INDEX_URL
RUN pipx install uv==0.11.13

ENV UV_INDEX_URL=$PIP_INDEX_URL
RUN --mount=type=cache,id=uv-cache,target=/home/shoobx/.cache/uv,uid=$USER_ID,sharing=locked \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

COPY --chown=$APP_USER:$APP_GROUP . .

RUN --mount=type=cache,id=uv-cache,target=/home/shoobx/.cache/uv,uid=$USER_ID,sharing=locked \
    uv sync --frozen

ENV UV_NO_SYNC="true"
CMD ["uv", "run", "sbx-mocks3-serve"]
