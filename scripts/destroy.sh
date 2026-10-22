#!/usr/bin/env bash
# ============================================================
# Destroy Video Agent CDK stack and all associated AWS resources
# Ensures zero ongoing costs when you no longer need the project.
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
INFRA_DIR="$ROOT_DIR/infra"

echo "⚠️  WARNING: This will destroy all AWS infrastructure created by the Video Agent stack."
echo "   (EC2 instance, EBS root volume, Security Groups, IAM roles, S3 bucket contents)."
echo
read -r -p "Are you sure you want to proceed? (y/N): " CONFIRM
if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
    echo "Aborted."
    exit 0
fi

cd "$INFRA_DIR"

if command -v cdk >/dev/null 2>&1; then
    CDK_CMD="cdk"
else
    CDK_CMD="npx aws-cdk"
fi

echo "🧨 Running cdk destroy..."
$CDK_CMD destroy --force "$@"

echo
echo "============================================================"
echo "✅ All Video Agent AWS resources have been destroyed."
echo "   Ongoing monthly cost is now $0.00."
echo "============================================================"
