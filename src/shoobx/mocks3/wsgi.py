###############################################################################
#
# Copyright 2016 by Shoobx, Inc.
#
###############################################################################
"""WSGI Entry Point
"""
import os

from shoobx.mocks3 import config


def get_wsgi_app():
    config_file = os.environ.get(
        'SHOOBX_MOCKS3_CONFIG',
        os.path.join(config.SHOOBX_MOCKS3_HOME, 'config', 'mocks3.cfg'))
    return config.configure(config_file)
