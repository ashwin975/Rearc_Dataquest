import aws_cdk as cdk
from data_pipeline_stack import PipelineStack  

app = cdk.App()
PipelineStack(app, "PipelineStack")
app.synth()
