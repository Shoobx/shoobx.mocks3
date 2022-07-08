###############################################################################
#
# Copyright 2016 by Shoobx, Inc.
#
###############################################################################
"""Shoobx S3 Backend
"""

import functools
import json
import shutil
import tempfile
import unittest
from unittest import mock

import boto3
import botocore
import requests
from botocore.client import ClientError, Config
from freezegun import freeze_time
from moto.core.models import MockAWS
from moto.s3.models import ALL_USERS_GRANTEE
from six.moves.urllib.error import HTTPError
from six.moves.urllib.request import urlopen

from shoobx.mocks3 import models

REDUCED_PART_SIZE = 256


def reduced_min_part_size(f):
    """ speed up tests by temporarily making the multipart minimum part size
        small
    """
    from moto import settings as msettings
    orig_size = msettings.S3_UPLOAD_PART_MIN_SIZE

    @functools.wraps(f)
    def wrapped(self, *args, **kwargs):
        try:
            msettings.S3_UPLOAD_PART_MIN_SIZE = REDUCED_PART_SIZE
            return f(self, *args, **kwargs)
        finally:
            msettings.S3_UPLOAD_PART_MIN_SIZE = orig_size  # noqa
    return wrapped


class BotoTestCase(unittest.TestCase):

    def setUp(self):
        self.mock_aws = MockAWS(models.s3_backends)
        self.mock_aws.start()
        self._dir = tempfile.mkdtemp()
        self.data_dir_patch = mock.patch(
            'shoobx.mocks3.models.ShoobxS3Backend.directory',
            self._dir)
        self.data_dir_patch.start()
        self.s3 = boto3.client(
            's3', region_name='us-east-1',
            config=Config(s3={'addressing_style': 'path'}))
        self.s3.create_bucket(Bucket='mybucket')
        # Create s3 bucket resource using same cfg for simpler tests
        self.s3_resource = boto3.resource(
            's3', region_name='us-east-1',
            config=Config(s3={'addressing_style': 'path'}))
        self.bucket = self.s3_resource.Bucket('mybucket')

    def tearDown(self):
        self.data_dir_patch.stop()
        shutil.rmtree(self._dir)
        self.mock_aws.stop()

    def store_key(
        self, name, body, bucket='mybucket', storageClass="STANDARD"
    ):
        self.s3.put_object(
            Bucket=bucket, Key=name, Body=body, StorageClass=storageClass
        )

    def retrieve_key(self, name, bucket='mybucket'):
        return self.s3.get_object(Bucket=bucket, Key=name)['Body']

    def test_save(self):
        self.store_key('steve', 'is awesome')

        body = self.retrieve_key('steve')
        self.assertEqual("is awesome", body.read().decode("utf-8"))

    def test_key_etag(self):
        self.store_key('steve', b'is awesome')
        resp = self.s3.get_object(Bucket='mybucket', Key='steve')
        self.assertEqual(
            '"d32bda93738f7e03adb22e66c90fbc04"', resp['ETag'])

