import os
from constructs import Construct
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    Tags,
    aws_ec2 as ec2,
    aws_s3 as s3,
    aws_iam as iam,
    aws_budgets as budgets,
)


class VideoAgentStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Apply cost allocation and identification stack tag
        Tags.of(self).add("Project", "video-agent")

        # -------------------------------------------------------------
        # 1. Context Parameters
        # -------------------------------------------------------------
        instance_type_str = self.node.try_get_context("instanceType") or "t3.small"
        allowed_cidr = self.node.try_get_context("allowedCidr") or "0.0.0.0/0"
        budget_usd = float(self.node.try_get_context("budgetUsd") or 5.0)
        budget_email = self.node.try_get_context("budgetEmail")
        enable_cloudfront = str(self.node.try_get_context("enableCloudFront")).lower() == "true"
        vpc_id = self.node.try_get_context("vpcId")

        # -------------------------------------------------------------
        # 2. VPC (Default VPC or minimal public-subnet-only VPC, 0 NAT)
        # -------------------------------------------------------------
        # We NEVER create NAT Gateways to avoid exorbitant idle costs ($32+/mo each).
        if self.account and self.account != "unknown-account" and not self.node.try_get_context("useIsolatedVpc"):
            try:
                if vpc_id:
                    vpc = ec2.Vpc.from_lookup(self, "Vpc", vpc_id=vpc_id)
                else:
                    vpc = ec2.Vpc.from_lookup(self, "Vpc", is_default=True)
            except Exception:
                vpc = ec2.Vpc(
                    self,
                    "Vpc",
                    max_azs=2,
                    nat_gateways=0,
                    subnet_configuration=[
                        ec2.SubnetConfiguration(
                            name="Public",
                            subnet_type=ec2.SubnetType.PUBLIC,
                            cidr_mask=24,
                        )
                    ],
                )
        else:
            vpc = ec2.Vpc(
                self,
                "Vpc",
                max_azs=2,
                nat_gateways=0,
                subnet_configuration=[
                    ec2.SubnetConfiguration(
                        name="Public",
                        subnet_type=ec2.SubnetType.PUBLIC,
                        cidr_mask=24,
                    )
                ],
            )

        # -------------------------------------------------------------
        # 3. S3 Bucket (Private backup of raw, processed, session state)
        # -------------------------------------------------------------
        bucket = s3.Bucket(
            self,
            "StateBackupBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=False,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="ExpireOldBackupsAfter30Days",
                    expiration=Duration.days(30),
                )
            ],
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # -------------------------------------------------------------
        # 4. IAM Instance Role (Least-privilege)
        # -------------------------------------------------------------
        instance_role = iam.Role(
            self,
            "InstanceRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            description="Least-privilege EC2 role for Video Agent",
        )

        # SSM Session Manager access (no SSH keys or port 22 needed)
        instance_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")
        )

        # Grant S3 bucket read/write/delete (for s3 sync)
        bucket.grant_read_write(instance_role)
        instance_role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:DeleteObject"],
                resources=[bucket.arn_for_objects("*")],
            )
        )

        # Grant access to SSM Parameter Store for /video-agent/* only
        instance_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ssm:GetParameter",
                    "ssm:GetParameters",
                    "ssm:GetParametersByPath",
                ],
                resources=[
                    f"arn:{self.partition}:ssm:{self.region}:{self.account}:parameter/video-agent/*"
                ],
            )
        )

        # Allow KMS decrypt using default AWS SSM key alias for SecureString
        instance_role.add_to_policy(
            iam.PolicyStatement(
                actions=["kms:Decrypt"],
                resources=[f"arn:{self.partition}:kms:{self.region}:{self.account}:alias/aws/ssm"],
            )
        )

        # -------------------------------------------------------------
        # 5. Security Group (No SSH, Port 8000 restricted to allowedCidr)
        # -------------------------------------------------------------
        security_group = ec2.SecurityGroup(
            self,
            "SecurityGroup",
            vpc=vpc,
            description="Security Group for Video Agent - No SSH, restricted web access",
            allow_all_outbound=True,
        )

        security_group.add_ingress_rule(
            peer=ec2.Peer.ipv4(allowed_cidr),
            connection=ec2.Port.tcp(8000),
            description="Video Agent Web UI and FastAPI endpoints",
        )
        security_group.add_ingress_rule(
            peer=ec2.Peer.ipv4(allowed_cidr),
            connection=ec2.Port.tcp(80),
            description="HTTP fallback / reverse proxy port",
        )

        # -------------------------------------------------------------
        # 6. EC2 Instance (Amazon Linux 2023, gp3 EBS, 2GB swap, Docker)
        # -------------------------------------------------------------
        machine_image = ec2.MachineImage.latest_amazon_linux2023(
            cpu_type=ec2.AmazonLinuxCpuType.X86_64
        )

        # User Data script
        user_data = ec2.UserData.for_linux()
        user_data.add_commands(
            "#!/bin/bash",
            "set -euxo pipefail",
            "",
            "# 1. Setup 2 GB Swap File on gp3 to guarantee memory headroom",
            "if [ ! -f /swapfile ]; then",
            "    dd if=/dev/zero of=/swapfile bs=128M count=16",
            "    chmod 600 /swapfile",
            "    mkswap /swapfile",
            "    swapon /swapfile",
            "    echo '/swapfile swap swap defaults 0 0' >> /etc/fstab",
            "fi",
            "",
            "# 2. Install Docker, Git, and Docker Compose plugin",
            "dnf update -y",
            "dnf install -y docker git",
            "systemctl enable --now docker",
            "usermod -aG docker ec2-user",
            "DOCKER_CONFIG=/usr/local/lib/docker",
            "mkdir -p $DOCKER_CONFIG/cli-plugins",
            "curl -SL https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-x86_64 -o $DOCKER_CONFIG/cli-plugins/docker-compose",
            "chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose",
            "",
            "# 3. Clone Repository at branch Cloud-Integrated",
            "APP_DIR=/opt/video-agent",
            "mkdir -p /etc/video-agent",
            f"echo '{bucket.bucket_name}' > /etc/video-agent/bucket.name",
            "if [ ! -d '$APP_DIR' ]; then",
            "    git clone -b Cloud-Integrated https://github.com/Monish-D609/Video-Agent.git $APP_DIR",
            "else",
            "    cd $APP_DIR && git fetch origin && git checkout Cloud-Integrated && git pull",
            "fi",
            "cd $APP_DIR",
            "chown -R ec2-user:ec2-user $APP_DIR",
            "",
            "# 4. Fetch secrets from SSM Parameter Store into .env",
            f"AWS_REGION='{self.region}'",
            "get_ssm_param() {",
            "    local name=\"$1\"",
            "    aws ssm get-parameter --region \"$AWS_REGION\" --name \"$name\" --with-decryption --query 'Parameter.Value' --output text 2>/dev/null || echo ''",
            "}",
            "CLOUDFLARE_ACCOUNT_ID=$(get_ssm_param '/video-agent/CLOUDFLARE_ACCOUNT_ID')",
            "CLOUDFLARE_API_TOKEN=$(get_ssm_param '/video-agent/CLOUDFLARE_API_TOKEN')",
            "SARVAM_API_KEY=$(get_ssm_param '/video-agent/SARVAM_API_KEY')",
            "APP_ACCESS_TOKEN=$(get_ssm_param '/video-agent/APP_ACCESS_TOKEN')",
            "WHISPER_MODEL=$(get_ssm_param '/video-agent/WHISPER_MODEL')",
            "if [ -z \"$WHISPER_MODEL\" ]; then WHISPER_MODEL='base'; fi",
            "",
            "cat <<EOF > $APP_DIR/.env",
            "CLOUDFLARE_ACCOUNT_ID=$CLOUDFLARE_ACCOUNT_ID",
            "CLOUDFLARE_API_TOKEN=$CLOUDFLARE_API_TOKEN",
            "SARVAM_API_KEY=$SARVAM_API_KEY",
            "APP_ACCESS_TOKEN=$APP_ACCESS_TOKEN",
            "WHISPER_MODEL=$WHISPER_MODEL",
            "CACHE_DIR=/app/downloads",
            "EOF",
            "chmod 600 $APP_DIR/.env",
            "",
            "# 5. Restore metadata backup from S3",
            "chmod +x $APP_DIR/scripts/s3_sync.sh",
            f"S3_BUCKET='{bucket.bucket_name}' APP_DIR=$APP_DIR $APP_DIR/scripts/s3_sync.sh restore || true",
            "",
            "# 6. Configure Systemd Service for Video Agent Compose",
            "cat <<'EOF' > /etc/systemd/system/video-agent.service",
            "[Unit]",
            "Description=Video Agent Docker Compose Application",
            "Requires=docker.service",
            "After=docker.service network-online.target",
            "Wants=network-online.target",
            "",
            "[Service]",
            "Type=oneshot",
            "RemainAfterExit=yes",
            "WorkingDirectory=/opt/video-agent",
            "ExecStart=/usr/local/lib/docker/cli-plugins/docker-compose up -d --build",
            "ExecStop=/usr/local/lib/docker/cli-plugins/docker-compose down",
            "TimeoutStartSec=0",
            "",
            "[Install]",
            "WantedBy=multi-user.target",
            "EOF",
            "",
            "# 7. Configure S3 Backup Service & Timer (every 10 minutes and on shutdown)",
            "cat <<EOF > /etc/systemd/system/video-agent-backup.service",
            "[Unit]",
            "Description=Video Agent S3 Metadata Backup Service",
            "After=network.target",
            "",
            "[Service]",
            "Type=oneshot",
            f"Environment='S3_BUCKET={bucket.bucket_name}'",
            "Environment='APP_DIR=/opt/video-agent'",
            "ExecStart=/opt/video-agent/scripts/s3_sync.sh backup",
            "EOF",
            "",
            "cat <<'EOF' > /etc/systemd/system/video-agent-backup.timer",
            "[Unit]",
            "Description=Run Video Agent S3 Backup every 10 minutes",
            "",
            "[Timer]",
            "OnBootSec=5min",
            "OnUnitActiveSec=10min",
            "Persistent=true",
            "",
            "[Install]",
            "WantedBy=timers.target",
            "EOF",
            "",
            "systemctl daemon-reload",
            "systemctl enable --now video-agent.service",
            "systemctl enable --now video-agent-backup.timer",
        )

        instance = ec2.Instance(
            self,
            "Instance",
            instance_type=ec2.InstanceType(instance_type_str),
            machine_image=machine_image,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_group=security_group,
            role=instance_role,
            user_data=user_data,
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/xvda",
                    volume=ec2.BlockDeviceVolume.ebs(
                        volume_size=25,
                        volume_type=ec2.EbsDeviceVolumeType.GP3,
                        delete_on_termination=True,
                        encrypted=True,
                    ),
                )
            ],
            detailed_monitoring=False,  # Basic CloudWatch metrics only (free)
        )

        # -------------------------------------------------------------
        # 7. AWS Budget + Email Alerts (Cost control alarm)
        # -------------------------------------------------------------
        if budget_email:
            notifications = [
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        comparison_operator="GREATER_THAN",
                        threshold=50.0,
                        threshold_type="PERCENTAGE",
                        notification_type="ACTUAL",
                    ),
                    subscribers=[
                        budgets.CfnBudget.SubscriberProperty(
                            address=budget_email,
                            subscription_type="EMAIL",
                        )
                    ],
                ),
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        comparison_operator="GREATER_THAN",
                        threshold=80.0,
                        threshold_type="PERCENTAGE",
                        notification_type="ACTUAL",
                    ),
                    subscribers=[
                        budgets.CfnBudget.SubscriberProperty(
                            address=budget_email,
                            subscription_type="EMAIL",
                        )
                    ],
                ),
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        comparison_operator="GREATER_THAN",
                        threshold=100.0,
                        threshold_type="PERCENTAGE",
                        notification_type="ACTUAL",
                    ),
                    subscribers=[
                        budgets.CfnBudget.SubscriberProperty(
                            address=budget_email,
                            subscription_type="EMAIL",
                        )
                    ],
                ),
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        comparison_operator="GREATER_THAN",
                        threshold=100.0,
                        threshold_type="PERCENTAGE",
                        notification_type="FORECASTED",
                    ),
                    subscribers=[
                        budgets.CfnBudget.SubscriberProperty(
                            address=budget_email,
                            subscription_type="EMAIL",
                        )
                    ],
                ),
            ]

            budgets.CfnBudget(
                self,
                "MonthlyCostBudget",
                budget=budgets.CfnBudget.BudgetDataProperty(
                    budget_name="video-agent-monthly-budget",
                    budget_type="COST",
                    time_unit="MONTHLY",
                    budget_limit=budgets.CfnBudget.SpendProperty(
                        amount=budget_usd,
                        unit="USD",
                    ),
                ),
                notifications_with_subscribers=notifications,
            )

        # -------------------------------------------------------------
        # 8. Optional CloudFront (Default *.cloudfront.net domain only)
        # -------------------------------------------------------------
        if enable_cloudfront:
            from aws_cdk import aws_cloudfront as cloudfront
            from aws_cdk import aws_cloudfront_origins as origins

            distribution = cloudfront.Distribution(
                self,
                "CloudFrontDistribution",
                default_behavior=cloudfront.BehaviorOptions(
                    origin=origins.HttpOrigin(
                        instance.instance_public_dns_name,
                        http_port=8000,
                        protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY,
                    ),
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
                ),
                comment="Video Agent free HTTPS distribution (*.cloudfront.net domain)",
            )

            CfnOutput(
                self,
                "CloudFrontHttpsUrl",
                value=f"https://{distribution.distribution_domain_name}",
                description="Video Agent HTTPS App URL via CloudFront",
            )

        # -------------------------------------------------------------
        # 9. Stack Outputs
        # -------------------------------------------------------------
        CfnOutput(
            self,
            "AppUrl",
            value=f"http://{instance.instance_public_ip}:8000",
            description="Video Agent Direct EC2 Web URL",
        )

        CfnOutput(
            self,
            "InstanceId",
            value=instance.instance_id,
            description="EC2 Instance ID for SSM Session Manager and cost management",
        )

        CfnOutput(
            self,
            "BucketName",
            value=bucket.bucket_name,
            description="S3 Bucket Name for metadata persistence",
        )
