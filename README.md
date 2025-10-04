# Rearc Data Quest

Table of Contents

Overview

Architecture

Repository Structure

Prerequisites

Setup & Usage

Part 1 — BLS Data → S3

Part 2 — Population API → S3

Part 3 — Analysis & Joins

Part 4 — IaC with AWS CDK

Proof of Execution

Operational Notes

Roadmap


## Part 1

Links to data in S3 :
Source Code : Source Code : population.ipynb

- [pr.series](https://rearc-data-quest-ssm.s3.us-east-2.amazonaws.com/bls/pr/pr.series)
pr.txt
pr.measure
pr.period
pr.seasonal
pr.sector
pr.duration
pr.footnote
pr.contacts
pr.data.0.Current
pr.data.1.AllData
pr.class


## Gist on what the script is doing and my bucket configs and why I chose those configurations, mention tag if used. Paste an image output of this s3 bucket.

Public datasets are fetched from BLS URL and published to `rearc-data-quest-ssm` S3 bucket. The sync script ensures:
- Files are dynamically discovered
- Duplicates are avoided
- Files are streamed directly to S3 without local storage
- Setup does not throw 403 error and is compliant with BLS data access policies

**S3 Bucket Configurations**
- Chose General Purpose Bucket
- Added a RearcDataQuest project tag
- Enabled versioning for traceability and rollbacks
- Used SSE-S3 for encryption (since its safe for public data). Will switch to SSE-KMS for sensitive data.

## If I had time, I will?

I would add recursive search for nested directores inside the pr/ directory. Currently the script parses the flat directory at /pub/time.series/pr/ but I would implement recursive traversal for potential subfolders within pr/ path
I would use retry strategy for request Session. This would enable automatic retries on time-out issues or other common network errors.
I would implement and store log.csv file in S3 to append metadata about uploads and structured events (like hash mismatch, upload success/failure, skipped files etc). This would improve auditing
I would also add more file validation techniques. Currently the script only compares hash of files in source and datalake but I'd expand it to include file size comparison, last modified timestamps and possibly a checksum strategy for byte comparison.
I would include a staging area like a \tmp folder to preprocess files or enable batch processing (If the files need to be zipped before upload or in other scenarios). But as of now, the script directly streams data into S3 since it is ideal for lightweight public datasets.
Upload Result



## Part 2
Source Code : population.ipynb

Link to data in S3 : nation_population.json

Future Continous Improvement (Find synonym)

Since Part 1 and Part 2 have the same functionality, I would implement the enhancements listed in part 1 like retry for request Session, have a metadata logging file and possibly include a staging area


## Part 3

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

## Part 4

## CHANGE PIPELINE NAME

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

