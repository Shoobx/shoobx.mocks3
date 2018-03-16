###############################################################################
#
# Copyright 2016 by Shoobx, Inc.
#
###############################################################################
"""Shoobx S3 Backend
"""
import base64
import codecs
import collections
import datetime
import hashlib
import json
import os
import shutil

from moto.cloudformation.exceptions import UnformattedGetAttTemplateException
from moto.s3 import models

def _encode_name(name):
    return name.replace('/', '__sl__')

def _decode_name(name):
    return name.replace('__sl__', '/')

class _InfoProperty(object):

    def __init__(self, name):
        self.name = name

    def __get__(self, inst, cls):
        if not os.path.exists(inst._info_path):
            return None
        with open(inst._info_path, 'r') as file:
            return json.load(file).get(self.name)

    def __set__(self, inst, value):
        if isinstance(value, bytes):
            value = value.decode('utf-8')
        with open(inst._info_path, 'r') as file:
            info = json.load(file)
        info[self.name] = value
        with open(inst._info_path, 'w') as file:
            json.dump(info, file)


class _AclProperty(_InfoProperty):

    def __get__(self, inst, cls):
        raw_data = super(_AclProperty, self).__get__(inst, cls)
        if raw_data is None:
            return models.get_canned_acl('private')
        return models.FakeAcl([
            models.FakeGrant(
                [models.FakeGrantee(**grantee)
                 for grantee in grant['grantees']],
                grant['permissions'])
            for grant in raw_data
        ])

    def __set__(self, inst, value):
        with open(inst._info_path, 'r') as file:
            info = json.load(file)
        if value is None:
            info[self.name] = None
        else:
            info[self.name] = [
                {'grantees': [
                    {'id': grantee.id,
                     'uri': grantee.uri,
                     'display_name': grantee.display_name}
                     for grantee in grant.grantees],
                 'permissions': grant.permissions}
                for grant in value.grants]
        with open(inst._info_path, 'w') as file:
            json.dump(info, file)