#    def test_boto3_list_keys_xml_escaped(self):
#        key_name = u'Q&A.txt'
#        self.s3.put_object(Bucket='mybucket', Key=key_name, Body=b'is awesome')
#        resp = self.s3.list_objects_v2(Bucket='mybucket', Prefix=key_name)
#        self.assertEqual(key_name, resp['Contents'][0]['Key'])

    def test_boto3_bucket_create(self):
        s3 = boto3.resource(
            's3', region_name='us-east-1',
            config=Config(s3={'addressing_style': 'path'}))
        s3.create_bucket(Bucket="blah")

        s3.Object('blah', 'hello.txt').put(Body="some text")

        body = s3.Object('blah', 'hello.txt').get()['Body']
        self.assertEqual("some text", body.read().decode("utf-8"))

    def test_boto3_bucket_create_eu_central(self):
        s3 = boto3.resource('s3', region_name='eu-central-1',
            config=Config(s3={'addressing_style': 'path'}))
        s3.create_bucket(
            Bucket="blah",
            CreateBucketConfiguration={
                'LocationConstraint': 'eu-central-1'
            }
        )

        s3.Object('blah', 'hello.txt').put(Body="some text")

        body = s3.Object('blah', 'hello.txt').get()['Body']
        self.assertEqual("some text", body.read().decode("utf-8"))

    def test_boto3_head_object(self):
        s3 = boto3.resource('s3', region_name='us-east-1',
            config=Config(s3={'addressing_style': 'path'}))
        s3.create_bucket(Bucket="blah")

        s3.Object('blah', 'hello.txt').put(Body="some text")

        s3.Object('blah', 'hello.txt').meta.client.head_object(
            Bucket='blah', Key='hello.txt')

        with self.assertRaises(ClientError):
            s3.Object('blah', 'hello2.txt').meta.client.head_object(
                Bucket='blah', Key='hello_bad.txt')

    def test_boto3_get_object(self):
        s3 = boto3.resource('s3', region_name='us-east-1',
            config=Config(s3={'addressing_style': 'path'}))
        s3.create_bucket(Bucket="blah")

        s3.Object('blah', 'hello.txt').put(Body="some text")

        s3.Object('blah', 'hello.txt').meta.client.head_object(
            Bucket='blah', Key='hello.txt')

        with self.assertRaises(ClientError) as err:
            s3.Object('blah', 'hello2.txt').get()

        self.assertEqual('NoSuchKey', err.exception.response['Error']['Code'])

    def test_boto3_head_object_with_versioning(self):
        s3 = boto3.resource('s3', region_name='us-east-1',
            config=Config(s3={'addressing_style': 'path'}))
        bucket = self.bucket
        bucket.Versioning().enable()

        obj = s3.Object('mybucket', 'hello.txt')
        old_content = 'some text'
        new_content = 'some new text'
        obj.put(Body=old_content)
        obj.put(Body=new_content)

        head_object = obj.meta.client.head_object(
            Bucket='mybucket', Key='hello.txt')
        self.assertEqual('1', head_object['VersionId'])
        self.assertEqual(len(new_content), head_object['ContentLength'])

        old_head_object = obj.meta.client.head_object(
            Bucket='mybucket', Key='hello.txt', VersionId='0')
        self.assertEqual(
            '0',
            old_head_object['VersionId'])
        self.assertEqual(
            len(old_content),
            old_head_object['ContentLength'])

    def create_multipart_upload(self, key, bucket='mybucket', metadata={}):
        upload_id = self.s3.create_multipart_upload(
            Bucket=bucket, Key=key, Metadata=metadata)['UploadId']
        return upload_id

    def upload_part(self, upload_id, key, body, part_number, bucket='mybucket'):
        etag = self.s3.upload_part(Bucket=bucket, Key=key,
                                   PartNumber=part_number,
                                   UploadId=upload_id, Body=body)['ETag']
        return etag

    def complete_multipart_upload(self, uid, key, etags, bucket='mybucket'):
        self.s3.complete_multipart_upload(
            Bucket=bucket, Key=key, UploadId=uid,
            MultipartUpload={'Parts': [{'ETag': etag, 'PartNumber': i}
                                       for i, etag in enumerate(etags, 1)]})

    def test_multipart_upload_too_small(self):
        upload_id = self.create_multipart_upload("the-key")
        etags = [self.upload_part(upload_id, 'the-key', body, pn) for
                 pn, body in enumerate([b'hello', b'world'], 1)]
        with self.assertRaises(botocore.exceptions.ClientError):
            # Multipart with total size under 5MB is refused
            self.complete_multipart_upload(upload_id, 'the-key', etags)

    @reduced_min_part_size
    def test_multipart_upload(self):
        upload_id = self.create_multipart_upload("the-key")
        part1 = b'0' * REDUCED_PART_SIZE
        # last part, can be less than 5 MB
        part2 = b'1'
        etags = [self.upload_part(upload_id, 'the-key', body, pn) for
                 pn, body in enumerate([part1, part2], 1)]
        self.complete_multipart_upload(upload_id, 'the-key', etags)
        body = self.retrieve_key('the-key')
        self.assertEqual(part1 + part2, body.read())

    @reduced_min_part_size
    def test_multipart_upload_out_of_order(self):
        upload_id = self.create_multipart_upload("the-key")
        # last part, can be less than 5 MB
        part2 = b'1' * REDUCED_PART_SIZE
        part1 = b'0' * REDUCED_PART_SIZE
        etags = [self.upload_part(upload_id, 'the-key', body, pn) for
                 pn, body in [(4, part2), (2, part1)]]
        self.s3.complete_multipart_upload(
            Bucket='mybucket', Key='the-key', UploadId=upload_id,
            MultipartUpload={'Parts': [{'ETag': etags[1], 'PartNumber': 2},
                                       {'ETag': etags[0], 'PartNumber': 4}]})
        body = self.retrieve_key('the-key')
        self.assertEqual(part1 + part2, body.read())

    @reduced_min_part_size
    def test_multipart_upload_with_headers(self):
        upload_id = self.create_multipart_upload("the-key",
                                                 metadata={"foo": "bar"})
        part1 = b'0' * 10
        etag = self.upload_part(upload_id, 'the-key', part1, 1)
        self.complete_multipart_upload(upload_id, 'the-key', [etag])
        md = self.s3.get_object(Bucket='mybucket', Key='the-key')['Metadata']
        self.assertEqual({"foo": "bar"}, md)

    @reduced_min_part_size
    def test_multipart_upload_with_part_copy(self):
        self.store_key("original-key", "key_value")
        upload_id = self.create_multipart_upload("the-key")
        part1 = b'0' * REDUCED_PART_SIZE
        etag1 = self.upload_part(upload_id, 'the-key', part1, 1)
        etag2 = self.s3.upload_part_copy(
            Bucket='mybucket', Key='the-key', UploadId=upload_id, PartNumber=2,
            CopySource={'Bucket': 'mybucket', 'Key': 'original-key'},
            CopySourceRange='0-3')['CopyPartResult']['ETag']
        self.complete_multipart_upload(upload_id, 'the-key', [etag1, etag2])
        body = self.retrieve_key('the-key')
        self.assertEqual(part1 + b"key_", body.read())

    @reduced_min_part_size
    def test_multipart_upload_abort(self):
        upload_id = self.create_multipart_upload("the-key")
        part1 = b'0' * REDUCED_PART_SIZE
        self.upload_part(upload_id, 'the-key', part1, 1)
        ret = self.s3.abort_multipart_upload(
            Bucket='mybucket', Key='the-key', UploadId=upload_id)
        self.assertEqual(204, ret['ResponseMetadata']['HTTPStatusCode'])

    @reduced_min_part_size
    def test_boto3_multipart_etag(self):
        upload_id = self.s3.create_multipart_upload(
            Bucket='mybucket', Key='the-key')['UploadId']
        part1 = b'0' * REDUCED_PART_SIZE
        etags = []
        etags.append(
            self.s3.upload_part(Bucket='mybucket', Key='the-key', PartNumber=1,
                           UploadId=upload_id, Body=part1)['ETag'])
        # last part, can be less than 5 MB
        part2 = b'1'
        etags.append(
            self.s3.upload_part(Bucket='mybucket', Key='the-key', PartNumber=2,
                           UploadId=upload_id, Body=part2)['ETag'])
        self.s3.complete_multipart_upload(
            Bucket='mybucket', Key='the-key', UploadId=upload_id,
            MultipartUpload={'Parts': [{'ETag': etag, 'PartNumber': i}
                                       for i, etag in enumerate(etags, 1)]})
        # we should get both parts as the key contents
        resp = self.s3.get_object(Bucket='mybucket', Key='the-key')
        self.assertEqual(
            '"66d1a1a2ed08fd05c137f316af4ff255-2"',
            resp['ETag'])

    @reduced_min_part_size
    def test_multipart_invalid_order(self):
        upload_id = self.create_multipart_upload("the-key")
        part1 = b'0' * REDUCED_PART_SIZE
        etag1 = self.upload_part(upload_id, 'the-key', part1, 1)
        # last part, can be less than 5 MB
        part2 = b'1'
        etag2 = self.upload_part(upload_id, 'the-key', part2, 2)
        with self.assertRaises(botocore.exceptions.ClientError):
            # First part is less than 5MB and upload is refused
            self.s3.complete_multipart_upload(
                Bucket='mybucket', Key='the-key', UploadId=upload_id,
                MultipartUpload={'Parts': [{'ETag': etag2, 'PartNumber': 2},
                                           {'ETag': etag1, 'PartNumber': 1}]})

    @reduced_min_part_size
    def test_multipart_duplicate_upload(self):
        upload_id = self.create_multipart_upload("the-key")
        part1 = b'0' * REDUCED_PART_SIZE
        _ = self.upload_part(upload_id, 'the-key', part1, 1)
        # same part again
        etag1 = self.upload_part(upload_id, 'the-key', part1, 1)
        part2 = b'1' * 1024
        etag2 = self.upload_part(upload_id, 'the-key', part2, 2)
        self.complete_multipart_upload(upload_id, 'the-key', [etag1, etag2])
        # We should get only one copy of part 1.
        body = self.retrieve_key('the-key')
        self.assertEqual(part1 + part2, body.read())

    def test_list_multiparts(self):
        uid1 = self.create_multipart_upload("one-key")
        uid2 = self.create_multipart_upload("two-key")
        uploads = [u for u in self.bucket.multipart_uploads.all()]
        self.assertEqual(2, len(uploads))
        self.assertEqual(
            {'one-key': uid1, 'two-key': uid2},
            {u.object_key: u.id for u in uploads})
        for u in uploads:
            if u.object_key == 'two-key':
                u.abort()
        uploads = [u for u in self.bucket.multipart_uploads.all()]
        self.assertEqual(1, len(uploads))
        self.assertEqual("one-key", uploads[0].object_key)
        uploads[0].abort()
        uploads = [u for u in self.bucket.multipart_uploads.all()]
        self.assertEqual(0, len(uploads))

    def test_key_save_to_missing_bucket(self):
        with self.assertRaises(self.s3.exceptions.NoSuchBucket):
            self.store_key("the-key", "foobar", bucket="missing")

    def test_missing_key(self):
        with self.assertRaises(self.s3.exceptions.NoSuchKey):
            self.s3.get_object(Bucket="mybucket", Key="the-key")

    def test_missing_key_urllib2(self):
        with self.assertRaises(HTTPError):
            urlopen("http://foobar.s3.amazonaws.com/the-key")

    def test_empty_key(self):
        self.store_key("the-key", "")
        body = self.retrieve_key("the-key")
        self.assertEqual(b'', body.read())

    def test_empty_key_set_on_existing_key(self):
        self.store_key("the-key", "foobar")
        obj = self.bucket.Object("the-key")
        self.assertEqual(6, obj.content_length)
        body = obj.get()["Body"]
        self.assertEqual(b'foobar', body.read())
        obj.put(Body=b'')
        body = obj.get()["Body"]
        self.assertEqual(b'', body.read())

    def test_large_key_save(self):
        self.store_key("the-key", "foobar" * 100000)
        body = self.retrieve_key("the-key")
        self.assertEqual(b'foobar' * 100000, body.read())

    def test_copy_key(self):
        self.store_key("the-key", "some value")
        copy_source = {'Bucket': 'mybucket', 'Key': 'the-key'}
        self.bucket.copy(copy_source, 'new-key')
        body = self.retrieve_key("new-key")
        self.assertEqual("some value", body.read().decode("utf-8"))

    def test_copy_key_with_version(self):
        self.bucket.Versioning().enable()
        self.store_key("the-key", "some value")
        self.store_key("the-key", "another value")
        copy_source = {'Bucket': 'mybucket', 'Key': 'the-key', 'VersionId': '0'}
        self.bucket.copy(copy_source, 'new-key')
        body = self.retrieve_key("the-key")
        self.assertEqual(b"another value", body.read())
        body = self.retrieve_key("new-key")
        self.assertEqual(b"some value", body.read())

    def test_set_metadata(self):
        obj = self.bucket.Object("the-key")
        md = {'md': 'Metadatastring'}
        obj.put(Body=b"some value", Metadata=md)
        self.assertEqual(md, self.bucket.Object("the-key").metadata)

    def test_copy_key_replace_metadata(self):
        obj = self.bucket.Object("the-key")
        obj.put(Body=b"some value", Metadata={'md': 'Metadatastring'})
        copy_source = {'Bucket': 'mybucket', 'Key': 'the-key'}
        md = {'momd': 'Mometadatastring'}
        self.s3.copy_object(Bucket='mybucket', Key="new-key",
                            CopySource=copy_source,
                            Metadata=md, MetadataDirective='REPLACE')
        self.assertEqual(md, self.bucket.Object("new-key").metadata)

    @freeze_time("2012-01-01 12:00:00")
    def test_last_modified(self):
        self.store_key("the-key", "some value")
        os = list(self.bucket.objects.all())

        self.assertEqual(
            '2012-01-01 12:00:00+00:00',
            str(os[0].last_modified))

        self.assertEqual(
            '2012-01-01 12:00:00+00:00',
            str(self.bucket.Object("the-key").last_modified))

    def test_create_existing_bucket_in_us_east_1(self):
        """Trying to create a bucket that already exists in us-east-1 returns
        the bucket

        http://docs.aws.amazon.com/AmazonS3/latest/API/ErrorResponses.html
        Your previous request to create the named bucket succeeded and you
        already own it. You get this error in all AWS regions except US
        Standard, us-east-1. In us-east-1 region, you will get 200 OK, but it
        is no-op (if bucket exists it Amazon S3 will not do anything).
        """
        s3 = boto3.resource('s3', region_name='us-east-1')
        bucket = s3.Bucket('mybucket')
        bucket.create()
        rsp = bucket.create()
        self.assertEqual(200, rsp['ResponseMetadata']['HTTPStatusCode'])

    def test_other_region(self):
        s3 = boto3.resource(
            's3', region_name='us-east-2',
            config=Config(s3={'addressing_style': 'path'}))
        bucket = s3.Bucket("foobar")
        bucket.create(CreateBucketConfiguration={'LocationConstraint': 'us-east-2'})
        self.assertEqual([], list(bucket.objects.all()))

    def test_bucket_deletion(self):
        self.store_key("the-key", "some value")

        # Try to delete a bucket that still has keys
        with self.assertRaises(ClientError):
            self.s3.delete_bucket(Bucket="mybucket")

        self.bucket.Object("the-key").delete()
        self.bucket.delete()

        # Delete non-existant bucket
        with self.assertRaises(ClientError):
            self.bucket.delete()

    def test_list_buckets(self):
        # TBD: MockAWS doesn't return timestamps so list_bucket_fails
        def parse_ts(ts):
            ts = ts if ts else "2012-01-01 12:00:00"
            return botocore.parsers.parse_timestamp(ts)

        with mock.patch("botocore.parsers.DEFAULT_TIMESTAMP_PARSER", parse_ts):
            self.s3.create_bucket(Bucket="foobar")
            self.s3.create_bucket(Bucket="foobar2")
            buckets = self.s3.list_buckets()
            self.assertEqual(3, len(buckets['Buckets']))

    def test_post_to_bucket(self):
        requests.post(
            "https://s3.amazonaws.com/mybucket",
            {
                'key': 'the-key',
                'file': 'nothing'
            })
        body = self.retrieve_key("the-key")
        self.assertEqual(b"nothing", body.read())

    def test_post_with_metadata_to_bucket(self):
        requests.post(
            "https://s3.amazonaws.com/mybucket",
            {
                'key': 'the-key',
                'file': 'nothing',
                'x-amz-meta-test': 'metadata'
            })
        self.assertEqual(
            {'test': 'metadata'},
            self.bucket.Object("the-key").metadata)

    def test_delete_missing_key(self):
        ret = self.bucket.Object("missing").delete()
        self.assertEqual(204, ret['ResponseMetadata']['HTTPStatusCode'])

    def test_delete_keys(self):
        self.store_key("file1", "abc")
        self.store_key("file2", "abc")
        self.store_key("file3", "abc")
        self.store_key("file4", "abc")

        rsp = self.s3.delete_objects(
            Bucket="mybucket",
            Delete={'Objects': [{'Key': 'file2'}, {'Key': 'file3'}]})

        self.assertEqual(2, len(rsp['Deleted']))
        self.assertFalse('Errors' in rsp)
        osummary = list(self.bucket.objects.all())
        self.assertEqual(2, len(osummary))
        self.assertEqual('file1', osummary[0].key)

    def test_delete_keys_with_invalid(self):
        self.store_key("file1", "abc")
        self.store_key("file2", "abc")
        self.store_key("file3", "abc")
        self.store_key("file4", "abc")

        rsp = self.s3.delete_objects(
            Bucket="mybucket",
            Delete={'Objects': [{'Key': 'abc'}, {'Key': 'file3'}]})

        # Moto no longer errors when there is an invalid key
        self.assertEqual(2, len(rsp['Deleted']), "Incorrect deletion length")
        osummary = list(self.bucket.objects.all())
        self.assertEqual(3, len(osummary))
        self.assertEqual('file1', osummary[0].key)

    def test_bucket_method_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            requests.patch("https://s3.amazonaws.com/foobar")

    def test_key_method_not_implemented(self):
        self.s3.create_bucket(Bucket="foobar")
        with self.assertRaises(KeyError):
            requests.post("https://s3.amazonaws.com/foobar/foo")

    def test_bucket_name_with_dot(self):
        self.s3.create_bucket(Bucket='firstname.lastname')
        self.store_key('somekey', 'somedata', bucket='firstname.lastname')

    def test_key_with_special_characters(self):
        self.store_key('test_list_keys_2/x?y', 'value1')
        osummary = list(self.bucket.objects.all())
        self.assertEqual('test_list_keys_2/x?y', osummary[0].key)

    def test_unicode_key_with_slash(self):
        self.store_key('/the-key-unîcode/test', 'value')
        body = self.retrieve_key('/the-key-unîcode/test')
        self.assertEqual(b"value", body.read())

    def test_bucket_key_listing_order(self):
        prefix = 'toplevel/'

        names = ['x/key', 'y.key1', 'y.key2', 'y.key3', 'x/y/key', 'x/y/z/key']
        for name in names:
            self.store_key(prefix + name, 'somedata')

        rsp = self.s3.list_objects(Bucket='mybucket', Prefix=prefix)
        self.assertEqual([
            'toplevel/x/key', 'toplevel/x/y/key', 'toplevel/x/y/z/key',
            'toplevel/y.key1', 'toplevel/y.key2', 'toplevel/y.key3'
            ],
            [x['Key'] for x in rsp['Contents']])

        rsp = self.s3.list_objects(
            Bucket='mybucket', Prefix=prefix, Delimiter='/')
        self.assertEqual(
            ['toplevel/y.key1', 'toplevel/y.key2', 'toplevel/y.key3'],
            [x['Key'] for x in rsp['Contents']])
        self.assertEqual(
            ['toplevel/x/'],
            [x['Prefix'] for x in rsp['CommonPrefixes']])

        # Test delimiter with no prefix
        rsp = self.s3.list_objects(Bucket='mybucket', Delimiter='/')
        self.assertEqual(
            ['toplevel/'],
            [x['Prefix'] for x in rsp['CommonPrefixes']])

        rsp = self.s3.list_objects(Bucket='mybucket', Prefix=prefix + 'x')
        self.assertEqual(
            ['toplevel/x/key', 'toplevel/x/y/key', 'toplevel/x/y/z/key'],
            [x['Key'] for x in rsp['Contents']])

        rsp = self.s3.list_objects(
            Bucket='mybucket', Prefix=prefix + 'x', Delimiter='/')
        self.assertEqual(
            ['toplevel/x/'],
            [x['Prefix'] for x in rsp['CommonPrefixes']])

    def test_key_with_reduced_redundancy(self):
        self.s3.put_object(
            Bucket='mybucket', Key='test_rr_key', Body='value1',
            StorageClass='REDUCED_REDUNDANCY')

        obj = self.bucket.Object('test_rr_key')
        self.assertEqual('REDUCED_REDUNDANCY', obj.storage_class)

    def test_copy_key_reduced_redundancy(self):
        self.store_key('the-key', 'some value')
        copy_source = {'Bucket': 'mybucket', 'Key': 'the-key'}
        self.s3.copy_object(Bucket='mybucket', Key="new-key",
                            CopySource=copy_source,
                            StorageClass='REDUCED_REDUNDANCY')
        self.assertEqual('REDUCED_REDUNDANCY',
                         self.bucket.Object("new-key").storage_class)
        self.assertEqual('STANDARD',
                         self.bucket.Object("the-key").storage_class)

    @freeze_time("2012-01-01 12:00:00")
    def test_restore_key(self):
        self.store_key("the-key", "some value", storageClass="GLACIER")
        self.assertIsNone(self.bucket.Object("the-key").restore)

        self.bucket.Object("the-key").restore_object(RestoreRequest={'Days': 1})
        self.assertEqual(
            'ongoing-request="false", expiry-date="Mon, 02 Jan 2012 12:00:00 GMT"',
            self.bucket.Object("the-key").restore)
        self.bucket.Object("the-key").restore_object(RestoreRequest={'Days': 2})
        self.assertEqual(
            'ongoing-request="false", expiry-date="Tue, 03 Jan 2012 12:00:00 GMT"',
            self.bucket.Object("the-key").restore)

    def test_get_versioning_status(self):
        self.assertIsNone(self.bucket.Versioning().status)
        self.bucket.Versioning().enable()
        self.assertEqual('Enabled', self.bucket.Versioning().status)
        self.bucket.Versioning().suspend()
        self.assertEqual('Suspended', self.bucket.Versioning().status)

    def test_key_version(self):
        self.bucket.Versioning().enable()
        self.store_key('the-key', 'some string')
        self.assertEqual('0', self.bucket.Object('the-key').version_id)
        self.store_key('the-key', 'some string')
        self.assertEqual('1', self.bucket.Object('the-key').version_id)

    def test_list_versions(self):
        self.bucket.Versioning().enable()
        self.store_key('the-key', b'Version 1')
        self.assertEqual('0', self.bucket.Object('the-key').version_id)
        self.store_key('the-key', b'Version 2')
        self.assertEqual('1', self.bucket.Object('the-key').version_id)
        rsp = self.s3.list_object_versions(Bucket="mybucket", Prefix="the-key")
        self.assertEqual(2, len(rsp['Versions']))
        self.assertEqual(
            [('0', 'the-key'), ('1', 'the-key')],
            sorted((v['VersionId'], v['Key']) for v in rsp['Versions']))
        rsp = self.bucket.Object('the-key').get(VersionId='0')
        self.assertEqual(b'Version 1', rsp['Body'].read())
        rsp = self.bucket.Object('the-key').get(VersionId='1')
        self.assertEqual(b'Version 2', rsp['Body'].read())

    def test_acl_setting(self):
        self.store_key('test.txt', b'imafile')
        self.bucket.Object('test.txt').Acl().put(ACL='public-read')

        rsp = self.bucket.Object('test.txt').get()
        self.assertEqual(b'imafile', rsp['Body'].read())

        grants = self.bucket.Object('test.txt').Acl().grants
        self.assertTrue(any(
            g['Grantee']['Type'] == 'Group' and
            g['Grantee']['URI'] == ALL_USERS_GRANTEE.uri and
            g['Permission'] == 'READ' for g in grants))

    def test_acl_switching(self):
        self.s3.put_object(
            Bucket='mybucket', Key='test.txt', Body=b'imafile',
            ACL='public-read')
        self.bucket.Object('test.txt').Acl().put(ACL='private')
        grants = self.bucket.Object('test.txt').Acl().grants
        self.assertFalse(any(
            g['Grantee']['Type'] == 'Group' and
            g['Grantee']['URI'] == ALL_USERS_GRANTEE.uri and
            g['Permission'] == 'READ' for g in grants))

    def test_bucket_acl_setting(self):
        self.bucket.Acl().put(ACL='public-read')
        grants = self.bucket.Acl().grants
        self.assertTrue(any(
            g['Grantee']['Type'] == 'Group' and
            g['Grantee']['URI'] == ALL_USERS_GRANTEE.uri and
            g['Permission'] == 'READ' for g in grants))

    def test_bucket_acl_switching(self):
        self.bucket.Acl().put(ACL='public-read')
        self.bucket.Acl().put(ACL='private')
        grants = self.bucket.Acl().grants
        self.assertFalse(any(
            g['Grantee']['Type'] == 'Group' and
            g['Grantee']['URI'] == ALL_USERS_GRANTEE.uri and
            g['Permission'] == 'READ' for g in grants))

    def test_unicode_key(self):
        self.store_key('こんにちは.jpg', 'Hello world!')
        osummary = list(self.bucket.objects.all())
        self.assertEqual('こんにちは.jpg', osummary[0].key)
        body = self.retrieve_key('こんにちは.jpg')
        self.assertEqual(b'Hello world!', body.read())

    def test_unicode_value(self):
        self.store_key('some_key', 'こんにちは.jpg')
        body = self.retrieve_key('some_key')
        self.assertEqual('こんにちは.jpg', body.read().decode("utf-8"))

    def test_setting_content_encoding(self):
        obj = self.bucket.Object("keyname")
        obj.put(Body=b"some value", ContentEncoding="gzip")
        self.assertEqual("gzip", self.bucket.Object("keyname").content_encoding)

    def test_ranged_get(self):
        rep = b"0123456789"
        self.store_key("bigkey", rep * 10)

        def contentsEqual(data, range):
            rsp = self.bucket.Object("bigkey").get(Range='bytes=' + range)
            self.assertEqual(
                data,
                rsp["Body"].read())

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

        self.assertEqual(100, self.bucket.Object("bigkey").content_length)

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

        with self.assertRaises(ClientError) as exc:
            self.bucket.Policy().policy

        rsp = exc.exception.response
        err = rsp['Error']
        self.assertEqual('NoSuchBucketPolicy', err['Code'])
        self.assertEqual('The bucket policy does not exist', err['Message'])
        self.assertEqual('mybucket', err['BucketName'])
        self.assertEqual(404, rsp['ResponseMetadata']['HTTPStatusCode'])

        self.assertTrue(self.bucket.Policy().put(Policy=policy))
        self.assertEqual(
            policy, self.bucket.Policy().policy)

        self.bucket.Policy().delete()
        with self.assertRaises(ClientError):
            self.bucket.Policy().policy

    def test_website_configuration(self):
        cfg = {
                'IndexDocument': {
                    'Suffix': 'index.html'
                },
                'RoutingRules': [
                    {
                        'Condition': {
                            'KeyPrefixEquals': 'test/testing'
                        },
                        'Redirect': {
                            'ReplaceKeyWith': 'test.txt'
                        }
                    },
                ]
            }
        self.bucket.Website().put(WebsiteConfiguration=cfg)
        self.assertEqual(
            cfg['IndexDocument'],
            self.bucket.Website().index_document)
        self.assertEqual(
            cfg['RoutingRules'],
            self.bucket.Website().routing_rules)

    def test_key_with_trailing_slash_in_ordinary_calling_format(self):
        key_name = 'key_with_slash/'
        self.store_key(key_name, 'some value')
        osummary = list(self.bucket.objects.all())
        self.assertIn(key_name, [s.key for s in osummary])

    def test_bucket_lifecycle_rules(self):
        cfg = {
                'Rules': [
                    {
                        'Expiration': {
                            'Days': 365
                        },
                        'Transitions': [
                            {
                                'Days': 90,
                                'StorageClass': 'STANDARD_IA'
                            }
                        ],
                        'ID': 'rule1',
                        'Prefix': 'path/',
                        'Status': 'Enabled'
                    }
                ]
            }
        self.bucket.LifecycleConfiguration().put(LifecycleConfiguration=cfg)
        self.assertEqual(
            cfg['Rules'],
            self.bucket.LifecycleConfiguration().rules)
