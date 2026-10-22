#!/usr/bin/env bash
# ============================================================
# Stop Video Agent EC2 instance to minimize AWS billing
# ============================================================
set -euo pipefail

AWS_REGION="${AWS_REGION:-ap-south-1}"
PROFILE_ARG=""
if [[ -n "${AWS_PROFILE:-}" ]]; then
    PROFILE_ARG="--profile $AWS_PROFILE"
fi

echo "🔍 Finding Video Agent EC2 instance in $AWS_REGION..."
INSTANCE_ID=$(aws ec2 describe-instances \
    $PROFILE_ARG \
    --region "$AWS_REGION" \
    --filters "Name=tag:Project,Values=video-agent" "Name=instance-state-name,Values=running,pending" \
    --query "Reservations[].Instances[].InstanceId" \
    --output text)

if [[ -z "$INSTANCE_ID" || "$INSTANCE_ID" == "None" ]]; then
    echo "⚠️  No running Video Agent instance found."
    exit 0
fi

echo "🛑 Stopping EC2 instance $INSTANCE_ID ..."
aws ec2 stop-instances $PROFILE_ARG --region "$AWS_REGION" --instance-ids "$INSTANCE_ID" >/dev/null
echo "✓ Stop command issued."

echo
echo "============================================================"
echo "💡 COST & BILLING NOTICE WHILE STOPPED:"
echo "============================================================"
echo "  • EC2 Compute (t3.small): $0.00 / hour (100% saved!)"
echo "  • Public IPv4 Address:    RELEASED ($0.00 / hour saved)"
echo "  • SSM Parameter Store:    $0.00 (Standard tier free)"
echo "  • EBS gp3 Root Volume:    Billed at ~$0.08/GB-mo (~$2.00/mo for 25GB"
echo "                            or $0.00 if within AWS 30GB Free Tier)"
echo "  • S3 Backup Storage:      Billed at ~$0.023/GB-mo (fractions of a cent)"
echo
echo "  NOTE: When you start the instance again via scripts/start.sh,"
echo "  AWS assigns a new public IPv4 address. The script will output the new URL."
echo "============================================================"