class Key(models.FakeKey):

    _last_modified = _InfoProperty('last_modified')
    storage_class = _InfoProperty('storage_class')
    metadata = _InfoProperty('metadata')
    _etag = _InfoProperty('etag')
    expiry_date = _InfoProperty('expiry_date')
    acl = _AclProperty('acl')

    def __init__(self, bucket, name, version=0):
        self.bucket = bucket
        self.name = name
        self.version = version
        self._path = os.path.join(bucket._path, 'keys', _encode_name(name))
        self._versioned_path = os.path.join(self._path, str(version))
        self._info_path = os.path.join(self._versioned_path, 'info.json')
        self._value_path = os.path.join(self._versioned_path, 'value')

    @property
    def _version_id(self):
        return self.version

    @_version_id.setter
    def _version_id(self, value):
        self.version = value

    @property
    def value(self):
        with open(self._value_path, 'rb') as file:
            return file.read()

    @value.setter
    def value(self, data):
        if not isinstance(data, (bytes, bytearray)):
            data = data.encode('utf-8')
        with open(self._value_path, 'wb') as file:
            file.write(data)

    @property
    def etag(self):
        if self._etag is None:
            with open(self._value_path, 'rb') as file:
                self._etag = hashlib.md5(file.read()).hexdigest()
        return '"{0}"'.format(self._etag)

    @property
    def last_modified(self):
        return datetime.datetime.strptime(
            self._last_modified, "%Y-%m-%dT%H:%M:%S.%fZ")

    @property
    def last_modified_ISO8601(self):
        return self._last_modified

    @property
    def last_modified_RFC1123(self):
        # Different datetime formats depending on how the key is obtained
        # https://github.com/boto/boto/issues/466
        return models.rfc_1123_datetime(self.last_modified)

    @property
    def response_dict(self):
        r = {
            'etag': self.etag,
            'last-modified': self.last_modified_RFC1123,
            'content-length': str(len(self.value)),
            }
        if self.storage_class is not None:
            r['x-amz-storage-class'] = self.storage_class
        if self.expiry_date is not None:
            rhdr = 'ongoing-request="false", expiry-date="{0}"'
            r['x-amz-restore'] = rhdr.format(self.expiry_date)

        if self.bucket.is_versioned:
            r['x-amz-version-id'] = str(self.version)

        return r

    @property
    def size(self):
        return os.path.getsize(self._value_path)

    def exists(self):
        return os.path.exists(self._versioned_path)

    def create(self, value, storage="STANDARD", etag=None):
        if not os.path.exists(self._versioned_path):
            os.makedirs(self._versioned_path)
        self.value = value
        with open(self._info_path, 'w') as file:
            json.dump({
                'last_modified': models.iso_8601_datetime_with_milliseconds(
                    datetime.datetime.utcnow()),
                'storage_class': storage,
                'metadata': {},
                'expiry_date': None,
                'etag': etag
            }, file)
        self.set_acl(models.get_canned_acl('private'))

    def delete(self):
        shutil.rmtree(self._path)

    def copy(self, new_name=None):
        new_path = os.path.join(self.bucket._path, 'keys', new_name)
        os.mkdir(new_path)
        new_versioned_path = os.path.join(new_path, str(self.version))
        shutil.copytree(self._versioned_path, new_versioned_path)
        return Key(self.bucket, new_name, version=self.version)

    def set_metadata(self, metadata, replace=False):
        md = self.metadata if not replace else {}
        md.update(metadata)
        self.metadata = md

    def set_storage_class(self, storage_class):
        self.storage_class = storage_class

    def set_acl(self, acl):
        self.acl = acl

    def append_to_value(self, value):
        if self.bucket.is_versioned:
            old_path = self._versioned_path
            self.__init__(self.bucket, self.name, self.version+1)
            os.rename(old_path, self._versioned_path)
            self.create()

        self.value += self.value
        self.last_modified = datetime.datetime.utcnow()
        self._etag = None  # must recalculate etag

    def restore(self, days):
        expiry = datetime.datetime.utcnow() + datetime.timedelta(days)
        self.expiry_date = expiry.strftime("%a, %d %b %Y %H:%M:%S GMT")

    @classmethod
    def get_versions(cls, bucket, name):
        key_dir = os.path.join(bucket._path, 'keys', _encode_name(name))
        if not os.path.exists(key_dir):
            return []
        return sorted([
            Key(bucket, name, int(version))
            for version in os.listdir(key_dir)
            ], key=lambda k: k.version)


class VersionedKeyStore(collections.MutableMapping):

    def __init__(self, bucket):
        self.bucket = bucket
        self._path = os.path.join(bucket._path, 'keys')

    def __getitem__(self, name):
        versions = Key.get_versions(self.bucket, name)
        if not versions:
            raise KeyError(name)
        return versions[-1]

    def __setitem__(self, name, key):
        if not key.exists():
            key.create()

    def __delitem__(self, name):
        key = Key(self.bucket, name)
        if not key.exists():
            raise KeyError(name)
        key.delete()

    def __iter__(self):
        if not os.path.exists(self._path):
            return
        for name in os.listdir(self._path):
            yield _decode_name(name)

    def __len__(self):
        return len(os.listdir(self._path))

    def getlist(self, name, default=None):
        keys = Key.get_versions(self.bucket, name)
        if not keys:
            return default
        return keys

    def iterlists(self):
        for name in self.keys():
            yield name, self.getlist(name)


