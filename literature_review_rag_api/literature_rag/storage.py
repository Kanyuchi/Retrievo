"""
S3 Storage integration for PDF uploads and document management.
"""
import os
import io
import boto3
from botocore.exceptions import ClientError
from typing import Optional, BinaryIO, Union
import logging

logger = logging.getLogger(__name__)


class S3Storage:
    """Handles S3 operations for PDF storage."""

    def __init__(
        self,
        bucket_name: str = None,
        region: str = None,
        access_key_id: str = None,
        secret_access_key: str = None,
    ):
        """
        Initialize S3 storage client.

        Args:
            bucket_name: S3 bucket name (default from env: AWS_S3_BUCKET)
            region: AWS region (default from env: AWS_REGION)
            access_key_id: AWS access key (default from env: AWS_ACCESS_KEY_ID)
            secret_access_key: AWS secret key (default from env: AWS_SECRET_ACCESS_KEY)
        """
        self.bucket_name = bucket_name or os.getenv('AWS_S3_BUCKET', 'lit-rag-flow')
        self.region = region or os.getenv('AWS_REGION', 'eu-north-1')

        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            region_name=self.region,
            aws_access_key_id=access_key_id or os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=secret_access_key or os.getenv('AWS_SECRET_ACCESS_KEY'),
        )

        logger.info(f"S3 Storage initialized: bucket={self.bucket_name}, region={self.region}")

    def _get_owner_prefix(self, owner_id: Union[int, str, None]) -> str:
        """Get S3 key prefix for a job or default collection."""
        if owner_id is None or str(owner_id).lower() == "default":
            return "collections/default"
        if str(owner_id).isdigit():
            return f"jobs/{owner_id}"
        return f"collections/{owner_id}"

    def _get_document_key(self, owner_id: Union[int, str, None], phase: str, topic: str, filename: str) -> str:
        """Generate S3 key for a document."""
        # Sanitize phase and topic for use in S3 key
        safe_phase = phase.replace('/', '_').replace(' ', '_')
        safe_topic = topic.replace('/', '_').replace(' ', '_')
        safe_filename = filename.replace('/', '_')
        prefix = self._get_owner_prefix(owner_id)
        return f"{prefix}/pdfs/{safe_phase}/{safe_topic}/{safe_filename}"

    def upload_pdf(
        self,
        job_id: Union[int, str, None],
        phase: str,
        topic: str,
        filename: str,
        file_content: BinaryIO,
        content_type: str = 'application/pdf',
    ) -> str:
        """
        Upload a PDF to S3.

        Args:
            job_id: The job ID
            phase: Document phase
            topic: Document topic
            filename: Original filename
            file_content: File-like object with PDF content
            content_type: MIME type

        Returns:
            S3 key where the file was stored
        """
        s3_key = self._get_document_key(job_id, phase, topic, filename)

        try:
            self.s3_client.upload_fileobj(
                file_content,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'Metadata': {
                        'job_id': str(job_id) if job_id is not None else "default",
                        'phase': phase,
                        'topic': topic,
                        'original_filename': filename,
                    }
                }
            )
            logger.info(f"Uploaded PDF to S3: {s3_key}")
            return s3_key
        except ClientError as e:
            logger.error(f"Failed to upload PDF to S3: {e}")
            raise

    def download_pdf(self, s3_key: str) -> bytes:
        """
        Download a PDF from S3.

        Args:
            s3_key: The S3 key of the document

        Returns:
            PDF content as bytes
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            return response['Body'].read()
        except ClientError as e:
            logger.error(f"Failed to download PDF from S3: {e}")
            raise

    def download_pdf_to_file(self, s3_key: str, local_path: str) -> str:
        """
        Download a PDF from S3 to a local file.

        Args:
            s3_key: The S3 key of the document
            local_path: Local path to save the file

        Returns:
            Local file path
        """
        try:
            self.s3_client.download_file(self.bucket_name, s3_key, local_path)
            logger.info(f"Downloaded PDF from S3 to {local_path}")
            return local_path
        except ClientError as e:
            logger.error(f"Failed to download PDF from S3: {e}")
            raise

    def delete_pdf(self, s3_key: str) -> bool:
        """
        Delete a PDF from S3.

        Args:
            s3_key: The S3 key of the document

        Returns:
            True if deleted successfully
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"Deleted PDF from S3: {s3_key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete PDF from S3: {e}")
            raise

    def delete_job_files(self, job_id: Union[int, str, None]) -> int:
        """
        Delete all files for a job or default collection.

        Args:
            job_id: The job ID

        Returns:
            Number of files deleted
        """
        prefix = self._get_owner_prefix(job_id)
        deleted_count = 0

        try:
            # List all objects with the job prefix
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)

            for page in pages:
                if 'Contents' not in page:
                    continue

                # Delete objects in batches
                objects_to_delete = [{'Key': obj['Key']} for obj in page['Contents']]
                if objects_to_delete:
                    self.s3_client.delete_objects(
                        Bucket=self.bucket_name,
                        Delete={'Objects': objects_to_delete}
                    )
                    deleted_count += len(objects_to_delete)

            logger.info(f"Deleted {deleted_count} files for job {job_id}")
            return deleted_count
        except ClientError as e:
            logger.error(f"Failed to delete job files from S3: {e}")
            raise

    def list_job_files(self, job_id: Union[int, str, None]) -> list:
        """
        List all files for a job or default collection.

        Args:
            job_id: The job ID

        Returns:
            List of S3 keys
        """
        prefix = self._get_owner_prefix(job_id)
        files = []

        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)

            for page in pages:
                if 'Contents' in page:
                    files.extend([obj['Key'] for obj in page['Contents']])

            return files
        except ClientError as e:
            logger.error(f"Failed to list job files from S3: {e}")
            raise

    def get_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        """
        Generate a presigned URL for downloading a file.

        Args:
            s3_key: The S3 key of the document
            expiration: URL expiration time in seconds (default 1 hour)

        Returns:
            Presigned URL string
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise

    def file_exists(self, s3_key: str) -> bool:
        """
        Check if a file exists in S3.

        Args:
            s3_key: The S3 key to check

        Returns:
            True if file exists
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise


