
import boto3
import csv
import io
from datetime import datetime
from zoneinfo import ZoneInfo
import os

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "ap-south-1")

S3_BUCKET_NAME="safefare-ai-sensor-readings-970547358626-ap-south-1-an"
S3_FOLDER="test-backend/"

# IMPORTANT:
# Must exactly match the iot_kit value in dbo.vehicles
IOT_KIT_ID = "IOT-KIT-001"

# Generate filename using IST timestamp
now = datetime.now(ZoneInfo("Asia/Kolkata"))
timestamp = now.strftime("%d-%m-%Y_%H-%M-%S")

filename = f"{IOT_KIT_ID}_{timestamp}.CSV"
s3_key = f"{S3_FOLDER.strip('/')}/{filename}"

# Sample CSV readings

rows = [
    ["timestamp", "iot_kit_id", "sensor_sub_id", "sensor_data"],

    [
        now.strftime("%Y-%m-%d %H:%M:%S"),
        "IR",
        1,
        "passenger_count:2,reading:idle"
    ],

    [
        now.strftime("%Y-%m-%d %H:%M:%S"),
        "ULT",
        2,
        "distance:3,reading:no_echo"
    ],

    [
        now.strftime("%Y-%m-%d %H:%M:%S"),
        "SMK",
        3,
        "value:2,reading:alert"
    ],

    [
        now.strftime("%Y-%m-%d %H:%M:%S"),
        "ALC",
        4,
        "value:3,reading:alert"
    ],
]


# Create CSV in memory
csv_buffer = io.StringIO()
writer = csv.writer(csv_buffer)
writer.writerows(rows)

# Connect to S3
s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_DEFAULT_REGION,
)

# Upload CSV
s3.put_object(
    Bucket=S3_BUCKET_NAME,
    Key=s3_key,
    Body=csv_buffer.getvalue().encode("utf-8"),
    ContentType="text/csv",
)

print("Sample CSV uploaded successfully!")
print("Filename:", filename)
print("S3 location:", s3_key)
