###############################################################################
#
# Copyright 2016 by Shoobx, Inc.
#
###############################################################################
"""S3 Responses
"""
from moto.s3 import responses

from shoobx.mocks3 import models


class ResponseObject(responses.ResponseObject):

    def subdomain_based_buckets(self, request):
        return False

    def get_storage_dir(self, request, full_url, headers):
        return 200, headers, self.backend.directory


S3ResponseInstance = ResponseObject(models.s3_sbx_backend)
