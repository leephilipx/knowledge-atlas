import boto3
import os
from io import BytesIO
from botocore.exceptions import NoCredentialsError

# Load from .env or environment variables
ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL")
ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
BUCKET_NAME = os.getenv("AWS_BUCKET_NAME", "knowledge-repo")

def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY
    )

def upload_file(file_obj, object_name, content_type=None):
    s3 = get_s3_client()
    try:
        # Create bucket if not exists
        try:
            s3.head_bucket(Bucket=BUCKET_NAME)
        except:
            s3.create_bucket(Bucket=BUCKET_NAME)

        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type

        file_obj.seek(0)
        s3.upload_fileobj(file_obj, BUCKET_NAME, object_name, ExtraArgs=extra_args)
        return f"{BUCKET_NAME}/{object_name}"
    except Exception as e:
        print(f"Upload Error: {e}")
        return None

def download_file_obj(object_path):
    s3 = get_s3_client()
    try:
        # object_path might be "bucket/key"
        bucket, key = object_path.split('/', 1)
        response = s3.get_object(Bucket=bucket, Key=key)
        return BytesIO(response['Body'].read())
    except Exception as e:
        print(f"Download Error: {e}")
        return None