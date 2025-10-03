import requests
import boto3
import json
from datetime import datetime
import config

# Create S3 client
s3 = boto3.client("s3")

def export_api_to_s3():
    # Fetch API data
    response = requests.get(API_URL)
    response.raise_for_status()
    data = response.json()

    # Upload to S3 as api_response.json
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=S3_KEY,
        Body=json.dumps(data),
        ContentType="application/json"
    )

    print(f"API data exported to s3://{S3_BUCKET}/{S3_KEY}")


if __name__ == "__main__":
    export_api_to_s3()
