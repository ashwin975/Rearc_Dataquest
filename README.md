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

Public datasets are fetched from BLS URL and published to `rearc-data-quest-ssm` S3 bucket. The sync script ensures:
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

### If I had time, I will?

I would add recursive search for nested directores inside the pr/ directory. Currently the script parses the flat directory at /pub/time.series/pr/ but I would implement recursive traversal for potential subfolders within pr/ path
I would use retry strategy for request Session. This would enable automatic retries on time-out issues or other common network errors.
I would implement and store log.csv file in S3 to append metadata about uploads and structured events (like hash mismatch, upload success/failure, skipped files etc). This would improve auditing
I would also add more file validation techniques. Currently the script only compares hash of files in source and datalake but I'd expand it to include file size comparison, last modified timestamps and possibly a checksum strategy for byte comparison.
I would include a staging area like a \tmp folder to preprocess files or enable batch processing (If the files need to be zipped before upload or in other scenarios). But as of now, the script directly streams data into S3 since it is ideal for lightweight public datasets.
Upload Result

### Part 2
**Goal**: Fetch national population data from the DataUSA API and save the response as nation_population.json in S3.

Source Code : [population.ipynb](https://github.com/ashwin975/Rearc_Dataquest/blob/main/part2/api_call.py)

**Description**: The Python script requests national population data from the public API and writes the raw JSON to S3 Bucket. The script uses a simple request header, performs a basic non-empty payload check, and also logs whether the object was created or updated.

Link to data in S3 : [nation_population.json](https://api-call-ashwin.s3.us-east-1.amazonaws.com/api-data/population.json)

### If I had time, I will?
Since Part 1 and Part 2 have the same functionality, I would implement the enhancements listed in part 1 like retry for request Session, have a metadata logging file and possibly include a staging area


## Part 3
**Goal**: US population mean & standard deviation for 2013–2018, find the best year (max annual sum of value) per series_id in pr.data.0.Current, and join to report value for series_id=PRS30006032, period=Q01 with population for that year (deliver as a .ipynb).

## CHANGE FORMAT AND VALUES 


Source Code : population.ipynb

Question 1 : Calculated US population summary (2013-2018)

Mean : 317437383.0
Standard Deviation : 4257089.54

Question 2 : Best Year by Series ID

Parsed pr.data.0.Current into a dataframe
Grouped data by Series ID and Year and calculated sum of values
Identified best year for each Series ID

Question 3 : Population mapping for specified series and period

Filtered pr.data.0.Current for series_id = PRS30006032 and period = Q01
Right merge population dataset on year column

### If I had time, I will?

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
Source Code : [CDK Stack](./part4_aws_cdk/part4_aws_cdk_stack.py)    

# MENTION TAGGING 

( All resources for this pipeline can be identified using tags: `Project: RearcDataQuest` and `Environment: dev`)

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
- Data ingestion from the BLS and Population API (Part 1 and 2)
  - Ingestion Lambda function Source Code : [Ingestion Lambda Function](./lambda_functions/data_ingestion/lambda_func.py)
- Daily sync schedule using EventBridge
- Event-driven data processing using SQS and Lambda (Part 3)
  - Analysis Lambda function Source Code : [Analysis Lambda Function](./lambda_functions/data_analysis/lambda_func.py)

## REMOVE TABLE 

**Pipeline Architecture**  
| Resource | Purpose |
|----------|---------|
| S3 Bucket | Stores both raw BLS and population datasets |
| Lambda (Ingestion) | Fetches BLS + API data daily and uploads to S3 |
| EventBridge Rule | Triggers ingestion Lambda daily |
| SQS Queue | Gets triggered when new population JSON is uploaded to S3 |
| Lambda (Analytics) | Processes messages from SQS, reads both datasets, and logs analysis |

## DON'T INCLUDE ALL

**Pipeline Flow (Implemented)**  
- **Daily Data Ingestion**: EventBridge triggers a Lambda function daily to fetch BLS data and population data from APIs, storing both datasets in S3 under separate prefixes.
- **Event-Driven Processing**: When new JSON files are uploaded to S3, an event notification triggers an SQS queue, which then invokes an analytics Lambda function.
- **Analytics & Reporting**: The analytics Lambda reads both datasets, computes population statistics (mean/std dev for 2013-2018), identifies the best performing year by series ID, creates a joined report for series `PRS30006032` with population data, and logs all results.

![Part4_pipeline](/resources/Part4_pipeline.png)

**Future hardening (planned)**
- Bronze/Silver/Gold zones across buckets
- DLQs + SNS alerts for failures
- QuickSight dashboards for reporting
- Private subnets / VPC endpoints

**Future Optimizations**  
- **Data Architecture**: I would implement `Bronze/Silver/Gold` data layers across separate S3 buckets for improved data quality and lineage tracking
- **Error Handling & Monitoring**: I would add `DLQ` for failed messages and `SNS` notifications for real-time pipeline failure alerts  
- **Reporting**: I would integrate `Amazon QuickSight` for interactive dashboards and user-friendly reporting
- **Security and Network Isolation**: I would deploy infrastructure in private `VPC` subnets for improved security and compliance

 ![Enhanced_Pipeline](/resources/Enhanced_Part4_Pipeline.png) 

## TAKE SCREENSHOTS FOR PROOF OF EXECUTION AND PUT IT IN SEPERATE FOLDER AND LINK THEM HERE

**Outputs & Proof of Execution**  
I have included a pipeline architecture diagram based on the resources deployed by the CDK infrastructure. For verification of specific resource configurations, all CDK output images are available in the [resources](/resources) folder with the `Part4` prefix.

![Output_Proof](/resources/Output_Proof.jpeg)

