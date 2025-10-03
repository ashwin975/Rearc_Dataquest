import os
import json
import hashlib
from urllib.parse import urljoin
from datetime import datetime

import boto3
import requests
from bs4 import BeautifulSoup

S3_BUCKET = os.environ["BUCKET_NAME"]
BLS_URL = os.environ["BLS_URL"]
BLS_PREFIX = os.environ.get("BLS_PREFIX", "bls-data/")
API_URL = os.environ.get("API_URL", "")
API_PREFIX = os.environ.get("API_PREFIX", "api-data/")
JSON_FILE_NAME = os.environ.get("JSON_FILE_NAME", "population.json")
USER_AGENT = os.environ.get("USER_AGENT", "Mozilla/5.0 (compatible; DataSyncBot/1.0)")
HEADERS = {"User-Agent": USER_AGENT}
s3 = boto3.client("s3")

def calculate_md5(content: bytes) -> str:
    return hashlib.md5(content).hexdigest()

def fetch_bls_file_list(base_url: str) -> list[str]:
    r = requests.get(base_url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    return [
        a["href"].split("/")[-1]
        for a in soup.find_all("a", href=True)
        if not a["href"].endswith("/")
    ]

def upload_if_changed(bucket: str, key: str, new_bytes: bytes) -> bool:
    try:
        existing = s3.get_object(Bucket=bucket, Key=key)
        old_md5 = calculate_md5(existing["Body"].read())
        new_md5 = calculate_md5(new_bytes)
        if old_md5 == new_md5:
            return False
    except Exception:
        pass
    s3.put_object(Bucket=bucket, Key=key, Body=new_bytes)
    return True

def sync_bls_to_s3() -> int:
    uploaded = 0
    for fname in fetch_bls_file_list(BLS_URL):
        url = urljoin(BLS_URL, fname)
        key = f"{BLS_PREFIX}{fname}"
        r = requests.get(url, headers=HEADERS, timeout=120)
        r.raise_for_status()
        if upload_if_changed(S3_BUCKET, key, r.content):
            uploaded += 1
            print(f"[BLS] Uploaded/Updated: {fname}")
    return uploaded

def export_api_to_s3() -> bool:
    if not API_URL:
        print("[API] Skipping: API_URL not set.")
        return False
    r = requests.get(API_URL, headers=HEADERS, timeout=60)
    r.raise_for_status()

    try:
        payload = json.dumps(r.json())
        content_type = "application/json"
    except ValueError:
        payload = r.text
        content_type = r.headers.get("Content-Type", "text/plain")

    key = f"{API_PREFIX}{JSON_FILE_NAME}"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=payload.encode("utf-8"),
        ContentType=content_type,
    )
    print(f"[API] Exported to s3://{S3_BUCKET}/{key}")
    return True

def lambda_handler(event, context):
    print(f"Run started: {datetime.utcnow().isoformat()}Z")
    uploaded_bls = sync_bls_to_s3()
    api_ok = export_api_to_s3()
    result = {
        "status": "ok",
        "bls_files_uploaded_or_updated": uploaded_bls,
        "api_exported": api_ok,
    }
    print(result)
    return result
