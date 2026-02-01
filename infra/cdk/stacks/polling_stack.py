"""ECS Fargate Stack for iFood Polling Service

This stack creates a long-running ECS Fargate task that polls the iFood API
every 30 seconds to keep the store open and receive order events.
"""

from aws_cdk import (
    Stack,
    Duration,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_logs as logs,
    aws_iam as iam,
    RemovalPolicy,
)
from constructs import Construct


class PollingStack(Stack):
    """Stack for iFood polling service using ECS Fargate"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Use default VPC (or create one if needed)
        vpc = ec2.Vpc.from_lookup(self, "VPC", is_default=True)

        # Create ECS Cluster
        cluster = ecs.Cluster(
            self,
            "PollingCluster",
            cluster_name=f"agentfirst-polling-{environment}",
            vpc=vpc,
            container_insights=True,
        )

        # Create CloudWatch Log Group
        log_group = logs.LogGroup(
            self,
            "PollingLogGroup",
            log_group_name=f"/ecs/agentfirst-polling-{environment}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Create Task Execution Role (for pulling image and writing logs)
        execution_role = iam.Role(
            self,
            "TaskExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy"
                ),
            ],
        )

        # Create Task Role (for application permissions)
        task_role = iam.Role(
            self,
            "TaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )

        # Grant same permissions as Lambda function
        # Secrets Manager
        task_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:DescribeSecret",
                ],
                resources=["arn:aws:secretsmanager:*:*:secret:*"],
            )
        )

        # DynamoDB
        task_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                ],
                resources=["arn:aws:dynamodb:*:*:table/agentfirst-*"],
            )
        )

        # SNS
        task_role.add_to_policy(
            iam.PolicyStatement(
                actions=["sns:Publish"],
                resources=["arn:aws:sns:*:*:agentfirst-*"],
            )
        )

        # SQS
        task_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "sqs:SendMessage",
                    "sqs:ReceiveMessage",
                    "sqs:DeleteMessage",
                ],
                resources=["arn:aws:sqs:*:*:agentfirst-*"],
            )
        )

        # CloudWatch Logs
        task_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=["*"],
            )
        )

        # Create Task Definition
        task_definition = ecs.FargateTaskDefinition(
            self,
            "PollingTaskDef",
            family=f"agentfirst-polling-{environment}",
            cpu=256,  # 0.25 vCPU
            memory_limit_mib=512,  # 0.5 GB
            execution_role=execution_role,
            task_role=task_role,
        )

        # Add container to task definition
        # Use the same Docker image asset as the Lambda function
        import pathlib
        project_root = pathlib.Path(__file__).parent.parent.parent.parent
        
        container = task_definition.add_container(
            "PollingContainer",
            image=ecs.ContainerImage.from_asset(
                str(project_root),
                exclude=["infra/cdk/cdk.out", "**/*.pyc", "**/__pycache__", ".git"]
            ),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="polling",
                log_group=log_group,
            ),
            environment={
                "ENVIRONMENT": environment,
                "AWS_REGION": self.region,
            },
            # Override entrypoint and command to run Python script
            # Working directory in Lambda image is /var/task
            entry_point=["python"],
            command=["/var/task/scripts/ifood_heartbeat.py"],
        )

        # Create ECS Service
        service = ecs.FargateService(
            self,
            "PollingService",
            service_name=f"agentfirst-polling-{environment}",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=1,  # Keep 1 task running at all times
            assign_public_ip=True,  # Required for pulling from ECR
            health_check_grace_period=Duration.seconds(60),
            min_healthy_percent=0,  # Allow task to restart without keeping old one
            max_healthy_percent=100,
        )

        # Output the service name
        self.service_name = service.service_name
        self.cluster_name = cluster.cluster_name
