from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_s3 as s3,
    aws_sqs as sqs,
    aws_lambda as _lambda,
    aws_lambda_event_sources as lambda_event_sources,
    aws_events as events,
    aws_events_targets as targets,
    
    aws_s3_notifications as s3n,
)
from constructs import Construct
from aws_cdk import aws_ecr_assets as ecr_assets
from aws_cdk import aws_logs as logs
from aws_cdk.aws_lambda_python_alpha import PythonFunction, BundlingOptions

class PipelineStack(Stack):
        def __init__(self, scope: Construct, construct_id: str, **kwargs):
            super().__init__(scope, construct_id, **kwargs)


            # S3 Bucket
            bucket = s3.Bucket(
                self, "wipBucket",
                versioned=True,
                bucket_name="lambda-wip-bucket",
                block_public_access=None,
                removal_policy=RemovalPolicy.DESTROY,
                auto_delete_objects=True
            )

            # Ingestion Lambda Function
            ingest_fn = PythonFunction(
                self, "IngestFn",
                entry="lambdas/ingest",
                index="handler.py",
                handler="lambda_handler",
                runtime=_lambda.Runtime.PYTHON_3_12,
                architecture=_lambda.Architecture.ARM_64,
                timeout=Duration.minutes(5),
                log_retention=logs.RetentionDays.ONE_WEEK,
                environment={
                    "BUCKET_NAME": bucket.bucket_name,
                    "BLS_URL": "https://download.bls.gov/pub/time.series/pr/",
                    "API_URL": "https://honolulu-api.datausa.io/tesseract/data.jsonrecords?cube=acs_yg_total_population_1&drilldowns=Year%2CNation&locale=en&measures=Population",
                    "BLS_PREFIX": "bls-data/",
                    "API_PREFIX": "api-data/",
                    "JSON_FILE_NAME": "population.json",
                    "USER_AGENT": "Mozilla/5.0 (compatible; DataSyncBot/1.0)"
                },  
                bundling=BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_12.bundling_image,
                    platform="linux/arm64",
                    command=[
                        "bash","-lc",
                        # install deps into /asset-output, then copy source
                        "python -m pip install -r requirements.txt -t /asset-output && cp -R . /asset-output"
                    ],
                ),
            )

            bucket.grant_read_write(ingest_fn)

            # SQS Queue
            report_queue = sqs.Queue(
                self, "wipQueue",
                queue_name="wip-queue",
                visibility_timeout=Duration.minutes(10),
                retention_period=Duration.days(14)
            )

            # Schedule eventbridge to run daily
            events.Rule(
            self, "DailySchedule",
            schedule=events.Schedule.rate(Duration.days(1)),
            targets=[targets.LambdaFunction(ingest_fn)]
        )
            
            # S3 -> SQS on API JSON writes
            bucket.add_event_notification(
                s3.EventType.OBJECT_CREATED,
                s3n.SqsDestination(report_queue),
                s3.NotificationKeyFilter(prefix="api-data/", suffix=".json"),
            )

            # Report Lambda (Part 3)
            report_fn = PythonFunction(
                self, "ReportFn",
                entry="lambdas/report",
                index="handler.py",
                handler="lambda_handler",
                runtime=_lambda.Runtime.PYTHON_3_12,
                architecture=_lambda.Architecture.ARM_64,      # <-- run on ARM in Lambda
                timeout=Duration.minutes(3),
                memory_size=1024,                              # pandas likes some RAM
                log_retention=logs.RetentionDays.ONE_WEEK,
                environment={
                    "BUCKET_NAME": bucket.bucket_name,
                    "BLS_PREFIX": "bls-data/",
                    "API_PREFIX": "api-data/",
                    "JSON_FILE_NAME": "population.json",
                },
                bundling=BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_12.bundling_image,
                    platform="linux/arm64",  # <-- bundle for ARM on Apple silicon
                    command=[
                        "bash","-lc",
                        # install deps then copy sources into /asset-output
                        "python -m pip install -r requirements.txt -t /asset-output && cp -R . /asset-output"
                    ],
                ),
            )
            bucket.grant_read(report_fn)
            report_queue.grant_consume_messages(report_fn)

            # SQS event source for Report Lambda
            report_fn.add_event_source(lambda_event_sources.SqsEventSource(
            report_queue,
            batch_size=5,
            max_batching_window=Duration.seconds(10),
            report_batch_item_failures=True,
        ))