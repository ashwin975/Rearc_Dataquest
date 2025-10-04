# Rearc Data Quest

A hands-on, end-to-end data engineering project that ingests public datasets, lands them in S3, and runs a lightweight serverless pipeline (Lambdas, SQS, EventBridge) provisioned via AWS CDK.

## Contents
- [Overview](#overview)
- [Setup & Usage](#setup--usage)
  - [Part 1 — BLS Data → S3](#part-1--bls-data--s3)
  - [Part 2 — Population API → S3](#part-2--population-api--s3)
  - [Part 3 — Analysis & Joins](#part-3--analysis--joins)
  - [Part 4 — IaC with AWS CDK](#part-4--iac-with-aws-cdk)
- [Outputs](#proof-of-execution)
- [Operational Notes](#operational-notes)
  
## Overview

- **Automated ingestion** of public datasets (BLS *time.series/pr* and a population dataset)
- **Durable landing** in an S3 Buckets and server-side encryption
- **Event-driven processing** using S3 notifications → SQS → Lambda.
- **Infrastructure as Code** using AWS CDK to define and deploy the pipeline.
  
### Part 1 — BLS Data → S3
**Goal:** Republish the BLS time.series/pr dataset to S3 and keep the S3 copy in sync with the source (no hard‑coded filenames, no duplicate uploads).

Source Code : [part1.ipynb](https://github.com/ashwin975/Rearc_Dataquest/blob/main/Part%201/Part-1.ipynb)

**Description**: The Python script lists files under BLS time.series/pr, streams each file, and uploads it to s3 Bucket without using local temp storage. The script skips keys that already exist (to avoid duplicates on re-runs) and logs attempted/skipped/uploaded counts for validation.

Links to data in S3 :

- [pr.series](https://rearc-data-quest-ssm.s3.us-east-2.amazonaws.com/bls/pr/pr.series)
- [pr.txt](https://bls-sync-data-ashwin.s3.us-east-1.amazonaws.com/bls-datasets/pr.data.0.Current/pr.txt)
- [pr.measure](https://bls-sync-data-ashwin.s3.us-east-1.amazonaws.com/bls-datasets/pr.data.0.Current/pr.measure)
- [pr.period](https://bls-sync-data-ashwin.s3.us-east-1.amazonaws.com/bls-datasets/pr.data.0.Current/pr.period)
- [pr.seasonal](https://bls-sync-data-ashwin.s3.us-east-1.amazonaws.com/bls-datasets/pr.data.0.Current/pr.seasonal)
- [pr.sector](https://bls-sync-data-ashwin.s3.us-east-1.amazonaws.com/bls-datasets/pr.data.0.Current/pr.sector)
- [pr.duration](https://bls-sync-data-ashwin.s3.us-east-1.amazonaws.com/bls-datasets/pr.data.0.Current/pr.duration)
- [pr.footnote](https://bls-sync-data-ashwin.s3.us-east-1.amazonaws.com/bls-datasets/pr.data.0.Current/pr.footnote)
- [pr.contacts](https://bls-sync-data-ashwin.s3.us-east-1.amazonaws.com/bls-datasets/pr.contacts)
- [pr.data.0.Current](https://bls-sync-data-ashwin.s3.us-east-1.amazonaws.com/bls-datasets/pr.data.0.Current)
- [pr.data.1.AllData](https://bls-sync-data-ashwin.s3.us-east-1.amazonaws.com/bls-datasets/pr.data.1.AllData)
- [pr.class](https://bls-sync-data-ashwin.s3.us-east-1.amazonaws.com/bls-datasets/pr.class)

**Highlights**

Public datasets are fetched from BLS URL and published to S3 bucket. The sync script ensures:
- Dynamic file discovery (no hard-coded filenames)
- Duplicate-aware uploads (hash check)
- Prefix bls/pr/ to organize objects cleanly and enable simple lifecycle rules down the road.
- Streamed I/O (no local disk usage)
- Setup does not throw 403 error and is compliant with BLS data access policies
- Added Tags: Project=RearcDataQuest for better Data Governance and cost monitor
- Enabled versioning for traceability and rollbacks
- Used SSE-S3 for encryption (since its safe for public data). Will switch to SSE-KMS for sensitive data.

### Enhancements
- **Depth-first listing for `pr/`**: Walk the entire `time.series/pr/` tree (subfolders, hidden index files), not just the root listing, using a queue/stack to avoid recursion limits.
- **Idempotency-Write**: Upload to `bls/pr/_incoming/<file>.part`, verify size+hash, then copy to `bls/pr/<file>` and delete the `.part`. Prevents half-written objects on interruptions.
- **Event trail**: Append operational events to `bls/pr/_logs/ingest.jsonl` (start, skip, upload, verify, error) with timestamps and durations—easy to grep or query later.
- **Observability hooks** (optional): Send a summary metric (files_seen, files_uploaded, bytes_transferred, duration_ms) to CloudWatch at the end of each run.

### Part 2 — Population API → S3
**Goal**: Fetch national population data via API and save the response as nation_population.json in S3.

Source Code : [population.ipynb](https://github.com/ashwin975/Rearc_Dataquest/blob/main/part2/api_call.py)

**Description**: The Python script requests national population data from the public API and writes the raw JSON to S3 Bucket. The script uses a simple request header, performs a basic non-empty payload check, and also logs whether the object was created or updated.

Link to data in S3 : [nation_population.json](https://api-call-ashwin.s3.us-east-1.amazonaws.com/api-data/population.json)

### Enhancements
Similar enhancements as in Part 1 would be sufficient

### Part 3 — Analysis & Joins
**Goal**: US population mean & standard deviation for 2013–2018, find the best year (max annual sum of value) per series_id in pr.data.0.Current, and join to report value for series_id=PRS30006032, period=Q01 with population for that year.

Source Code : [population.ipynb](https://github.com/ashwin975/Rearc_Dataquest/blob/main/part%203/data_analysis.ipynb)

1. US population summary (2013-2018)

Mean : 322069808.0
Standard Deviation : 4158441.04

2. Best Years by Series ID

Put the pr.data.0.Current into a dataframe
Grouped data by Series ID and Year and calculated sum 
Identified best year for each Series ID

3. Population mapping for specified series and period

Filtered pr.data.0.Current for series_id = PRS30006032 and period = Q01
Right join - merged population dataset on year column

### Enhancements

### Part 4 — IaC with AWS CDK
**Goal**: Automate the pipeline with IaC (CloudFormation/CDK/Terraform): schedule a Lambda to run Parts 1 & 2 daily, publish an SQS message when the JSON lands in S3, and trigger a Lambda that runs the Part 3 reports.

## Architecture
![Pipeline Architecture](https://github.com/ashwin975/Rearc_Dataquest/blob/main/part4-wip/Architecture101.svg)

**Implemented flow**
1. **EventBridge** triggers **Ingestion Lambda** daily.
2. Lambda streams **BLS time.series/pr** files and **Population API** output directly to **S3** (no local temp storage).
3. When a new population JSON lands in S3, an **S3 event** notifies **SQS**.
4. **Analysis Lambda** is invoked by SQS, reads both datasets from S3, computes summary stats & joins, and logs results.

> See `resources/` for screenshots and exported diagrams.

Source Code : [CDK Stack](https://github.com/ashwin975/Rearc_Dataquest/blob/main/part4-wip/data_pipeline_stack.py)   

( All resources for this pipeline can be identified using tags: `Project: RearcDataQuest`) 

**AWS Resources Created**
This CDK deployment creates the following AWS resources:
- **S3 Bucket:** `lambda-pipeline-data-bucket` - Stores BLS data files and population JSON data
- **Lambda Functions:**
  `data-ingestion-lambda` - Downloads and processes data from external APIs daily
  `data-analysis-lambda` - Processes data when triggered by S3 events
- **SQS Queue:** `data-processing-queue` - Queues messages when new data is uploaded to S3
- **EventBridge Rule:** `daily-data-ingestion-trigger` - Triggers the ingestion Lambda daily
- **IAM Roles:** Auto-generated roles with appropriate permissions for Lambda execution  

Built a serverless data pipeline using CDK that automates:
- **Data ingestion (Parts 1 & 2):** An EventBridge schedule triggers the Ingestion Lambda to fetch BLS `time.series/pr` files and the Population API response, streaming both directly to S3.
- **Event-driven processing (Part 3):** An S3 `ObjectCreated` event on the `population/` prefix publishes to SQS.
  - The [Ingest Lambda](https://github.com/ashwin975/Rearc_Dataquest/blob/main/part4-wip/lambdas/ingest/handler.py) consumes the message, reads both datasets from S3, performs the       required stats/join, and writes results to CloudWatch Logs (file outputs to S3 planned).
  - The [Analysis Lambda](https://github.com/ashwin975/Rearc_Dataquest/blob/main/part4-wip/lambdas/report/handler.py) triggers SQS messages published by S3 `ObjectCreated:*` events on the `population/` prefix. Then Reads the population JSON and required BLS objects from S3, computes the Part 3 outputs (population stats, best year per `series_id`, and the join for `PRS30006032`/`Q01`), and **logs** results to CloudWatch Logs.
- **Daily cadence:** The schedule is managed by EventBridge; parameterize cron/rate in the stack for easy changes.
- **Source layout:** See the CDK app and Lambda code under `part4-wip/` in this repository.

### Enhancements/Future Hardening
- Bronze/Silver/Gold layers using Databricks
- Autoloader acting as File watcher to append new data from Silver layer
- Power BI dashboards for reporting
- Private subnets / VPC endpoints for better security

 ![Enhanced_Pipeline](https://github.com/ashwin975/Rearc_Dataquest/blob/main/part4-wip/Enhanced%20Databricks%20Architecture.svg)

### Outputs
![Part1_CDK](https://github.com/ashwin975/Rearc_Dataquest/blob/main/part4-wip/Part1_cdk.jpg)
![Part1_Part2_CDK](https://github.com/ashwin975/Rearc_Dataquest/blob/main/part4-wip/Part1_Part%202_CDK.jpg)
![Part3_CDK](https://github.com/ashwin975/Rearc_Dataquest/blob/main/part4-wip/Part3_cdk.jpg)

### Operational Notes

- Additionaly, I tested Docker Containerization on Part 4 without the CDK, 
- Docker image: I wrapped Python, needed libraries, handler.py, and settings into a single container, so it runs the same on my laptop and in AWS Lambda.
- handler.py does: grabs BLS data, checks if files changed, uploads new/updated ones to S3, and can also pull from a second API if enabled.
- Dependencies: listed in requirements.txt so everything gets installed during the image build.
- Local Lambda: the Lambda Runtime Interface Emulator (RIE) lets me test the function locally just like AWS Lambda would run it.
