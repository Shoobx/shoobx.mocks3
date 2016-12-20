
import boto3
import io
import sys

s3 = boto3.resource(
    's3', region_name='us-east-1', endpoint_url=sys.argv[1])

bucket = s3.Bucket('test')
bucket.create()

bucket.put_object(
    Key='hello',
    Body='Hello World!',
    ContentDisposition='attachment; filename=hello.txt',
    ContentEncoding='utf-8',
    ContentType='text/plain',
    Metadata={'Field1': 'Value1'},
    ContentLength=12)

file = io.BytesIO()
bucket.download_fileobj('hello', file)
file.seek(0)
print file.read()

s3.Object(bucket.name, 'hello').delete()

bucket.delete()

