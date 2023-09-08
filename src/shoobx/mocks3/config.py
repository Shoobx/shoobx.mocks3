###############################################################################
#
# Copyright 2016 by Shoobx, Inc.
#
###############################################################################
"""Application Configuration
"""
import logging
import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from flask_cors import CORS
from moto import server

try:
    import ConfigParser as configparser  # Py2
except ImportError:
    import configparser  # Py3

from shoobx.mocks3 import models


# Define Source code root.
# pragma: no cover
if __file__.split("/")[-4] == "src":
    # Dev sandbox
    SHOOBX_MOCKS3_HOME = __file__.rsplit("src", 1)[0]
else:
    # Deployment virtualenv
    SHOOBX_MOCKS3_HOME = __file__.rsplit("lib", 1)[0]  # pragma: no cover

SHOOBX_MOCKS3_HOME = os.environ.get("SHOOBX_MOCKS3_HOME", SHOOBX_MOCKS3_HOME)

log = logging.getLogger("shoobx.mocks3")


class ServerConfig(BaseSettings):
    model_config = SettingsConfigDict(extra='ignore')

    host_ip: str = Field(default="0.0.0.0")
    host_port: int = Field(default=8003)

class Mocks3Config(BaseSettings):
    model_config = SettingsConfigDict(extra='ignore')

    log_level: str = Field(default="INFO")
    log_file: Optional[str] = None
    directory: str = Field(default="./data")
    hostname: str = Field(default="localhost")
    reload: bool = Field(default=True)
    debug: bool  = Field(default=False)

class Settings(BaseSettings):
    server: ServerConfig
    mocks3: Mocks3Config

_CONFIG: Settings = None
CONFIG_FILE = None

def load_config(config_path):
    global _CONFIG
    if _CONFIG is not None:
        return _CONFIG
    config_file = configparser.ConfigParser()
    #
    # Load from config files. It will load from all files, with last one
    # winning if there are multiple files.
    config_file.read(config_path)

    _CONFIG = Settings(
        mocks3=Mocks3Config(**config_file['shoobx:mocks3'] if config_file.has_section('shoobx:mocks3') else {}),
        server=ServerConfig(**config_file['shoobx:server'] if config_file.has_section('shoobx:server') else {}),
    )

    return _CONFIG


def configure(config_file):
    config = load_config(config_file)

    # Setup logging.
    logging.basicConfig(
        filename=config.mocks3.log_file, level=config.mocks3.log_level
    )

    directory = config.mocks3.directory
    models.s3_backends[models.MOTO_DEFAULT_ACCOUNT_ID]["global"].directory = directory
    if not os.path.exists(directory):
        os.makedirs(directory)

    def create_backend_app(service):
        app = server.create_backend_app(service)
        CORS(app)
        return app

    app = server.DomainDispatcherApplication(create_backend_app, service="s3-sbx")

    return app.get_application(
        {
            "HTTP_HOST": config.mocks3.hostname,
        }
    )
