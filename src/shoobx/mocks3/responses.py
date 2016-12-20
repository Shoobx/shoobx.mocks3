###############################################################################
#
# Copyright 2016 by Shoobx, Inc.
#
###############################################################################
"""S3 Responses
"""
from shoobx.mocks3 import models
from moto.s3 import responses

S3ResponseInstance = responses.ResponseObject(models.s3_sbx_backend)
