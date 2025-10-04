# Rearc Data Quest

A hands-on, end-to-end data engineering project that ingests public datasets, lands them in S3, and runs a lightweight serverless pipeline (Lambdas, SQS, EventBridge) provisioned via AWS CDK.

## Contents
- [Overview](#overview)
- [Setup & Usage](#setup--usage)
  - [Part 1 — BLS Data → S3](#part-1--bls-data--s3)
  - [Part 2 — Population API → S3](#part-2--population-api--s3)
  - [Part 3 — Analysis & Joins](#part-3--analysis--joins)
  - [Part 4 — IaC with AWS CDK](#part-4--iac-with-aws-cdk)
- [Proof of Execution](#proof-of-execution)
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

**S3 Bucket Configurations**
- Chose General Purpose Bucket
- Added Tags: Project=RearcDataQuest
- Enabled versioning for traceability and rollbacks
- Used SSE-S3 for encryption (since its safe for public data). Will switch to SSE-KMS for sensitive data.

### Enhancements

- I would add recursive traversal to explore nested directories within pr/ instead of just parsing the flat directory at /pub/time.series/pr/. I'd use a queue or stack-based approach to walk the entire time.series/pr/ tree (including subfolders and hidden index files) to avoid hitting recursion limits.
- Can set up a retry strategy for the requests Session so it automatically handles timeouts and common network issues.
- Implement idempotent uploads by writing files to bls/pr/_incoming/<file>.part first, verifying the size and hash, then copying to the final location bls/pr/<file> and deleting the .part file. This prevents half-written objects from appearing during interruptions.
- Create a JSON event logs and store them in S3 to track upload metadata and key events like hash mismatches, upload successes or failures, and skipped files—this would really help with auditing
- Can also include a staging area (like a /tmp folder) for preprocessing or batch operations when files need to be compressed or transformed, though the current approach of streaming directly to S3 works great for these lightweight public datasets
- Setup observability hooks to send summary metrics (files_seen, files_uploaded, bytes_transferred, duration_ms) to CloudWatch at the end of each run for better monitoring and operational visibility

### Part 2
**Goal**: Fetch national population data from the DataUSA API and save the response as nation_population.json in S3.

Source Code : [population.ipynb](https://github.com/ashwin975/Rearc_Dataquest/blob/main/part2/api_call.py)

**Description**: The Python script requests national population data from the public API and writes the raw JSON to S3 Bucket. The script uses a simple request header, performs a basic non-empty payload check, and also logs whether the object was created or updated.

Link to data in S3 : [nation_population.json](https://api-call-ashwin.s3.us-east-1.amazonaws.com/api-data/population.json)

### Enhancements
Similar enhancements as in Part 1 would be sufficient

## Part 3
**Goal**: US population mean & standard deviation for 2013–2018, find the best year (max annual sum of value) per series_id in pr.data.0.Current, and join to report value for series_id=PRS30006032, period=Q01 with population for that year.

## CHANGE FORMAT AND VALUES 

Source Code : [population.ipynb](https://github.com/ashwin975/Rearc_Dataquest/blob/main/part%203/data_analysis.ipynb)

1. Calculated US population summary (2013-2018)

Mean : 322069808.0
Standard Deviation : 4158441.04

2. Best Year by Series ID

Parsed pr.data.0.Current into a dataframe
Grouped data by Series ID and Year and calculated sum of values
Identified best year for each Series ID

3. Population mapping for specified series and period

Filtered pr.data.0.Current for series_id = PRS30006032 and period = Q01
Right join - merged population dataset on year column

### Enhancements

## Part 4
**Goal**: Automate the pipeline with IaC (CloudFormation/CDK/Terraform): schedule a Lambda to run Parts 1 & 2 daily, publish an SQS message when the JSON lands in S3, and trigger a Lambda that runs the Part 3 reports (logging results is sufficient).

## CHANGE PIPELINE NAME

## Architecture

**Implemented flow**
1. **EventBridge** triggers **Ingestion Lambda** daily.
2. Lambda streams **BLS time.series/pr** files and **Population API** output directly to **S3** (no local temp storage).
3. When a new population JSON lands in S3, an **S3 event** notifies **SQS**.
4. **Analysis Lambda** is invoked by SQS, reads both datasets from S3, computes summary stats & joins, and logs results.

> See `resources/` for screenshots and exported diagrams.

# **Infrastructure as Code (IaC) and Automated Data Pipeline (CDK)** 
Source Code : [CDK Stack](https://github.com/ashwin975/Rearc_Dataquest/blob/main/part4-wip/data_pipeline_stack.py)   

# MENTION TAGGING 

( All resources for this pipeline can be identified using tags: `Project: RearcDataQuest`) for better Data Governance and cost monitor

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

![Part4_pipeline](/resources/Part4_pipeline.png)

### Enhancements/Future Hardening
- Bronze/Silver/Gold zones across buckets
- DLQs + SNS alerts for failures
- QuickSight dashboards for reporting
- Private subnets / VPC endpoints

 ![Enhanced_Pipeline](/resources/Enhanced_Part4_Pipeline.png) 

## TAKE SCREENSHOTS FOR PROOF OF EXECUTION AND PUT IT IN SEPERATE FOLDER AND LINK THEM HERE

**Outputs & Proof of Execution**  
I have included a pipeline architecture diagram based on the resources deployed by the CDK infrastructure. For verification of specific resource configurations, all CDK output images are available in the [resources](/resources) folder with the `Part4` prefix.

![Output_Proof](/resources/Output_Proof.jpeg)

