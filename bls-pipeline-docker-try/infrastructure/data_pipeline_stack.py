import os
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_lambda as _lambda,
    aws_s3 as s3,
    aws_events as events,
    aws_events_targets as targets,
    aws_logs as logs,
)
from constructs import Construct


def _bool_env(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")


class DataPipelineStack(Stack):
    def __init__(self, scope: Construct, stack_id: str, **kwargs):
        super().__init__(scope, stack_id, **kwargs)

        # ---------- Config (envs are optional; safe defaults used) ----------
        # Exact, fixed bucket name you requested
        bucket_name_raw = os.getenv("BUCKET_NAME", "quest-part-4-02")
        bucket_name = bucket_name_raw.lower().replace("_", "-").strip()

        # If you already created the bucket manually and want to reuse it, set:
        #   IMPORT_EXISTING_BUCKET=true
        import_existing_bucket = _bool_env("IMPORT_EXISTING_BUCKET", False)

        # Fixed Lambda name to match your existing log group
        lambda_function_name = os.getenv("LAMBDA_FUNCTION_NAME", "data-analysis-function")

        bls_url = os.getenv("BLS_URL", "")
        bls_prefix = os.getenv("BLS_PREFIX", "bls_data/").strip()
        api_url = os.getenv("API_URL", "")
        api_prefix = os.getenv("API_PREFIX", "api_data/").strip()
        json_file_name = os.getenv("JSON_FILE_NAME", "population.json").strip()

        # ---------- S3 bucket: create or import ----------
        if import_existing_bucket:
            # Reuse an existing bucket with the exact name
            bucket = s3.Bucket.from_bucket_name(
                self, "DataPipelineBucket", bucket_name=bucket_name
            )
            created_bucket = False
        else:
            # Create the bucket with the exact name
            bucket = s3.Bucket(
                self,
                "DataPipelineBucket",
                bucket_name=bucket_name,
                versioned=True,
                removal_policy=RemovalPolicy.DESTROY,   # dev/test only; RETAIN for prod
                auto_delete_objects=True,               # requires custom resource (needs bootstrap)
            )
            created_bucket = True

        # ---------- Lambda from Docker image (built from ../lambda_src) ----------
        # NOTE: DockerImageFunction requires CDK bootstrap to publish the image asset.
        fn = _lambda.DockerImageFunction(
            self,
            "DataAnalysisLambda",
            code=_lambda.DockerImageCode.from_image_asset(directory="../lambda_src"),
            function_name=lambda_function_name,  # fixed physical name
            timeout=Duration.minutes(15),
            memory_size=1024,
            environment={
                "BUCKET_NAME": bucket_name,
                "BLS_URL": bls_url,
                "BLS_PREFIX": bls_prefix,
                "API_URL": api_url,
                "API_PREFIX": api_prefix,
                "JSON_FILE_NAME": json_file_name,
            },
        )

        # ---------- Reuse existing CloudWatch Log Group ----------
        # By default, CDK would synthesize a LogGroup child that CFN tries to CREATE.
        # That fails if the log group already exists. Remove that child so CFN won't create it.
        synthesized_lg = fn.node.try_find_child("LogGroup")
        if synthesized_lg:
            fn.node.try_remove_child("LogGroup")

        # OPTIONAL: If you want CDK to set retention on the existing group, uncomment:
        # logs.LogRetention(
        #     self, "DataAnalysisLogRetention",
        #     log_group_name=f"/aws/lambda/{lambda_function_name}",
        #     retention=logs.RetentionDays.ONE_MONTH,
        # )

        # ---------- Permissions ----------
        # For imported buckets, use grant APIs from the imported object:
        # (It still attaches to the correct underlying bucket policy/IAM)
        if created_bucket:
            bucket.grant_read_write(fn)
        else:
            bucket.grant_read_write(fn)

        # ---------- Schedule: daily at UTC midnight ----------
        rule = events.Rule(
            self,
            "DailySchedule",
            schedule=events.Schedule.cron(minute="0", hour="0"),
        )
        rule.add_target(targets.LambdaFunction(fn))

        # ---------- Optional: nice outputs ----------
        cdk.CfnOutput(self, "DataBucketName", value=bucket_name)
        cdk.CfnOutput(self, "LambdaName", value=lambda_function_name)
