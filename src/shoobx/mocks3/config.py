###############################################################################
#
# Copyright 2016 by Shoobx, Inc.
#
###############################################################################
"""Application Configuration
"""
import ConfigParser
import logging
import os
from moto import server

_CONFIG = None
CONFIG_FILE = None

# Define Source code root.
# pragma: no cover
if __file__.split('/')[-4] == 'src':
    # Dev sandbox
    SHOOBX_MOCKS3_HOME = __file__.rsplit('src', 1)[0]
else:
    # Deployment virtualenv
    SHOOBX_MOCKS3_HOME = __file__.rsplit('lib', 1)[0]  # pragma: no cover

SHOOBX_MOCKS3_HOME = os.environ.get('SHOOBX_MOCKS3_HOME', SHOOBX_MOCKS3_HOME)

log = logging.getLogger('shoobx.mocks3')


def load_config(config_path):
    global _CONFIG
    if _CONFIG is not None:
        return _CONFIG
    _CONFIG = ConfigParser.ConfigParser()

    # Load from config files. It will load from all files, with last one
    # winning if there are multiple files.
    _CONFIG.read(config_path)

    return _CONFIG


def configure(config_file):
    config = load_config(config_file)

    # Setup logging.
    logging.basicConfig(level=config.get('shoobx:mocks3', 'log-level'))

    register_resources()

    # Create the Flask app.
    log.info("Starting...")

    app = server.DomainDispatcherApplication(
        server.create_backend_app, service='s3-sbx')

    return app
