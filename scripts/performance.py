
import boto3
import io
import sys
import time

s3 = boto3.resource(
    's3', region_name='us-east-1', endpoint_url=sys.argv[1])

bucket = s3.Bucket('com.shoobx.app.perf.test')
bucket.create()

t1 = time.time()

data = 'Hello World! '*1000

for idx in range(100):
    bucket.put_object(
        Key='hello-%i' % idx,
        Body=data,
        ContentDisposition='attachment; filename=hello.txt',
        ContentEncoding='utf-8',
        ContentType='text/plain',
        Metadata={'Field1': 'Value1'},
        ContentLength=len(data))

t2 = time.time()

print "Write: "
print 'Average: %.3f s/req' % ((t2-t1) / 100)
print 'Throughput: %.3f req/s' % (100 / (t2-t1))

for idx in range(100):
    file = io.BytesIO()
    bucket.download_fileobj('hello-%i' % idx, file)

t3 = time.time()

print "Read: "
print 'Average: %.3f s/req' % ((t3-t2) / 100)
print 'Throughput: %.3f req/s' % (100 / (t3-t2))

for idx in range(100):
    s3.Object(bucket.name, 'hello-%i' % idx).delete()

t4 = time.time()

print "Delete: "
print 'Average: %.3f s/req' % ((t4-t3) / 100)
print 'Throughput: %.3f req/s' % (100 / (t4-t3))


bucket.delete()

