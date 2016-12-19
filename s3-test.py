import boto3
import sys

s3 = boto3.resource(
    's3', region_name='us-east-1', endpoint_url=sys.argv[1])

bucket = s3.Bucket('test')
import pdb; pdb.set_trace()
bucket.create()
bucket.delete()



