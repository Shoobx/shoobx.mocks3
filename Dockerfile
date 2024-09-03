FROM python:3.11-bullseye

LABEL org.opencontainers.image.authors="dev@shoobx.com"


RUN apt-get update && \
    apt-get upgrade -y vim && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/*

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

COPY --chown=$APP_USER:$APP_GROUP . .
ENV PATH="$PATH:$APP_HOME/.local/bin"

RUN pip install -r requirements.txt


CMD ["sbx-mocks3-serve"]
