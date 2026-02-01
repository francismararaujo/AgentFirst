"""AWS CDK App for AgentFirst2 MVP Infrastructure"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from aws_cdk import App, Environment
from stacks.core_stack import CoreStack
from stacks.lambda_stack import LambdaStack
from stacks.monitoring_stack import MonitoringStack
from stacks.polling_stack import PollingStack


def main():
    """Create and configure CDK app"""
    app = App()

    # Get environment variables
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    aws_account = os.getenv("AWS_ACCOUNT_ID", "")
    environment_name = os.getenv("ENVIRONMENT", "development")

    # Define AWS environment
    env = Environment(
        account=aws_account,
        region=aws_region
    )

    # Create stacks
    core_stack = CoreStack(
        app,
        f"agentfirst-core-{environment_name}",
        env=env,
        environment_name=environment_name,
        description="AgentFirst2 MVP - Core Infrastructure (DynamoDB, SNS, SQS, KMS)"
    )

    lambda_stack = LambdaStack(
        app,
        f"agentfirst-lambda-{environment_name}",
        env=env,
        environment_name=environment_name,
        core_stack=core_stack,
        description="AgentFirst2 MVP - Lambda & API Gateway"
    )

    monitoring_stack = MonitoringStack(
        app,
        f"agentfirst-monitoring-{environment_name}",
        env=env,
        environment_name=environment_name,
        lambda_stack=lambda_stack,
        description="AgentFirst2 MVP - CloudWatch & X-Ray Monitoring"
    )

    polling_stack = PollingStack(
        app,
        f"agentfirst-polling-{environment_name}",
        env=env,
        environment=environment_name,
        description="AgentFirst2 MVP - iFood Polling Service (ECS Fargate)"
    )

    # Add dependencies
    lambda_stack.add_dependency(core_stack)
    monitoring_stack.add_dependency(lambda_stack)
    polling_stack.add_dependency(lambda_stack)

    app.synth()


if __name__ == "__main__":
    main()