# Singleton instance
_storage_instance: Optional[S3Storage] = None


def get_storage() -> S3Storage:
    """Get or create the S3 storage singleton."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = S3Storage()
    return _storage_instance


class LocalStorage:
    """Local filesystem storage fallback for development."""

    def __init__(self, base_path: str = "./uploads"):
        """Initialize local storage."""
        import os
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
        logger.info(f"Local Storage initialized: base_path={self.base_path}")

    def _get_document_path(self, job_id: Union[int, str, None], phase: str, topic: str, filename: str) -> str:
        """Generate local path for a document."""
        import os
        safe_phase = phase.replace('/', '_').replace(' ', '_')
        safe_topic = topic.replace('/', '_').replace(' ', '_')
        safe_filename = filename.replace('/', '_')

        if job_id is None or str(job_id).lower() == "default":
            prefix = "collections/default"
        elif str(job_id).isdigit():
            prefix = f"jobs/{job_id}"
        else:
            prefix = f"collections/{job_id}"

        dir_path = os.path.join(self.base_path, prefix, "pdfs", safe_phase, safe_topic)
        os.makedirs(dir_path, exist_ok=True)
        return os.path.join(dir_path, safe_filename)

    def upload_pdf(
        self,
        job_id: Union[int, str, None],
        phase: str,
        topic: str,
        filename: str,
        file_content: BinaryIO,
        content_type: str = 'application/pdf',
    ) -> str:
        """Save a PDF to local storage."""
        local_path = self._get_document_path(job_id, phase, topic, filename)

        with open(local_path, 'wb') as f:
            f.write(file_content.read())

        logger.info(f"Saved PDF locally: {local_path}")
        return local_path

    def download_pdf(self, local_path: str) -> bytes:
        """Read a PDF from local storage."""
        with open(local_path, 'rb') as f:
            return f.read()

    def delete_pdf(self, local_path: str) -> bool:
        """Delete a PDF from local storage."""
        import os
        if os.path.exists(local_path):
            os.remove(local_path)
            logger.info(f"Deleted local PDF: {local_path}")
            return True
        return False

    def get_presigned_url(self, local_path: str, expiration: int = 3600) -> str:
        """For local storage, return a file:// URL or placeholder."""
        return f"file://{local_path}"

    def file_exists(self, local_path: str) -> bool:
        """Check if file exists locally."""
        import os
        return os.path.exists(local_path)


# Local storage singleton
_local_storage_instance: Optional[LocalStorage] = None


def get_local_storage() -> LocalStorage:
    """Get or create the local storage singleton."""
    global _local_storage_instance
    if _local_storage_instance is None:
        _local_storage_instance = LocalStorage()
    return _local_storage_instance


def is_s3_configured() -> bool:
    """Check if S3 credentials are configured."""
    return bool(os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'))


def get_storage_auto():
    """Get appropriate storage backend based on configuration."""
    if is_s3_configured():
        return get_storage()
    else:
        return get_local_storage()
