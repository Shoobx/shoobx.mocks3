FROM python:3.11-bullseye

LABEL org.opencontainers.image.authors="dev@shoobx.com"


RUN apt-get update && apt-get upgrade -y

ARG APP_USER=shoobx\
    APP_GROUP=shoobx\
    CODE_FOLDER=/shoobx/shoobx.mocks3 \
    USER_ID=2000 \
    GROUP_ID=2000

RUN groupadd --gid $GROUP_ID --non-unique $APP_GROUP && \
    useradd --no-log-init --uid $USER_ID --non-unique --gid $GROUP_ID --create-home --shell /bin/bash $APP_USER && \
    echo Created user $USER_ID and group $GROUP_ID

WORKDIR $CODE_FOLDER

RUN mkdir var etc

RUN chown -R $APP_USER:$APP_GROUP $CODE_FOLDER var etc


COPY . .
RUN pip install -r requirements.txt

USER $APP_USER
EXPOSE 8081

CMD sbx-mocks3-serve -c /dev/null
