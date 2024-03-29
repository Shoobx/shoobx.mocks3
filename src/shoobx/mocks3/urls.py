###############################################################################
#
# Copyright 2016 by Shoobx, Inc.
#
###############################################################################
"""Flask endpoints
"""
from shoobx.mocks3.responses import S3ResponseInstance

url_bases = [
    "https?://s3(.*).amazonaws.com",
    r"https?://(?P<bucket_name>[a-zA-Z0-9\-_.]*)\.?s3(.*).amazonaws.com",
]


def ambiguous_response1(*args, **kwargs):
    return S3ResponseInstance.ambiguous_response(*args, **kwargs)


def ambiguous_response2(*args, **kwargs):
    return S3ResponseInstance.ambiguous_response(*args, **kwargs)


url_paths = {
    # subdomain bucket
    "{0}/$": S3ResponseInstance.bucket_response,
    # Expose the storage directory
    "{0}/STORAGE_DIR$": S3ResponseInstance.get_storage_dir,
    # subdomain key of path-based bucket
    "{0}/(?P<key_or_bucket_name>[^/]+)/?$": S3ResponseInstance.ambiguous_response,
    # path-based bucket + key
    "{0}/(?P<bucket_name_path>[^/]+)/(?P<key_name>.+)": S3ResponseInstance.key_response,
}
