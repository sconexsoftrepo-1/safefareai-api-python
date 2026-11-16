import logging
import boto3

from botocore.exceptions import ClientError

from app.config.settings import settings
from app.services.csv_parser import is_prs_file

logger = logging.getLogger(__name__)


class S3Service:

    def __init__(self):
        if not settings.S3_BUCKET_NAME:
            raise ValueError("S3_BUCKET_NAME is missing in .env")

        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )

        self.bucket_name = settings.S3_BUCKET_NAME
        self.folder = settings.S3_FOLDER

    def list_csv_files(self, prs=None):
        """
        List CSV files inside the configured S3 folder.
        Handles S3 pagination.

        prs=None  -> every CSV file
        prs=True  -> only PRS_... files   (seat pressure -> prs_sensor_readings)
        prs=False -> only the other files (-> sensor_readings)
        """

        csv_files = []
        paginator = self.s3_client.get_paginator("list_objects_v2")

        try:
            for page in paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=self.folder
            ):
                for item in page.get("Contents", []):
                    key = item["Key"]

                    filename = key.split("/")[-1]

                    if prs is not None and is_prs_file(filename) != prs:
                        continue

                    if key.lower().endswith(".csv"):
                        csv_files.append({
                            "key": key,
                            "filename": key.split("/")[-1],
                            "size": item["Size"],
                            "last_modified": item["LastModified"]
                        })

            logger.info(
                "Found %s %sCSV files in S3.",
                len(csv_files),
                "" if prs is None else ("PRS " if prs else "sensor "),
            )
            return csv_files

        except ClientError:
            logger.exception("Failed to list CSV files from S3.")
            raise

    def download_csv_file(self, s3_key: str) -> bytes:
        """
        Download a CSV file from S3 and return its contents.
        """

        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )

            content = response["Body"].read()

            logger.info("Downloaded S3 file: %s", s3_key)

            return content

        except ClientError:
            logger.exception("Failed to download S3 file: %s", s3_key)
            raise

    def delete_csv_file(self, s3_key: str):
        """
        Delete a CSV file from S3.
        Call this only after successful database processing.
        """

        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )

            logger.info("Deleted processed S3 file: %s", s3_key)

        except ClientError:
            logger.exception("Failed to delete S3 file: %s", s3_key)
            raise


s3_service = S3Service()