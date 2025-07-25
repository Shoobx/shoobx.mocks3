###############################################################################
#
# Copyright 2016 by Shoobx, Inc.
#
###############################################################################
"""Shoobx Mock S3
"""
import importlib
import importlib.metadata as importlib_metadata

try:
    __version__ = importlib_metadata.version("shoobx.mocks3")
except importlib_metadata.PackageNotFoundError:
    __version__ = "unknown"

import moto.backends

from .models import s3_backends  # noqa

def _import_backend(module_name, backends_name):
    # Hijack s3 module
    if module_name == "s3":
        module = importlib.import_module("shoobx.mocks3")
    else:
        module = importlib.import_module("moto." + module_name)
    return getattr(module, backends_name)

# Monkey patch _import_backend to return our s3 service
moto.backends._import_backend = _import_backend
