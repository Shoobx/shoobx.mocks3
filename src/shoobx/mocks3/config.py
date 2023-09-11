###############################################################################
#
# Copyright 2016 by Shoobx, Inc.
#
###############################################################################
"""Application Configuration
"""
from configparser import ConfigParser
import logging
import os

from flask_cors import CORS
from moto import server

try:
    import ConfigParser as configparser  # Py2
except ImportError:
    import configparser  # Py3

from shoobx.mocks3 import models

_CONFIG = None
CONFIG_FILE = None

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


def fill_config(config_path):
    """
    Config priority

    default values -> config -> env
    """
    config = ConfigParser()
    default_values = {
        "shoobx:mocks3":{
            "log-level": "INFO",
            "directory": "./data",
            "hostname": "localhost",
            "reload": "True",
            "debug": "False",
        },
        "shoobx:server": {
            "host-ip": "0.0.0.0",
            "host-port": "8003"
        }
    }

    for section, option in default_values.items():
        config[section] = {}
        for key, value in option.items():
            config[section][key] = value
    config.read(config_path)

    for section in config.sections():
        for key in config[section]:
            os_key = key.upper().replace('-', '_')
            if os_key in os.environ:
                config[section][key] = os.environ[os_key]
    return config


def load_config(config_path):
    global _CONFIG
    if _CONFIG is not None:
        return _CONFIG

    # Load from config files. It will load from all files, with last one
    # winning if there are multiple files.
    _CONFIG = fill_config(config_path)

    return _CONFIG


def configure(config_file):
    config = load_config(config_file)

    # Setup logging.
    filename = None
    if config.has_option("shoobx:mocks3", "log-file"):
        filename = config.get("shoobx:mocks3", "log-file")
    logging.basicConfig(
        filename=filename, level=config.get("shoobx:mocks3", "log-level")
    )

    directory = config.get("shoobx:mocks3", "directory")
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
            "HTTP_HOST": config.get("shoobx:mocks3", "hostname"),
        }
    )