class Part(object):

    _last_modified = _InfoProperty('last_modified')
    etag = _InfoProperty('etag')

    def __init__(self, multipart, name):
        self.multipart = multipart
        self.name = name
        self._path = os.path.join(multipart._path, str(name)+'.part')
        self._info_path = os.path.join(self._path, 'info.json')
        self._value_path = os.path.join(self._path, 'value')

    def exists(self):
        return os.path.exists(self._path)

    @property
    def value(self):
        with open(self._value_path, 'rb') as file:
            return file.read()

    @value.setter
    def value(self, data):
        with open(self._value_path, 'wb') as file:
            file.write(data)
        self.etag = '"{0}"'.format(hashlib.md5(data).hexdigest())

    @property
    def size(self):
        return os.path.getsize(self._value_path)

    @property
    def last_modified(self):
        return datetime.datetime.strptime(
            self._last_modified, "%Y-%m-%dT%H:%M:%S.%fZ")

    @property
    def last_modified_ISO8601(self):
        return self._last_modified

    @property
    def last_modified_RFC1123(self):
        # Different datetime formats depending on how the key is obtained
        # https://github.com/boto/boto/issues/466
        return models.rfc_1123_datetime(self.last_modified)

    @property
    def response_dict(self):
        return {
            'etag': self.etag,
            'last-modified': self.last_modified_RFC1123,
        }

    def create(self, value):
        if not os.path.exists(self._path):
            os.makedirs(self._path)
        with open(self._info_path, 'w') as file:
            json.dump({
                'last_modified': models.iso_8601_datetime_with_milliseconds(
                    datetime.datetime.utcnow()),
                'etag': None
            }, file)
        self.value = value

    def delete(self):
        shutil.rmtree(self._path)


class Multipart(object):

    key_name = _InfoProperty('key_name')
    metadata = _InfoProperty('metadata')

    def __init__(self, bucket, id=None):
        self.id = id
        if id is None:
            rand_b64 = base64.b64encode(os.urandom(models.UPLOAD_ID_BYTES))
            self.id = rand_b64.decode('utf-8')\
              .replace('=', '').replace('+', '').replace('/', '')

        self._path = os.path.join(bucket._path, 'multiparts', self.id)
        self._info_path = os.path.join(self._path, 'info.json')

    def exists(self):
        return os.path.exists(self._path)

    def create(self, key_name, metadata):
        if not os.path.exists(self._path):
            os.makedirs(self._path)
        with open(self._info_path, 'w') as file:
            json.dump({
                'key_name': key_name,
                'metadata': metadata
                }, file)

    def delete(self):
        if not os.path.exists(self._path):
            return False
        shutil.rmtree(self._path)
        return True

    def complete(self, body):
        decode_hex = codecs.getdecoder("hex_codec")
        total = bytearray()
        md5s = bytearray()

        last = None
        count = 0
        for pn, etag in body:
            part = self.get_part(pn)
            if part is None or part.etag != etag:
                raise models.InvalidPart()
            if last is not None and \
                    len(last.value) < models.UPLOAD_PART_MIN_SIZE:
                raise models.EntityTooSmall()
            part_etag = part.etag.replace('"', '')
            md5s.extend(decode_hex(part_etag)[0])
            total.extend(part.value)
            last = part
            count += 1

        etag = hashlib.md5()
        etag.update(bytes(md5s))
        return total, "{0}-{1}".format(etag.hexdigest(), count)

    def get_part(self, part_id):
        part = Part(self, part_id)
        if not part.exists():
            return None
        return part

    def set_part(self, part_id, value):
        if part_id < 1:
            return

        part = Part(self, part_id)
        part.create(value)
        return part

    def list_parts(self):
        parts = sorted([
            fn[:-5] for fn in os.listdir(self._path)
            if fn.endswith('.part')],
            key = lambda v: int(v))
        for part in parts:
                yield self.get_part(part)


class Multiparts(collections.MutableMapping):

    def __init__(self, bucket):
        self.bucket = bucket
        self._path = os.path.join(bucket._path, 'multiparts')

    def __getitem__(self, name):
        mp = Multipart(self.bucket, name)
        if not mp.exists():
            raise KeyError(name)
        return mp

    def __setitem__(self, name, mp):
        if not mp.exists():
            mp.create()

    def __delitem__(self, name):
        mp = Multipart(self.bucket, name)
        if not mp.exists():
            raise KeyError(name)
        mp.delete()

    def __iter__(self):
        if not os.path.exists(self._path):
            return
        for name in os.listdir(self._path):
            yield name

    def __len__(self):
        return len(os.listdir(self._path))


