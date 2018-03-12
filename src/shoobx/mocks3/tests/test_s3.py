# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright 2016 by Shoobx, Inc.
#
###############################################################################
"""Shoobx S3 Backend
"""
from __future__ import unicode_literals

import boto
import functools
import io
import json
import mock
import os
import requests
import shutil
import tempfile
import unittest
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from boto.exception import S3CreateError, S3ResponseError
from freezegun import freeze_time
from moto.core.models import HttprettyMockAWS
from moto.s3.models import ALL_USERS_GRANTEE
from six.moves.urllib.error import HTTPError
from six.moves.urllib.request import urlopen

from shoobx.mocks3 import models

REDUCED_PART_SIZE = 256


def reduced_min_part_size(f):
    """ speed up tests by temporarily making the multipart minimum part size
        small
    """
    import moto.s3.models as s3model
    orig_size = s3model.UPLOAD_PART_MIN_SIZE

    @functools.wraps(f)
    def wrapped(self, *args, **kwargs):
        try:
            s3model.UPLOAD_PART_MIN_SIZE = REDUCED_PART_SIZE
            return f(self, *args, **kwargs)
        finally:
            s3model.UPLOAD_PART_MIN_SIZE = orig_size
    return wrapped


class BotoTestCase(unittest.TestCase):

    def setUp(self):
        self.mock_aws = HttprettyMockAWS({'global': models.s3_sbx_backend})
        self.mock_aws.start()
        self._dir = tempfile.mkdtemp()
        self.data_dir_patch = mock.patch(
            'shoobx.mocks3.models.s3_sbx_backend.directory',
            self._dir)
        self.data_dir_patch.start()
        self.conn = boto.connect_s3(
            'the_key', 'the_secret',
            calling_format=boto.s3.connection.OrdinaryCallingFormat())
        self.bucket = self.conn.create_bucket('mybucket')

    def tearDown(self):
        self.data_dir_patch.stop()
        shutil.rmtree(self._dir)
        self.mock_aws.stop()

    def save(self, name, value=None, bucket=None):
        k = Key(bucket or self.bucket)
        k.key = name
        if value is not None:
            k.set_contents_from_string(value)
        return k

    def test_save(self):
        self.save('steve', 'is awesome')

        self.assertEqual(
            b'is awesome',
            self.bucket.get_key('steve').get_contents_as_string())

    def test_key_etag(self):
        self.save('steve', 'is awesome')

        self.assertEqual(
            '"d32bda93738f7e03adb22e66c90fbc04"',
            self.bucket.get_key('steve').etag)

    def test_multipart_upload_too_small(self):
        multipart = self.bucket.initiate_multipart_upload("the-key")
        multipart.upload_part_from_file(io.BytesIO(b'hello'), 1)
        multipart.upload_part_from_file(io.BytesIO(b'world'), 2)
        with self.assertRaises(S3ResponseError):
            # Multipart with total size under 5MB is refused
            multipart.complete_upload()

    @reduced_min_part_size
    def test_multipart_upload(self):
        multipart = self.bucket.initiate_multipart_upload("the-key")
        part1 = b'0' * REDUCED_PART_SIZE
        multipart.upload_part_from_file(io.BytesIO(part1), 1)
        # last part, can be less than 5 MB
        part2 = b'1'
        multipart.upload_part_from_file(io.BytesIO(part2), 2)
        multipart.complete_upload()
        # we should get both parts as the key contents
        self.assertEqual(
            part1 + part2,
            self.bucket.get_key("the-key").get_contents_as_string())

    @reduced_min_part_size
    def test_multipart_upload_out_of_order(self):
        multipart = self.bucket.initiate_multipart_upload("the-key")
        # last part, can be less than 5 MB
        part2 = b'1' * REDUCED_PART_SIZE
        multipart.upload_part_from_file(io.BytesIO(part2), 4)
        part1 = b'0' * REDUCED_PART_SIZE
        multipart.upload_part_from_file(io.BytesIO(part1), 2)
        multipart.complete_upload()
        # we should get both parts as the key contents
        self.assertEqual(
            part1 + part2,
            self.bucket.get_key("the-key").get_contents_as_string())

    @reduced_min_part_size
    def test_multipart_upload_with_headers(self):
        multipart = self.bucket.initiate_multipart_upload(
            "the-key", metadata={"foo": "bar"})
        part1 = b'0' * 10
        multipart.upload_part_from_file(io.BytesIO(part1), 1)
        multipart.complete_upload()

        key = self.bucket.get_key("the-key")
        self.assertEqual({"foo": "bar"}, key.metadata)

    @reduced_min_part_size
    def test_multipart_upload_with_copy_key(self):
        key = self.save("original-key", "key_value")

        multipart = self.bucket.initiate_multipart_upload("the-key")
        part1 = b'0' * REDUCED_PART_SIZE
        multipart.upload_part_from_file(io.BytesIO(part1), 1)
        multipart.copy_part_from_key("mybucket", "original-key", 2, 0, 3)
        multipart.complete_upload()
        self.assertEqual(
            part1 + b"key_",
            self.bucket.get_key("the-key").get_contents_as_string())

    @reduced_min_part_size
    def test_multipart_upload_cancel(self):
        multipart = self.bucket.initiate_multipart_upload("the-key")
        part1 = b'0' * REDUCED_PART_SIZE
        multipart.upload_part_from_file(io.BytesIO(part1), 1)
        multipart.cancel_upload()
        # TODO we really need some sort of assertion here, but we don't currently
        # have the ability to list mulipart uploads for a bucket.

    @reduced_min_part_size
    def test_multipart_etag(self):
        multipart = self.bucket.initiate_multipart_upload("the-key")
        part1 = b'0' * REDUCED_PART_SIZE
        multipart.upload_part_from_file(io.BytesIO(part1), 1)
        # last part, can be less than 5 MB
        part2 = b'1'
        multipart.upload_part_from_file(io.BytesIO(part2), 2)
        multipart.complete_upload()
        # we should get both parts as the key contents
        self.assertEqual(
            '"66d1a1a2ed08fd05c137f316af4ff255-2"',
            self.bucket.get_key("the-key").etag)

    @reduced_min_part_size
    def test_multipart_invalid_order(self):
        multipart = self.bucket.initiate_multipart_upload("the-key")
        part1 = b'0' * 5242880
        etag1 = multipart.upload_part_from_file(io.BytesIO(part1), 1).etag
        # last part, can be less than 5 MB
        part2 = b'1'
        etag2 = multipart.upload_part_from_file(io.BytesIO(part2), 2).etag
        xml = "<Part><PartNumber>{0}</PartNumber><ETag>{1}</ETag></Part>"
        xml = xml.format(2, etag2) + xml.format(1, etag1)
        xml = "<CompleteMultipartUpload>{0}</CompleteMultipartUpload>".format(xml)
        with self.assertRaises(S3ResponseError):
            self.bucket.complete_multipart_upload(
                multipart.key_name, multipart.id, xml)

    @reduced_min_part_size
    def test_multipart_duplicate_upload(self):
        multipart = self.bucket.initiate_multipart_upload("the-key")
        part1 = b'0' * REDUCED_PART_SIZE
        multipart.upload_part_from_file(io.BytesIO(part1), 1)
        # same part again
        multipart.upload_part_from_file(io.BytesIO(part1), 1)
        part2 = b'1' * 1024
        multipart.upload_part_from_file(io.BytesIO(part2), 2)
        multipart.complete_upload()
        # We should get only one copy of part 1.
        self.assertEqual(
            part1 + part2,
            self.bucket.get_key("the-key").get_contents_as_string())

    def test_list_multiparts(self):
        multipart1 = self.bucket.initiate_multipart_upload("one-key")
        multipart2 = self.bucket.initiate_multipart_upload("two-key")
        uploads = self.bucket.get_all_multipart_uploads()
        self.assertEqual(2, len(uploads))
        self.assertEqual(
            {'one-key': multipart1.id, 'two-key': multipart2.id},
            dict([(u.key_name, u.id) for u in uploads]))
        multipart2.cancel_upload()
        uploads = self.bucket.get_all_multipart_uploads()
        self.assertEqual(1, len(uploads))
        self.assertEqual("one-key", uploads[0].key_name)
        multipart1.cancel_upload()
        uploads = self.bucket.get_all_multipart_uploads()
        self.assertEqual(0, len(uploads))

    def test_key_save_to_missing_bucket(self):
        bucket = self.conn.get_bucket('missing', validate=False)
        key = self.save("the-key", bucket=bucket)
        with self.assertRaises(S3ResponseError):
            key.set_contents_from_string("foobar")

    def test_missing_key(self):
        self.assertIsNone(self.bucket.get_key("the-key"))

    def test_missing_key_urllib2(self):
        with self.assertRaises(HTTPError):
            urlopen("http://foobar.s3.amazonaws.com/the-key")

    def test_empty_key(self):
        self.save("the-key", "")

        key = self.bucket.get_key("the-key")
        self.assertEqual(0, key.size)
        self.assertEqual(b'', key.get_contents_as_string())

    def test_empty_key_set_on_existing_key(self):
        self.save("the-key", "foobar")

        key = self.bucket.get_key("the-key")
        self.assertEqual(6, key.size)
        self.assertEqual(
            b'foobar',
            key.get_contents_as_string())

        key.set_contents_from_string("")
        self.assertEqual(
            b'',
            self.bucket.get_key("the-key").get_contents_as_string())

    def test_large_key_save(self):
        self.save("the-key", "foobar" * 100000)
        self.assertEqual(
            b'foobar' * 100000,
            self.bucket.get_key("the-key").get_contents_as_string())

    def test_copy_key(self):
        self.save("the-key", "some value")

        self.bucket.copy_key('new-key', 'mybucket', 'the-key')
        self.assertEqual(
            b"some value",
            self.bucket.get_key("the-key").get_contents_as_string())

    def test_copy_key_with_version(self):
        self.bucket.configure_versioning(versioning=True)
        key = self.save("the-key", "some value")
        key.set_contents_from_string("another value")

        self.bucket.copy_key(
            'new-key', 'mybucket', 'the-key', src_version_id='0')

        self.assertEqual(
            b"another value",
            self.bucket.get_key("the-key").get_contents_as_string())
        self.assertEqual(
            b"some value",
            self.bucket.get_key("new-key").get_contents_as_string())

    def test_set_metadata(self):
        key = self.save("the-key")
        key.set_metadata('md', 'Metadatastring')
        key.set_contents_from_string("some value")

        self.assertEqual(
            'Metadatastring',
            self.bucket.get_key('the-key').get_metadata('md'))

    def test_copy_key_replace_metadata(self):
        key = self.save("the-key")
        key.set_metadata('md', 'Metadatastring')
        key.set_contents_from_string("some value")

        self.bucket.copy_key(
            'new-key', 'mybucket', 'the-key',
            metadata={'momd': 'Mometadatastring'})

        self.assertIsNone(
            self.bucket.get_key("new-key").get_metadata('md'))
        self.assertEqual(
            'Mometadatastring',
            self.bucket.get_key("new-key").get_metadata('momd'))

    @freeze_time("2012-01-01 12:00:00")
    def test_last_modified(self):
        self.save("the-key", "some value")

        rs = self.bucket.get_all_keys()
        self.assertEqual(
            '2012-01-01T12:00:00.000Z',
            rs[0].last_modified)

        self.assertEqual(
            'Sun, 01 Jan 2012 12:00:00 GMT',
            self.bucket.get_key("the-key").last_modified)

    def test_missing_bucket(self):
        with self.assertRaises(S3ResponseError):
            self.conn.get_bucket('missing')

    def test_bucket_with_dash(self):
        with self.assertRaises(S3ResponseError):
            self.conn.get_bucket('mybucket-test')

