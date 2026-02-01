"""Core Infrastructure Stack for AgentFirst2 MVP

This stack creates:
- DynamoDB tables (Users, Sessions, Memory, Usage, Audit Logs, Escalation)
- SNS topics (Omnichannel, Retail events)
- SQS queues (with DLQ)
- KMS encryption keys
"""

from aws_cdk import (
    Stack,
    aws_dynamodb as dynamodb,
    aws_sns as sns,
    aws_sqs as sqs,
    aws_kms as kms,
    Duration,
    RemovalPolicy,
    CfnOutput,
)
from constructs import Construct


class CoreStack(Stack):
    """Core infrastructure stack with DynamoDB, SNS, SQS, and KMS"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment_name: str = "development",
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.environment_name = environment_name

        # Create KMS key for encryption
        self.kms_key = self._create_kms_key()

        # Create DynamoDB tables
        self.users_table = self._create_users_table()
        self.sessions_table = self._create_sessions_table()
        self.memory_table = self._create_memory_table()
        self.usage_table = self._create_usage_table()
        self.audit_logs_table = self._create_audit_logs_table()
        self.escalation_table = self._create_escalation_table()
        self.otp_table = self._create_otp_table()
        self.merchants_table = self._create_merchants_table()

        # Create SNS topics
        self.omnichannel_topic = self._create_omnichannel_topic()
        self.retail_topic = self._create_retail_topic()

        # Create SQS queues
        self.dlq, self.queue = self._create_sqs_queue()

        # Output ARNs and URLs
        self._create_outputs()

    def _create_kms_key(self) -> kms.Key:
        """Create KMS key for encryption"""
        key = kms.Key(
            self,
            "AgentFirstKMSKey",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.RETAIN,
            description="KMS key for AgentFirst2 MVP encryption",
        )
        return key

    def _create_users_table(self) -> dynamodb.Table:
        """Create Users DynamoDB table"""
        table = dynamodb.Table(
            self,
            "UsersTable",
            partition_key=dynamodb.Attribute(
                name="email",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.kms_key,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.RETAIN,
            table_name=f"agentfirst-users-{self.environment_name}",
        )
        return table

    def _create_sessions_table(self) -> dynamodb.Table:
        """Create Sessions DynamoDB table with TTL"""
        table = dynamodb.Table(
            self,
            "SessionsTable",
            partition_key=dynamodb.Attribute(
                name="email",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="session_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.kms_key,
            point_in_time_recovery=True,
            time_to_live_attribute="expires_at",
            removal_policy=RemovalPolicy.RETAIN,
            table_name=f"agentfirst-sessions-{self.environment_name}",
        )
        return table

    def _create_memory_table(self) -> dynamodb.Table:
        """Create Memory DynamoDB table with GSI"""
        table = dynamodb.Table(
            self,
            "MemoryTable",
            partition_key=dynamodb.Attribute(
                name="email",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.NUMBER
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.kms_key,
            point_in_time_recovery=True,
            time_to_live_attribute="expires_at",
            removal_policy=RemovalPolicy.RETAIN,
            table_name=f"agentfirst-memory-{self.environment_name}",
            # Enable DynamoDB Streams for event sourcing
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
        )

        # Add GSI for domain queries
        table.add_global_secondary_index(
            index_name="domain-index",
            partition_key=dynamodb.Attribute(
                name="domain",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.NUMBER
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        return table

    def _create_usage_table(self) -> dynamodb.Table:
        """Create Usage DynamoDB table"""
        table = dynamodb.Table(
            self,
            "UsageTable",
            partition_key=dynamodb.Attribute(
                name="email",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="month",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.kms_key,
            time_to_live_attribute="expires_at",
            removal_policy=RemovalPolicy.RETAIN,
            table_name=f"agentfirst-usage-{self.environment_name}",
        )
        return table

    def _create_audit_logs_table(self) -> dynamodb.Table:
        """Create Audit Logs DynamoDB table (immutable)"""
        table = dynamodb.Table(
            self,
            "AuditLogsTable",
            partition_key=dynamodb.Attribute(
                name="email",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.NUMBER
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.kms_key,
            point_in_time_recovery=True,
            time_to_live_attribute="expires_at",
            removal_policy=RemovalPolicy.RETAIN,
            table_name=f"agentfirst-audit-logs-{self.environment_name}",
        )

        # Add GSI for agent queries
        table.add_global_secondary_index(
            index_name="agent-index",
            partition_key=dynamodb.Attribute(
                name="agent",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.NUMBER
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        return table

    def _create_escalation_table(self) -> dynamodb.Table:
        """Create Escalation DynamoDB table"""
        table = dynamodb.Table(
            self,
            "EscalationTable",
            partition_key=dynamodb.Attribute(
                name="escalation_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.kms_key,
            time_to_live_attribute="expires_at",
            removal_policy=RemovalPolicy.RETAIN,
            table_name=f"agentfirst-escalation-{self.environment_name}",
        )

        # Add GSI for user queries
        table.add_global_secondary_index(
            index_name="user-index",
            partition_key=dynamodb.Attribute(
                name="email",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="created_at",
                type=dynamodb.AttributeType.NUMBER
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        return table

    def _create_otp_table(self) -> dynamodb.Table:
        """Create OTP DynamoDB table"""
        table = dynamodb.Table(
            self,
            "OTPTable",
            partition_key=dynamodb.Attribute(
                name="email",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.kms_key,
            time_to_live_attribute="expires_at",
            removal_policy=RemovalPolicy.RETAIN,
            table_name=f"agentfirst-otp-{self.environment_name}",
        )
        return table

    def _create_merchants_table(self) -> dynamodb.Table:
        """Create Merchants DynamoDB table for multi-tenant iFood integration"""
        table = dynamodb.Table(
            self,
            "MerchantsTable",
            partition_key=dynamodb.Attribute(
                name="merchant_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="user_email",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.kms_key,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.RETAIN,
            table_name=f"agentfirst-merchants-{self.environment_name}",
        )

        # GSI for querying active merchants (used by polling service)
        table.add_global_secondary_index(
            index_name="status-index",
            partition_key=dynamodb.Attribute(
                name="status",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="created_at",
                type=dynamodb.AttributeType.NUMBER
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # GSI for querying merchants by user email
        table.add_global_secondary_index(
            index_name="user-email-index",
            partition_key=dynamodb.Attribute(
                name="user_email",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="created_at",
                type=dynamodb.AttributeType.NUMBER
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        return table

    def _create_omnichannel_topic(self) -> sns.Topic:
        """Create SNS topic for omnichannel events"""
        topic = sns.Topic(
            self,
            "OmnichannelTopic",
            display_name="AgentFirst2 Omnichannel Events",
            topic_name=f"agentfirst-omnichannel-{self.environment_name}",
            master_key=self.kms_key,
        )
        return topic

    def _create_retail_topic(self) -> sns.Topic:
        """Create SNS topic for retail events"""
        topic = sns.Topic(
            self,
            "RetailTopic",
            display_name="AgentFirst2 Retail Events",
            topic_name=f"agentfirst-retail-{self.environment_name}",
            master_key=self.kms_key,
        )
        return topic

    def _create_sqs_queue(self) -> tuple:
        """Create SQS queue with DLQ"""
        # Create DLQ
        dlq = sqs.Queue(
            self,
            "DLQ",
            queue_name=f"agentfirst-dlq-{self.environment_name}",
            retention_period=Duration.days(14),
            encryption=sqs.QueueEncryption.KMS,
            encryption_master_key=self.kms_key,
        )

        # Create main queue
        queue = sqs.Queue(
            self,
            "Queue",
            queue_name=f"agentfirst-queue-{self.environment_name}",
            visibility_timeout=Duration.seconds(300),
            retention_period=Duration.days(4),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=dlq
            ),
            encryption=sqs.QueueEncryption.KMS,
            encryption_master_key=self.kms_key,
        )

        return dlq, queue

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs"""
        CfnOutput(
            self,
            "UsersTableName",
            value=self.users_table.table_name,
            export_name=f"agentfirst-users-table-{self.environment_name}",
        )

        CfnOutput(
            self,
            "SessionsTableName",
            value=self.sessions_table.table_name,
            export_name=f"agentfirst-sessions-table-{self.environment_name}",
        )

        CfnOutput(
            self,
            "MemoryTableName",
            value=self.memory_table.table_name,
            export_name=f"agentfirst-memory-table-{self.environment_name}",
        )

        CfnOutput(
            self,
            "UsageTableName",
            value=self.usage_table.table_name,
            export_name=f"agentfirst-usage-table-{self.environment_name}",
        )

        CfnOutput(
            self,
            "AuditLogsTableName",
            value=self.audit_logs_table.table_name,
            export_name=f"agentfirst-audit-logs-table-{self.environment_name}",
        )

        CfnOutput(
            self,
            "EscalationTableName",
            value=self.escalation_table.table_name,
            export_name=f"agentfirst-escalation-table-{self.environment_name}",
        )

        CfnOutput(
            self,
            "OTPTableName",
            value=self.otp_table.table_name,
            export_name=f"agentfirst-otp-table-{self.environment_name}",
        )

        CfnOutput(
            self,
            "OmnichannelTopicArn",
            value=self.omnichannel_topic.topic_arn,
            export_name=f"agentfirst-omnichannel-topic-{self.environment_name}",
        )

        CfnOutput(
            self,
            "RetailTopicArn",
            value=self.retail_topic.topic_arn,
            export_name=f"agentfirst-retail-topic-{self.environment_name}",
        )

        CfnOutput(
            self,
            "QueueUrl",
            value=self.queue.queue_url,
            export_name=f"agentfirst-queue-url-{self.environment_name}",
        )

        CfnOutput(
            self,
            "DLQUrl",
            value=self.dlq.queue_url,
            export_name=f"agentfirst-dlq-url-{self.environment_name}",
        )

        CfnOutput(
            self,
            "KMSKeyId",
            value=self.kms_key.key_id,
            export_name=f"agentfirst-kms-key-{self.environment_name}",
        )
