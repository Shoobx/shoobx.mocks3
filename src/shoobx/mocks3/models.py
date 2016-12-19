###############################################################################
#
# Copyright 2016 by Shoobx, Inc.
#
###############################################################################
"""Shoobx S3 Backend
"""
import UserDict
import json
import os
import shutil

from moto.cloudformation.exceptions import UnformattedGetAttTemplateException
from moto.s3 import models


class Key(models.FakeKey):

    def __init__(self, bucket, name):
        self.bucket = bucket
        self.name = name
        self._path = os.path.join(bucket._path, name + '.key')
        self._info_path = os.path.join(self._path, 'info.json')
        self._metadata_path = os.path.join(self._path, 'metadata.json')


    def create(self, value, storage="STANDARD", etag=None,
                 is_versioned=False, version_id=0):
        self.name = name
        self.value = value
        self.last_modified = datetime.datetime.utcnow()
        self.acl = get_canned_acl('private')
        self._storage_class = storage
        self._metadata = {}
        self._expiry = None
        self._etag = etag
        self._version_id = version_id
        self._is_versioned = is_versioned

    def copy(self, new_name=None):
        raise NotImplementedError

    def set_metadata(self, metadata, replace=False):
        if replace:
            self._metadata = {}
        self._metadata.update(metadata)

    def set_storage_class(self, storage_class):
        self._storage_class = storage_class

    def set_acl(self, acl):
        self.acl = acl

    def append_to_value(self, value):
        self.value += value
        self.last_modified = datetime.datetime.utcnow()
        self._etag = None  # must recalculate etag
        if self._is_versioned:
            self._version_id += 1
        else:
            self._is_versioned = 0

    def restore(self, days):
        self._expiry = datetime.datetime.utcnow() + datetime.timedelta(days)

    @property
    def etag(self):
        if self._etag is None:
            value_md5 = hashlib.md5()
            if isinstance(self.value, six.text_type):
                value = self.value.encode("utf-8")
            else:
                value = self.value
            value_md5.update(value)
            self._etag = value_md5.hexdigest()
        return '"{0}"'.format(self._etag)

    @property
    def last_modified_ISO8601(self):
        return iso_8601_datetime_with_milliseconds(self.last_modified)

    @property
    def last_modified_RFC1123(self):
        # Different datetime formats depending on how the key is obtained
        # https://github.com/boto/boto/issues/466
        return rfc_1123_datetime(self.last_modified)

    @property
    def metadata(self):
        return self._metadata

    @property
    def response_dict(self):
        r = {
            'etag': self.etag,
            'last-modified': self.last_modified_RFC1123,
        }
        if self._storage_class != 'STANDARD':
            r['x-amz-storage-class'] = self._storage_class
        if self._expiry is not None:
            rhdr = 'ongoing-request="false", expiry-date="{0}"'
            r['x-amz-restore'] = rhdr.format(self.expiry_date)

        if self._is_versioned:
            r['x-amz-version-id'] = self._version_id

        return r

    @property
    def size(self):
        return len(self.value)

    @property
    def storage_class(self):
        return self._storage_class

    @property
    def expiry_date(self):
        if self._expiry is not None:
            return self._expiry.strftime("%a, %d %b %Y %H:%M:%S GMT")


class VersionKeyStore(UserDict.UserDict):
    pass



