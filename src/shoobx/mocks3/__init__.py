###############################################################################
#
# Copyright 2016 by Shoobx, Inc.
#
###############################################################################
"""Shoobx Mock S3
"""
import importlib
import importlib.metadata as importlib_metadata

from typing import Literal, Union, overload

try:
    __version__ = importlib_metadata.version("shoobx.mocks3")
except importlib_metadata.PackageNotFoundError:
    __version__ = "unknown"

import moto.backends
# Insert our custom backend into moto.
from moto.core.base_backend import BackendDict
from moto.backends import SERVICE_NAMES

from .models import ShoobxS3Backend, s3_backends  # noqa

def _import_backend(module_name, backends_name):
    if module_name.startswith("shoobx."):
        module = importlib.import_module(module_name)
    else:
        module = importlib.import_module("moto." + module_name)
    return getattr(module, backends_name)

orig_list_of_moto_modules = moto.backends.list_of_moto_modules

def list_of_moto_modules():
    yield "shoobx.mocks3"
    orig_list_of_moto_modules()

moto.backends.list_of_moto_modules = list_of_moto_modules



# Monkey patch _import_backend to escape "moto." pkg prefixing
# for shoobx backends
moto.backends._import_backend = _import_backend


original_get_service_from_url = moto.backends.get_service_from_url

def get_service_from_url(url: str):
    be = original_get_service_from_url
    if be == "s3":
        return "s3_sbx"
    return be

moto.backends.get_service_from_url = get_service_from_url



# moto.backends.SERVICE_NAMES = Union[SERVICE_NAMES, Literal["s3_sbx"]]
moto.backends.ALT_SERVICE_NAMES["s3"] = "shoobx.mocks3"
moto.backends.ALT_BACKEND_NAMES["shoobx.mocks3"] = "s3"

@overload
def get_backend(name: "Literal['s3']") -> "BackendDict[ShoobxS3Backend]": ...


# BACKENDS["s3_sbx"] = ("shoobx.mocks3", "s3_backends")