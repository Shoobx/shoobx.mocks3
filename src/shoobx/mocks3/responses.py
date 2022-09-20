###############################################################################
#
# Copyright 2016 by Shoobx, Inc.
#
###############################################################################
"""S3 Responses
"""
from moto.s3 import responses

from .models import MOTO_DEFAULT_ACCOUNT_ID, s3_backends


class S3Response(responses.S3Response):
    @property
    def backend(self):
        return s3_backends[MOTO_DEFAULT_ACCOUNT_ID]["global"]

    def subdomain_based_buckets(self, request):
        return False

    def get_storage_dir(self, request, full_url, headers):
        return 200, headers, self.backend.directory


S3ResponseInstance = S3Response()