class Bucket(object):

    def __init__(self, s3, name):
        self.s3 = s3
        self.name = name

        self._path = os.path.join(s3.directory, self.name + '.bucket')
        self._info_path = os.path.join(self._path, 'info.json')
        self._lifecyle_path = os.path.join(self._path, 'lifecycle.json')
        self._acl_path = os.path.join(self._path, 'acl.json')
        self._policy_path = os.path.join(self._path, 'policy.json')
        self._ws_config_path = os.path.join(
            self._path, 'website_configuration.xml')

    @property
    def info(self):
        with open(self._info_path, 'r') as file:
            return json.read(file)

    @info.setter
    def info(self, value):
        with open(self._info_path, 'w') as file:
            return json.dump(value, file)

    @property
    def keys(self):
        return VersionsKeyStore(self)

    @property
    def multiparts(self):
        raise NotImplemented(u'Multiparts are not supported at this time.')

    @property
    def location(self):
        return self.info.get('region_name')

    @property
    def is_versioned(self):
        return self.versioning_status == 'Enabled'

    @property
    def physical_resource_id(self):
        return self.name

    @property
    def rules(self):
        if not os.path.exists(self._lifecyle_path):
            return []
        with open(self._lifecyle_path, 'r') as file:
            raw_rules = json.load(file)
        rules = []
        for rule in rules:
            expiration = rule.get('Expiration')
            transition = rule.get('Transition')
            self.rules.append(models.LifecycleRule(
                id=rule.get('ID'),
                prefix=rule['Prefix'],
                status=rule['Status'],
                expiration_days=expiration.get('Days') if expiration else None,
                expiration_date=expiration.get('Date') if expiration else None,
                transition_days=transition.get('Days') if transition else None,
                transition_date=transition.get('Date') if transition else None,
                storage_class=transition['StorageClass'] if transition else None,
            ))
        return rules

    @property
    def acl(self)
        if not os.path.exists(self._acl_path):
            return []
        with open(self._acl_path, 'r') as file:
            grants = json.load(file)
        return models.FakeAcl(grants)

    @property
    def website_configuration(self)
        if not os.path.exists(self._ws_config_path):
            return []
        with open(self._ws_config_path, 'r') as file:
            return file.read()

    @property
    def versioning_status(self):
        return self.info.get('versioning_status')

    @versioning_status.setter
    def versioning_status(self, value):
        info = self.info
        info['versioning_status'] = value
        self.info = info

    @property
    def policy(self)
        if not os.path.exists(self._policy_path):
            return None
        with open(self._policy_path, 'r') as file:
            return file.read()

    @policy.setter
    def policy(self, value)
        with open(self._policy_path, 'w') as file:
            file.write(value)

    def create(self, region_name=None):
        os.mkdir(self._path)
        with open(self._info_path, 'w') as file:
            json.dump({
                'region_name': region_name
                }, file)

    def delete(self):
        shutil.rmtree(self._path)

    def set_lifecycle(self, rules):
        with open(self._lifecyle_path, 'w') as file:
            json.dump(rules, file)

    def delete_lifecycle(self):
        os.remove(self._lifecyle_path)

    def set_website_configuration(self, website_configuration):
        self.website_configuration = website_configuration

    def get_cfn_attribute(self, attribute_name):
        if attribute_name == 'DomainName':
            raise NotImplementedError(
                '"Fn::GetAtt" : [ "{0}" , "DomainName" ]"')
        elif attribute_name == 'WebsiteURL':
            raise NotImplementedError(
                '"Fn::GetAtt" : [ "{0}" , "WebsiteURL" ]"')
        raise UnformattedGetAttTemplateException()

    def set_acl(self, acl):
        with open(self._acl_path, 'w') as file:
            json.dump(acl.grants, file)


class ShoobxS3Backend(models.S3Backend):

    def __init__(self, directory):
        self.directory = directory

    def create_bucket(self, bucket_name, region_name):
        if bucket_name in self.buckets:
            raise BucketAlreadyExists(bucket=bucket_name)
        new_bucket = Bucket(
            self, name=bucket_name, region_name=region_name)
        new_bucket.create()

    def get_all_buckets(self):
        return [
            Bucket(self, fn)
            for fn in os.listdir(self.directory)
            if fn.endswtih('.bucket')]

    def get_bucket(self, bucket_name):
        bucket = Bucket(self, bucket_name)
        if not bucket.exists():
            raise models.MissingBucket(bucket=bucket_name)
        return bucket

    def delete_bucket(self, bucket_name):
        bucket = Bucket(self, bucket_name)
        return bucket.delete()


s3_sbx_backend = ShoobxS3Backend()
