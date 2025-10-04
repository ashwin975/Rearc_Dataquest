import os
import aws_cdk as cdk
from data_pipeline_stack import DataPipelineStack

app = cdk.App()

DataPipelineStack(
    app,
    "DataPipelineStack1",
    stack_name="datapipeline1",
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"),
        region=os.getenv("CDK_DEFAULT_REGION")
    )
)

app.synth()
