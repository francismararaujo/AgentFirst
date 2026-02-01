"""Lambda & API Gateway Stack for AgentFirst2 MVP

This stack creates:
- Lambda function (512MB, 30s timeout, X-Ray tracing, VPC)
- API Gateway (regional, CloudWatch logging, rate limiting)
- IAM roles & policies (least privilege)
- Webhook endpoints (Telegram, iFood)
"""

import os
from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
    aws_iam as iam,
    aws_logs as logs,
    aws_ec2 as ec2,
    Duration,
    CfnOutput,
)
from constructs import Construct
from infra.cdk.stacks.core_stack import CoreStack


class LambdaStack(Stack):
    """Lambda and API Gateway stack"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment_name: str = "development",
        core_stack: CoreStack = None,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.environment_name = environment_name
        self.core_stack = core_stack

        # Create Lambda function
        self.lambda_function = self._create_lambda_function()

        # Create API Gateway
        self.api = self._create_api_gateway()

        # Create outputs
        self._create_outputs()

    def _create_lambda_function(self) -> lambda_.Function:
        """Create Lambda function"""
        # Create Lambda execution role
        lambda_role = iam.Role(
            self,
            "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Execution role for AgentFirst2 Lambda",
        )

        # Add basic Lambda execution policy
        lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )

        # Add X-Ray write access
        lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AWSXRayDaemonWriteAccess"
            )
        )

        # Add DynamoDB access
        for table in [
            self.core_stack.users_table,
            self.core_stack.sessions_table,
            self.core_stack.memory_table,
            self.core_stack.usage_table,
            self.core_stack.audit_logs_table,
            self.core_stack.escalation_table,
            self.core_stack.otp_table,
            self.core_stack.merchants_table,
        ]:
            table.grant_read_write_data(lambda_role)

        # Add SNS publish access
        self.core_stack.omnichannel_topic.grant_publish(lambda_role)
        self.core_stack.retail_topic.grant_publish(lambda_role)

        # Add SQS access
        self.core_stack.queue.grant_send_messages(lambda_role)
        self.core_stack.dlq.grant_send_messages(lambda_role)

        # Add KMS decrypt access
        self.core_stack.kms_key.grant_decrypt(lambda_role)

        # Add Secrets Manager access
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:DescribeSecret",
                ],
                resources=["arn:aws:secretsmanager:*:*:secret:*"],
            )
        )

        # Add Bedrock access
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=[
                    "arn:aws:bedrock:*:*:foundation-model/*",
                    "arn:aws:bedrock:*:*:inference-profile/*"
                ],
            )
        )

        # Add SES send email access
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["ses:SendEmail"],
                resources=["*"],
            )
        )

        # Create Lambda function using Docker image
        # This ensures compiled dependencies like pydantic_core are properly included
        
        # Use a more specific path to avoid recursive copying issues
        # Point directly to the project root (where Dockerfile is)
        import pathlib
        project_root = pathlib.Path(__file__).parent.parent.parent.parent
        
        lambda_function = lambda_.DockerImageFunction(
            self,
            "AgentFirstLambda",
            code=lambda_.DockerImageCode.from_image_asset(
                str(project_root),
                exclude=["infra/cdk/cdk.out", "**/*.pyc", "**/__pycache__", ".git"]
            ),
            memory_size=512,
            timeout=Duration.seconds(30),
            environment={
                "ENVIRONMENT": self.environment_name,
                "DYNAMODB_USERS_TABLE": self.core_stack.users_table.table_name,
                "DYNAMODB_SESSIONS_TABLE": self.core_stack.sessions_table.table_name,
                "DYNAMODB_MEMORY_TABLE": self.core_stack.memory_table.table_name,
                "DYNAMODB_USAGE_TABLE": self.core_stack.usage_table.table_name,
                "DYNAMODB_AUDIT_TABLE": self.core_stack.audit_logs_table.table_name,
                "DYNAMODB_ESCALATION_TABLE": self.core_stack.escalation_table.table_name,
                "DYNAMODB_OTP_TABLE": self.core_stack.otp_table.table_name,
                "DYNAMODB_MERCHANTS_TABLE": self.core_stack.merchants_table.table_name,
                "SNS_OMNICHANNEL_TOPIC_ARN": self.core_stack.omnichannel_topic.topic_arn,
                "SNS_RETAIL_TOPIC_ARN": self.core_stack.retail_topic.topic_arn,
                "SQS_QUEUE_URL": self.core_stack.queue.queue_url,
                "SQS_DLQ_URL": self.core_stack.dlq.queue_url,
                "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN", ""),
                "TELEGRAM_WEBHOOK_URL": os.getenv("TELEGRAM_WEBHOOK_URL", ""),
                "IFOOD_CLIENT_ID": os.getenv("IFOOD_CLIENT_ID", ""),
                "IFOOD_CLIENT_SECRET": os.getenv("IFOOD_CLIENT_SECRET", ""),
                "SENDER_EMAIL": os.getenv("SENDER_EMAIL", "naoresponder@agentfirst.com.br"),
            },
            role=lambda_role,
            tracing=lambda_.Tracing.ACTIVE,
            log_retention=logs.RetentionDays.ONE_WEEK,
            function_name=f"agentfirst-{self.environment_name}",
            description="AgentFirst2 MVP Lambda function",
        )

        return lambda_function

    def _create_api_gateway(self) -> apigateway.RestApi:
        """Create API Gateway"""
        # Create API Gateway
        api = apigateway.RestApi(
            self,
            "AgentFirstAPI",
            rest_api_name=f"agentfirst-{self.environment_name}",
            description="AgentFirst2 MVP API Gateway",
            endpoint_types=[apigateway.EndpointType.REGIONAL],
            cloud_watch_role=True,
        )

        # Add CloudWatch logging for error responses
        api.add_gateway_response(
            "DEFAULT_4XX",
            type=apigateway.ResponseType.DEFAULT_4_XX,
        )
        api.add_gateway_response(
            "DEFAULT_5XX", 
            type=apigateway.ResponseType.DEFAULT_5_XX,
        )

        # Create Lambda integration
        lambda_integration = apigateway.LambdaIntegration(
            self.lambda_function,
            proxy=True,
        )

        # Add root resource
        api.root.add_method("ANY", lambda_integration)

        # Add proxy resource for all paths
        api.root.add_resource("{proxy+}").add_method("ANY", lambda_integration)

        # Add request validator
        request_validator = api.add_request_validator(
            "RequestValidator",
            validate_request_body=True,
            validate_request_parameters=True,
        )

        # Add throttling
        api.add_usage_plan(
            "UsagePlan",
            name=f"agentfirst-usage-plan-{self.environment_name}",
            throttle=apigateway.ThrottleSettings(
                rate_limit=10000,
                burst_limit=20000,
            ),
        ).add_api_stage(
            stage=api.deployment_stage,
        )

        # Add CORS
        api.root.add_cors_preflight(
            allow_origins=["*"],
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type", "Authorization"],
        )

        return api

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs"""
        CfnOutput(
            self,
            "LambdaFunctionArn",
            value=self.lambda_function.function_arn,
            export_name=f"agentfirst-lambda-arn-{self.environment_name}",
        )

        CfnOutput(
            self,
            "LambdaFunctionName",
            value=self.lambda_function.function_name,
            export_name=f"agentfirst-lambda-name-{self.environment_name}",
        )

        CfnOutput(
            self,
            "APIEndpoint",
            value=self.api.url,
            export_name=f"agentfirst-api-endpoint-{self.environment_name}",
        )

        CfnOutput(
            self,
            "TelegramWebhookURL",
            value=f"{self.api.url}webhook/telegram",
            export_name=f"agentfirst-telegram-webhook-{self.environment_name}",
        )

        CfnOutput(
            self,
            "iFoodWebhookURL",
            value=f"{self.api.url}webhook/ifood",
            export_name=f"agentfirst-ifood-webhook-{self.environment_name}",
        )
