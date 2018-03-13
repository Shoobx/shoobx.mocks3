###############################################################################
#
# Copyright 2016 by Shoobx, Inc.
#
###############################################################################
"""Shoobx Mock S3
"""
from pkg_resources import get_distribution
__version__ = get_distribution('shoobx.mocks3').version

# Insert our custom backend into moto.
from moto.backends import BACKENDS
from .models import s3_sbx_backend

BACKENDS['s3-sbx'] = {'global': s3_sbx_backend}

mock_s3_sbx = s3_sbx_backend.decorator
