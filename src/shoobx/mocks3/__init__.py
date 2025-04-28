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
# Insert our custom backend into moto.
from moto.backends import BACKENDS

from .models import s3_backends  # noqa


def _import_backend(module_name, backends_name):
    if module_name.startswith("shoobx."):
        module = importlib.import_module(module_name)
    else:
        module = importlib.import_module("moto." + module_name)
    return getattr(module, backends_name)


# Monkey patch _import_backend to escape "moto." pkg prefixing
# for shoobx backends
moto.backends._import_backend = _import_backend

BACKENDS["s3-sbx"] = ("shoobx.mocks3", "s3_backends")
