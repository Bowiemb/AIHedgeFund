"""S3 client for storing raw filings."""

import logging
from typing import Optional

import aioboto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3Client:
    """Async S3 client for filing storage."""

    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str = "us-east-1",
    ):
        """
        Initialize S3 client.

        Args:
            endpoint_url: S3 endpoint (MinIO or AWS)
            access_key: AWS access key
            secret_key: AWS secret key
            bucket: Bucket name
            region: AWS region
        """
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        self.region = region
        self.session = aioboto3.Session()

    async def upload_file(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload file to S3.

        Args:
            key: S3 object key
            data: File data
            content_type: MIME type

        Returns:
            S3 URL
        """
        async with self.session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
        ) as s3:
            try:
                await s3.put_object(
                    Bucket=self.bucket,
                    Key=key,
                    Body=data,
                    ContentType=content_type,
                )
                logger.info(f"Uploaded to S3: {key}")
                return f"s3://{self.bucket}/{key}"

            except ClientError as e:
                logger.error(f"Failed to upload {key}: {e}")
                raise

    async def download_file(self, key: str) -> Optional[bytes]:
        """
        Download file from S3.

        Args:
            key: S3 object key

        Returns:
            File data or None if not found
        """
        async with self.session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
        ) as s3:
            try:
                response = await s3.get_object(Bucket=self.bucket, Key=key)
                data = await response["Body"].read()
                logger.info(f"Downloaded from S3: {key}")
                return data

            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchKey":
                    logger.warning(f"Key not found in S3: {key}")
                    return None
                logger.error(f"Failed to download {key}: {e}")
                raise

    async def file_exists(self, key: str) -> bool:
        """
        Check if file exists in S3.

        Args:
            key: S3 object key

        Returns:
            True if exists
        """
        async with self.session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
        ) as s3:
            try:
                await s3.head_object(Bucket=self.bucket, Key=key)
                return True
            except ClientError:
                return False

    async def ensure_bucket_exists(self) -> None:
        """Create bucket if it doesn't exist."""
        async with self.session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
        ) as s3:
            try:
                await s3.head_bucket(Bucket=self.bucket)
                logger.info(f"Bucket exists: {self.bucket}")
            except ClientError:
                logger.info(f"Creating bucket: {self.bucket}")
                await s3.create_bucket(Bucket=self.bucket)
