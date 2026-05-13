import boto3
from botocore.exceptions import ClientError
from app.core.config import settings
import uuid
import os

def upload_contract_file(file_content: bytes, filename: str, company_id: str) -> str:
    """
    Upload contract file to S3.
    Returns mock URL if AWS not configured.
    """
    if not settings.AWS_ACCESS_KEY_ID:
        # Return mock URL for development
        return f"https://mock-s3.contractflow.local/{company_id}/{uuid.uuid4()}/{filename}"

    try:
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )

        key = f"contracts/{company_id}/{uuid.uuid4()}/{filename}"
        s3_client.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=key,
            Body=file_content,
            ContentType="application/pdf"
        )

        return f"https://{settings.S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"

    except ClientError as e:
        raise Exception(f"S3 upload failed: {str(e)}")
