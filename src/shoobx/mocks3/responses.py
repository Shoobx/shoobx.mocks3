###############################################################################
#
# Copyright 2016 by Shoobx, Inc.
#
###############################################################################
"""S3 Responses
"""
import io
from typing import Union

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

    # Backported from moto 5.0. Pinned version does not handle aws-chunked files correctly.
    # Last parameter is unused because we maintain original method signature for compatibility.
    def _handle_encoded_body(self, body: Union[io.BufferedIOBase, bytes], content_length_unused: int) -> bytes:
        decoded_body = b""
        if not body:
            return decoded_body
        if isinstance(body, bytes):
            body = io.BytesIO(body)
        # first line should equal '{content_length}\r\n' while the content_length is a hex number
        content_length = int(body.readline().strip(), 16)
        while content_length > 0:
            # read the content_length of the actual data
            decoded_body += body.read(content_length)
            # next is line with just '\r\n' so we skip it
            body.readline()
            # read another line with '{content_length}\r\n'
            content_length = int(body.readline().strip(), 16)

        return decoded_body

S3ResponseInstance = S3Response()
