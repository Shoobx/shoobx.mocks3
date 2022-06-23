###############################################################################
#
# Copyright 2016 by Shoobx, Inc.
#
###############################################################################
"""S3 Responses
"""
from moto.s3 import responses

from shoobx.mocks3 import models


class S3Response(responses.S3Response):

    @property
    def backend(self):
        return models.s3_sbx_backend

    def subdomain_based_buckets(self, request):
        return False

    def get_storage_dir(self, request, full_url, headers):
        return 200, headers, self.backend.directory


S3ResponseInstance = S3Response()
