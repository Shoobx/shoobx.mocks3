# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright 2016 by Shoobx, Inc.
#
###############################################################################
"""Shoobx S3 Backend
"""
from __future__ import unicode_literals

import boto3
import functools
import mock
import shutil
import tempfile
import unittest
from botocore.client import ClientError, Config
from moto.core.models import MockAWS

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
        self.mock_aws = MockAWS({'global': models.s3_sbx_backend})
        self.mock_aws.start()
        self._dir = tempfile.mkdtemp()
        self.data_dir_patch = mock.patch(
            'shoobx.mocks3.models.s3_sbx_backend.directory',
            self._dir)
        self.data_dir_patch.start()
        self.s3 = boto3.client(
            's3', region_name='us-east-1',
            config=Config(s3={'addressing_style': 'path'}))
        self.bucket = self.s3.create_bucket(Bucket='mybucket')

    def tearDown(self):
        self.data_dir_patch.stop()
        shutil.rmtree(self._dir)
        self.mock_aws.stop()

    def store_key(self, name, body, bucket='mybucket'):
        self.s3.put_object(Bucket=bucket, Key=name, Body=body)

    def test_boto3_key_etag(self):
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
        self.s3 = boto3.resource(
            's3', region_name='us-east-1',
            config=Config(s3={'addressing_style': 'path'}))
        self.s3.create_bucket(Bucket="blah")

        self.s3.Object('blah', 'hello.txt').put(Body="some text")

        body = self.s3.Object('blah', 'hello.txt').get()['Body']
        self.assertEqual("some text", body.read().decode("utf-8"))

    def test_boto3_bucket_create_eu_central(self):
        self.s3 = boto3.resource('s3', region_name='eu-central-1',
            config=Config(s3={'addressing_style': 'path'}))
        self.s3.create_bucket(Bucket="blah")

        self.s3.Object('blah', 'hello.txt').put(Body="some text")

        body = self.s3.Object('blah', 'hello.txt').get()['Body']
        self.assertEqual("some text", body.read().decode("utf-8"))

    def test_boto3_head_object(self):
        self.s3 = boto3.resource('s3', region_name='us-east-1',
            config=Config(s3={'addressing_style': 'path'}))
        self.s3.create_bucket(Bucket="blah")

        self.s3.Object('blah', 'hello.txt').put(Body="some text")

        self.s3.Object('blah', 'hello.txt').meta.client.head_object(
            Bucket='blah', Key='hello.txt')

        with self.assertRaises(ClientError):
            self.s3.Object('blah', 'hello2.txt').meta.client.head_object(
                Bucket='blah', Key='hello_bad.txt')

    def test_boto3_get_object(self):
        self.s3 = boto3.resource('s3', region_name='us-east-1',
            config=Config(s3={'addressing_style': 'path'}))
        self.s3.create_bucket(Bucket="blah")

        self.s3.Object('blah', 'hello.txt').put(Body="some text")

        self.s3.Object('blah', 'hello.txt').meta.client.head_object(
            Bucket='blah', Key='hello.txt')

        with self.assertRaises(ClientError) as err:
            self.s3.Object('blah', 'hello2.txt').get()

        self.assertEqual('NoSuchKey', err.exception.response['Error']['Code'])

    def test_boto3_head_object_with_versioning(self):
        self.s3 = boto3.resource('s3', region_name='us-east-1',
            config=Config(s3={'addressing_style': 'path'}))
        bucket = self.s3.create_bucket(Bucket="mybucket")
        bucket.Versioning().enable()

        obj = self.s3.Object('mybucket', 'hello.txt')
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

    @reduced_min_part_size
    def test_boto3_multipart_etag(self):
        # Create Bucket so that test can run
        self.s3 = boto3.client('s3', region_name='us-east-1',
            config=Config(s3={'addressing_style': 'path'}))
        self.s3.create_bucket(Bucket='mybucket')

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