#    def test_create_existing_bucket(self):
#        "Trying to create a bucket that already exists should raise an Error"
#        with self.assertRaises(S3CreateError):
#            self.conn.create_bucket('mybucket')

    def test_create_existing_bucket_in_us_east_1(self):
        """Trying to create a bucket that already exists in us-east-1 returns
        the bucket

        http://docs.aws.amazon.com/AmazonS3/latest/API/ErrorResponses.html
        Your previous request to create the named bucket succeeded and you
        already own it. You get this error in all AWS regions except US
        Standard, us-east-1. In us-east-1 region, you will get 200 OK, but it
        is no-op (if bucket exists it Amazon S3 will not do anything).
        """
        conn = boto.s3.connect_to_region("us-east-1")
        conn.create_bucket("foobar")
        bucket = conn.create_bucket("foobar")
        self.assertEqual("foobar", bucket.name)

    def test_other_region(self):
        conn = S3Connection(
            'key', 'secret', host='s3-website-ap-southeast-2.amazonaws.com')
        conn.create_bucket("foobar")
        self.assertEqual(
            [], list(conn.get_bucket("foobar").get_all_keys()))

    def test_bucket_deletion(self):
        self.save("the-key", "some value")

        # Try to delete a bucket that still has keys
        with self.assertRaises(S3ResponseError):
            self.conn.delete_bucket("mybucket")

        self.bucket.delete_key("the-key")
        self.conn.delete_bucket("mybucket")

        # Get non-existing bucket
        with self.assertRaises(S3ResponseError):
            self.conn.get_bucket("mybucket")

        # Delete non-existant bucket
        with self.assertRaises(S3ResponseError):
            self.conn.delete_bucket("mybucket")

    def test_get_all_buckets(self):
        self.conn.create_bucket("foobar")
        self.conn.create_bucket("foobar2")
        buckets = self.conn.get_all_buckets()
        self.assertEqual(3, len(buckets))

    def test_post_to_bucket(self):
        requests.post("https://s3.amazonaws.com/mybucket", {
            'key': 'the-key',
            'file': 'nothing'
        })
        self.assertEqual(
            b'nothing',
            self.bucket.get_key('the-key').get_contents_as_string())

    def test_post_with_metadata_to_bucket(self):
        requests.post("https://s3.amazonaws.com/mybucket", {
            'key': 'the-key',
            'file': 'nothing',
            'x-amz-meta-test': 'metadata'
        })
        self.assertEqual(
            'metadata',
            self.bucket.get_key('the-key').get_metadata('test'))

    def test_delete_missing_key(self):
        deleted_key = self.bucket.delete_key("mybucket")
        self.assertEqual("mybucket", deleted_key.key)

    def test_delete_keys(self):
        self.save("file1", "abc")
        self.save("file2", "abc")
        self.save("file3", "abc")
        self.save("file4", "abc")

        result = self.bucket.delete_keys(['file2', 'file3'])
        self.assertEqual(2, len(result.deleted))
        self.assertEqual(0, len(result.errors))
        keys = self.bucket.get_all_keys()
        self.assertEqual(2, len(keys))
        self.assertEqual('file1', keys[0].name)

    def test_delete_keys_with_invalid(self):
        self.save("file1", "abc")
        self.save("file2", "abc")
        self.save("file3", "abc")
        self.save("file4", "abc")

        result = self.bucket.delete_keys(['abc', 'file3'])

        self.assertEqual(1, len(result.deleted))
        self.assertEqual(1, len(result.errors))
        keys = self.bucket.get_all_keys()
        self.assertEqual(3, len(keys))
        self.assertEqual('file1', keys[0].name)

    def test_bucket_method_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            requests.patch("https://s3.amazonaws.com/foobar")

    def test_key_method_not_implemented(self):
        self.conn.create_bucket("foobar")
        with self.assertRaises(NotImplementedError):
            requests.post("https://s3.amazonaws.com/foobar/foo")

    def test_bucket_name_with_dot(self):
        bucket = self.conn.create_bucket('firstname.lastname')
        self.save('somekey', 'somedata', bucket)

    def test_key_with_special_characters(self):
        self.save('test_list_keys_2/x?y', 'value1')

        key_list = self.bucket.list('test_list_keys_2/', '/')
        keys = [x for x in key_list]
        self.assertEqual(
            "test_list_keys_2/x?y", keys[0].name)

    def test_unicode_key_with_slash(self):
        self.save('/the-key-unîcode/test', 'value')

        key = self.bucket.get_key("/the-key-unîcode/test")
        self.assertEqual(
            b'value', key.get_contents_as_string())

    def test_bucket_key_listing_order(self):
        prefix = 'toplevel/'

        names = ['x/key', 'y.key1', 'y.key2', 'y.key3', 'x/y/key', 'x/y/z/key']
        for name in names:
            self.save(prefix + name, 'somedata')

        delimiter = None
        self.assertEqual([
            'toplevel/x/key', 'toplevel/x/y/key', 'toplevel/x/y/z/key',
            'toplevel/y.key1', 'toplevel/y.key2', 'toplevel/y.key3'
            ],
            [x.name for x in self.bucket.list(prefix, delimiter)])

        delimiter = '/'
        self.assertEqual(
            ['toplevel/y.key1', 'toplevel/y.key2', 'toplevel/y.key3',
            'toplevel/x/'],
            [x.name for x in self.bucket.list(prefix, delimiter)])

        # Test delimiter with no prefix
        delimiter = '/'
        self.assertEqual(
            ['toplevel/'],
            [x.name for x in self.bucket.list(prefix=None, delimiter=delimiter)])

        delimiter = None
        self.assertEqual(
            [u'toplevel/x/key', u'toplevel/x/y/key', u'toplevel/x/y/z/key'],
            [x.name for x in self.bucket.list(prefix + 'x', delimiter)])

        delimiter = '/'
        self.assertEqual(
            [u'toplevel/x/'],
            [x.name for x in self.bucket.list(prefix + 'x', delimiter)])

    def test_key_with_reduced_redundancy(self):
        key = self.save('test_rr_key')
        key.set_contents_from_string('value1', reduced_redundancy=True)
        # we use the bucket iterator because of:
        # https:/github.com/boto/boto/issues/1173
        self.assertEqual(
            'REDUCED_REDUNDANCY',
            list(self.bucket)[0].storage_class)

    def test_copy_key_reduced_redundancy(self):
        key = self.save("the-key", "some value")

        self.bucket.copy_key(
            'new-key', 'mybucket', 'the-key',
            storage_class='REDUCED_REDUNDANCY')

        # we use the bucket iterator because of:
        # https:/github.com/boto/boto/issues/1173
        keys = dict([(k.name, k) for k in self.bucket])
        self.assertEqual(
            'REDUCED_REDUNDANCY',
            keys['new-key'].storage_class)
        self.assertEqual(
            "STANDARD",
            keys['the-key'].storage_class)

    @freeze_time("2012-01-01 12:00:00")
    def test_restore_key(self):
        key = self.save("the-key", "some value")
        self.assertIsNone(
            list(self.bucket)[0].ongoing_restore)
        key.restore(1)
        key = self.bucket.get_key('the-key')
        self.assertIsNotNone(key.ongoing_restore)
        self.assertFalse(key.ongoing_restore)
        self.assertEqual(
            "Mon, 02 Jan 2012 12:00:00 GMT",
            key.expiry_date)
        key.restore(2)
        key = self.bucket.get_key('the-key')
        self.assertIsNotNone(key.ongoing_restore)
        self.assertFalse(key.ongoing_restore)
        self.assertEqual(
            "Tue, 03 Jan 2012 12:00:00 GMT",
            key.expiry_date)

    @freeze_time("2012-01-01 12:00:00")
    def test_restore_key_headers(self):
        key = self.save("the-key", "some value")
        key.restore(1, headers={'foo': 'bar'})
        key = self.bucket.get_key('the-key')
        self.assertIsNotNone(key.ongoing_restore)
        self.assertFalse(key.ongoing_restore)
        self.assertEqual(
            "Mon, 02 Jan 2012 12:00:00 GMT",
            key.expiry_date)

    def test_get_versioning_status(self):
        self.assertEqual({}, self.bucket.get_versioning_status())

        self.bucket.configure_versioning(versioning=True)
        self.assertEqual(
            'Enabled', self.bucket.get_versioning_status()['Versioning'])

        self.bucket.configure_versioning(versioning=False)
        d = self.bucket.get_versioning_status()
        self.assertEqual('Suspended', d['Versioning'])

    def test_key_version(self):
        self.bucket.configure_versioning(versioning=True)

        key = self.save('the-key')
        self.assertIsNone(key.version_id)
        key.set_contents_from_string('some string')
        self.assertEqual('0', key.version_id)
        key.set_contents_from_string('some string')
        self.assertEqual('1', key.version_id)

        key = self.bucket.get_key('the-key')
        self.assertEqual('1', key.version_id)

    def test_list_versions(self):
        self.bucket.configure_versioning(versioning=True)

        key = self.save('the-key')
        self.assertIsNone(key.version_id)
        key.set_contents_from_string(b'Version 1')
        self.assertEqual('0', key.version_id)
        key.set_contents_from_string(b'Version 2')
        self.assertEqual('1', key.version_id)

        versions = list(self.bucket.list_versions())
        self.assertEqual(2, len(versions))

        self.assertEqual('the-key', versions[0].name)
        self.assertEqual('0', versions[0].version_id)
        self.assertEqual(b'Version 1', versions[0].get_contents_as_string())

        self.assertEqual('the-key', versions[1].name)
        self.assertEqual('1', versions[1].version_id)
        self.assertEqual(b'Version 2', versions[1].get_contents_as_string())

    def test_acl_setting(self):
        key = self.save('test.txt', b'imafile')
        key.make_public()

        key = self.bucket.get_key('test.txt')
        self.assertEqual(b'imafile', key.get_contents_as_string())

        grants = key.get_acl().acl.grants
        self.assertTrue(
            any(g.uri == ALL_USERS_GRANTEE.uri and
                g.permission == 'READ' for g in grants))

    def test_acl_setting_via_headers(self):
        key = self.save('test.txt')
        key.set_contents_from_string(b'imafile', headers={
            'x-amz-grant-full-control': 'uri="%s"' % ALL_USERS_GRANTEE.uri
        })

        key = self.bucket.get_key('test.txt')
        self.assertEqual(b'imafile', key.get_contents_as_string())

        grants = key.get_acl().acl.grants
        self.assertTrue(
            any(g.uri == ALL_USERS_GRANTEE.uri and
                g.permission == 'FULL_CONTROL' for g in grants))

    def test_acl_switching(self):
        key = self.save('test.txt')
        key.set_contents_from_string(b'imafile', policy='public-read')
        key.set_acl('private')

        grants = key.get_acl().acl.grants
        self.assertFalse(
            any(g.uri == ALL_USERS_GRANTEE.uri and
                g.permission == 'READ' for g in grants))

    def test_bucket_acl_setting(self):
        self.bucket.make_public()

        grants = self.bucket.get_acl().acl.grants
        self.assertTrue(
            any(g.uri == ALL_USERS_GRANTEE.uri and
                g.permission == 'READ' for g in grants))

    def test_bucket_acl_switching(self):
        self.bucket.make_public()
        self.bucket.set_acl('private')

        grants = self.bucket.get_acl().acl.grants
        self.assertFalse(
            any(g.uri == ALL_USERS_GRANTEE and
                g.permission == 'READ' for g in grants))

    def test_unicode_key(self):
        key = self.save(u'こんにちは.jpg', 'Hello world!')
        self.assertTrue(
            [key.key],
            [listed_key.key for listed_key in self.bucket.list()])
        fetched_key = self.bucket.get_key(key.key)
        self.assertTrue(key.key, fetched_key.key)
        self.assertTrue(
            'Hello world!',
            fetched_key.get_contents_as_string().decode("utf-8"))

    def test_unicode_value(self):
        key = self.save('some_key', u'こんにちは.jpg')
        list(self.bucket.list())
        key = self.bucket.get_key(key.key)
        self.assertTrue(
            u'こんにちは.jpg',
            key.get_contents_as_string().decode("utf-8"))

    def test_setting_content_encoding(self):
        key = self.save("keyname")
        key.set_metadata("Content-Encoding", "gzip")
        key.set_contents_from_string("abcdef")

        key = self.bucket.get_key("keyname")
        self.assertEqual("gzip", key.content_encoding)

