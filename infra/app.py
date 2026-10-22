#!/usr/bin/env python3
import os
import aws_cdk as cdk
from video_agent_stack import VideoAgentStack

app = cdk.App()

account = os.environ.get("CDK_DEFAULT_ACCOUNT", os.environ.get("AWS_ACCOUNT_ID"))
region = os.environ.get("CDK_DEFAULT_REGION", os.environ.get("AWS_DEFAULT_REGION", "ap-south-1"))

env = cdk.Environment(account=account, region=region) if account else None

VideoAgentStack(
    app,
    "VideoAgentStack",
    env=env,
    description="Video Agent single-instance deployment stack with S3 backup and SSM secrets",
)

app.synth()