class Bucket(object):

    policy = _InfoProperty('policy')
    versioning_status = _InfoProperty('versioning_status')
    acl = _AclProperty('acl')

    def __init__(self, s3, name):
        self.s3 = s3
        self.name = name

        self._path = os.path.join(s3.directory, self.name + '.bucket')
        self._info_path = os.path.join(self._path, 'info.json')
        self._lifecyle_path = os.path.join(self._path, 'lifecycle.json')
        self._ws_config_path = os.path.join(
            self._path, 'website_configuration.xml')

    @property
    def info(self):
        with open(self._info_path, 'rb') as file:
            return json.load(file)

    @info.setter
    def info(self, value):
        with open(self._info_path, 'wb') as file:
            return json.dump(value, file)

    @property
    def keys(self):
        return VersionedKeyStore(self)

    @property
    def multiparts(self):
        return Multiparts(self)

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
    def website_configuration(self):
        if not os.path.exists(self._ws_config_path):
            return []
        with open(self._ws_config_path, 'r') as file:
            return file.read()

    def exists(self):
        return os.path.exists(self._path)

    def create(self, region_name=None):
        os.mkdir(self._path)
        with open(self._info_path, 'w') as file:
            json.dump({
                'region_name': region_name
                }, file)

    def delete(self):
        if not os.path.exists(self._path):
            return False
        if len(self.keys):
            return False
        shutil.rmtree(self._path)
        return True

    def set_lifecycle(self, rules):
        with open(self._lifecyle_path, 'w') as file:
            json.dump(rules, file)

    def delete_lifecycle(self):
        os.remove(self._lifecyle_path)

    def set_website_configuration(self, website_configuration):
        if isinstance(website_configuration, bytes):
            website_configuration = website_configuration.decode('utf-8')
        if website_configuration is None:
            os.remove(self._ws_config_path)
            return
        with open(self._ws_config_path, 'w') as file:
            return file.write(website_configuration)

    def get_cfn_attribute(self, attribute_name):
        if attribute_name == 'DomainName':
            raise NotImplementedError(
                '"Fn::GetAtt" : [ "{0}" , "DomainName" ]"')
        elif attribute_name == 'WebsiteURL':
            raise NotImplementedError(
                '"Fn::GetAtt" : [ "{0}" , "WebsiteURL" ]"')
        raise UnformattedGetAttTemplateException()

    def set_acl(self, acl):
        self.acl = acl


class ShoobxS3Backend(models.S3Backend):

    def __init__(self):
        self.directory = './data'

    def create_bucket(self, bucket_name, region_name):
        new_bucket = Bucket(self, bucket_name)
        if new_bucket.exists():
            raise models.BucketAlreadyExists(bucket=bucket_name)
        new_bucket.create(region_name)

    def get_all_buckets(self):
        return [
            Bucket(self, fn[:-7])
            for fn in os.listdir(self.directory)
            if fn.endswith('.bucket')]

    def get_bucket(self, bucket_name):
        bucket = Bucket(self, bucket_name)
        if not bucket.exists():
            raise models.MissingBucket(bucket=bucket_name)
        return bucket

    def delete_bucket(self, bucket_name):
        bucket = Bucket(self, bucket_name)
        return bucket.delete()

    def set_key(self, bucket_name, key_name, value, storage=None, etag=None):
        key_name = models.clean_key_name(key_name)

        bucket = self.get_bucket(bucket_name)

        old_key = bucket.keys.get(key_name, None)
        if old_key is not None and bucket.is_versioned:
            new_version = old_key.version + 1
        else:
            new_version = 0

        new_key = Key(bucket, key_name, new_version)
        new_key.create(
            value=value,
            storage=storage,
            etag=etag)

        return new_key

    def initiate_multipart(self, bucket_name, key_name, metadata):
        bucket = self.get_bucket(bucket_name)
        new_multipart = Multipart(bucket)
        new_multipart.create(key_name, metadata)
        return new_multipart

    def complete_multipart(self, bucket_name, multipart_id, body):
        bucket = self.get_bucket(bucket_name)
        multipart = bucket.multiparts[multipart_id]
        value, etag = multipart.complete(body)
        if value is None:
            return

        key = self.set_key(bucket_name, multipart.key_name, value, etag=etag)
        key.set_metadata(multipart.metadata)

        del bucket.multiparts[multipart_id]

        return key

s3_sbx_backend = ShoobxS3Backend()