# XXX: This does not work now that I switched to path-based buckets.
#    def test_bucket_location(self):
#        conn = boto.s3.connect_to_region(
#            "us-west-2",
#            calling_format=boto.s3.connection.OrdinaryCallingFormat())
#        bucket = conn.create_bucket('mybucket2')
#        self.assertEqual("us-west-2", bucket.get_location())

    def test_ranged_get(self):
        rep = b"0123456789"
        key = self.save('bigkey', rep * 10)

        def contentsEqual(data, range):
            self.assertEqual(
                data,
                key.get_contents_as_string(headers={'Range': 'bytes='+range}))

        # Implicitly bounded range requests.
        contentsEqual(rep * 10, '0-')
        contentsEqual(rep * 5, '50-')
        contentsEqual(b'9', '99-')

        # Explicitly bounded range requests starting from the first byte.
        contentsEqual(b'0', '0-0')
        contentsEqual(rep * 5, '0-49')
        contentsEqual(rep * 10, '0-99')
        contentsEqual(rep * 10, '0-100')
        contentsEqual(rep * 10, '0-700')

        # Explicitly bounded range requests starting from the / a middle byte.
        contentsEqual(rep[:5], '50-54')
        contentsEqual(rep * 5, '50-99')
        contentsEqual(rep * 5, '50-100')
        contentsEqual(rep * 5, '50-700')

        # Explicitly bounded range requests starting from the last byte.
        contentsEqual(b'9', '99-99')
        contentsEqual(b'9', '99-100')
        contentsEqual(b'9', '99-700')

        # Suffix range requests.
        contentsEqual(b'9', '-1')
        contentsEqual(rep * 6, '-60')
        contentsEqual(rep * 10, '-100')
        contentsEqual(rep * 10, '-101')
        contentsEqual(rep * 10, '-700')

        self.assertEqual(100, key.size)

    def test_policy(self):
        policy = json.dumps({
            "Version": "2012-10-17",
            "Id": "PutObjPolicy",
            "Statement": [
                {
                    "Sid": "DenyUnEncryptedObjectUploads",
                    "Effect": "Deny",
                    "Principal": "*",
                    "Action": "s3:PutObject",
                    "Resource": "arn:aws:s3:::mybucket/*",
                    "Condition": {
                        "StringNotEquals": {
                            "s3:x-amz-server-side-encryption": "aws:kms"
                        }
                    }
                }
            ]
        })

        with self.assertRaises(S3ResponseError) as err:
            self.bucket.get_policy()

        ex = err.exception
        self.assertIsNone(ex.box_usage)
        self.assertEqual('NoSuchBucketPolicy', ex.error_code)
        self.assertEqual('The bucket policy does not exist', ex.message)
        self.assertEqual('Not Found', ex.reason)
        self.assertIsNone(ex.resource)
        self.assertEqual(404, ex.status)
        self.assertIn('mybucket', ex.body)
        self.assertIsNotNone(ex.request_id)

        self.assertTrue(self.bucket.set_policy(policy))
        self.assertEqual(
            policy, self.bucket.get_policy().decode('utf-8'))

        self.bucket.delete_policy()
        with self.assertRaises(S3ResponseError):
            self.bucket.get_policy()

    TEST_XML = """\
    <?xml version="1.0" encoding="UTF-8"?>
    <ns0:WebsiteConfiguration xmlns:ns0="http://s3.amazonaws.com/doc/2006-03-01/">
        <ns0:IndexDocument>
            <ns0:Suffix>index.html</ns0:Suffix>
        </ns0:IndexDocument>
        <ns0:RoutingRules>
            <ns0:RoutingRule>
                <ns0:Condition>
                    <ns0:KeyPrefixEquals>test/testing</ns0:KeyPrefixEquals>
                </ns0:Condition>
                <ns0:Redirect>
                    <ns0:ReplaceKeyWith>test.txt</ns0:ReplaceKeyWith>
                </ns0:Redirect>
            </ns0:RoutingRule>
        </ns0:RoutingRules>
    </ns0:WebsiteConfiguration>
    """

    def test_website_configuration_xml(self):
        self.bucket.set_website_configuration_xml(self.TEST_XML)
        self.assertEqual(
            self.TEST_XML,
            self.bucket.get_website_configuration_xml())

    def test_key_with_trailing_slash_in_ordinary_calling_format(self):
        bucket = self.conn.create_bucket('test_bucket_name')

        key_name = 'key_with_slash/'

        key = Key(bucket, key_name)
        key.set_contents_from_string('some value')

        self.assertIn(key_name, [k.name for k in bucket.get_all_keys()])
