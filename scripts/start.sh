#!/usr/bin/env bash
# ============================================================
# Start Video Agent EC2 instance and output application URL
# ============================================================
set -euo pipefail

AWS_REGION="${AWS_REGION:-ap-south-1}"
PROFILE_ARG=""
if [[ -n "${AWS_PROFILE:-}" ]]; then
    PROFILE_ARG="--profile $AWS_PROFILE"
fi

echo "🔍 Finding stopped Video Agent EC2 instance in $AWS_REGION..."
INSTANCE_ID=$(aws ec2 describe-instances \
    $PROFILE_ARG \
    --region "$AWS_REGION" \
    --filters "Name=tag:Project,Values=video-agent" "Name=instance-state-name,Values=stopped" \
    --query "Reservations[].Instances[].InstanceId" \
    --output text)

if [[ -z "$INSTANCE_ID" || "$INSTANCE_ID" == "None" ]]; then
    # Check if already running
    RUNNING_ID=$(aws ec2 describe-instances \
        $PROFILE_ARG \
        --region "$AWS_REGION" \
        --filters "Name=tag:Project,Values=video-agent" "Name=instance-state-name,Values=running" \
        --query "Reservations[].Instances[].InstanceId" \
        --output text)
    if [[ -n "$RUNNING_ID" && "$RUNNING_ID" != "None" ]]; then
        INSTANCE_ID="$RUNNING_ID"
        echo "ℹ️  Instance $INSTANCE_ID is already running."
    else
        echo "⚠️  No Video Agent instance found in stopped or running state."
        exit 1
    fi
else
    echo "▶️  Starting EC2 instance $INSTANCE_ID ..."
    aws ec2 start-instances $PROFILE_ARG --region "$AWS_REGION" --instance-ids "$INSTANCE_ID" >/dev/null
    echo "⏳ Waiting for instance to enter running state..."
    aws ec2 wait instance-running $PROFILE_ARG --region "$AWS_REGION" --instance-ids "$INSTANCE_ID"
    echo "✓ Instance is now running."
fi

PUBLIC_IP=$(aws ec2 describe-instances \
    $PROFILE_ARG \
    --region "$AWS_REGION" \
    --instance-ids "$INSTANCE_ID" \
    --query "Reservations[0].Instances[0].PublicIpAddress" \
    --output text)

echo
echo "============================================================"
echo "🚀 Video Agent is running!"
echo "============================================================"
echo "  • Instance ID: $INSTANCE_ID"
echo "  • Public IP:   $PUBLIC_IP"
echo "  • App URL:     http://${PUBLIC_IP}:8000"
echo
echo "  (If you configured APP_ACCESS_TOKEN, append: ?token=YOUR_TOKEN)"
echo "  (Docker service auto-starts and restores backup from S3 at boot)"
echo "============================================================"
