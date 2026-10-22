#!/usr/bin/env bash
# ============================================================
# Interactive script to store Video Agent secrets in AWS SSM
# Standard tier SecureString parameters (Free Tier eligible)
# ============================================================
set -euo pipefail

echo "============================================================"
echo " Video Agent - AWS SSM Parameter Store Setup (SecureString)"
echo "============================================================"
echo "Note: Secrets will NEVER be stored in git or CloudFormation templates."
echo

read -r -p "Enter AWS Region [ap-south-1]: " AWS_REGION
AWS_REGION="${AWS_REGION:-ap-south-1}"

read -r -p "Enter AWS CLI profile (leave empty for default): " AWS_PROFILE
PROFILE_ARG=""
if [[ -n "$AWS_PROFILE" ]]; then
    PROFILE_ARG="--profile $AWS_PROFILE"
fi

put_secret() {
    local param_name="$1"
    local prompt_text="$2"
    local default_val="${3:-}"
    local is_silent="${4:-true}"

    local secret_val=""
    if [[ "$is_silent" == "true" ]]; then
        read -r -s -p "$prompt_text" secret_val
        echo
    else
        read -r -p "$prompt_text" secret_val
    fi

    if [[ -z "$secret_val" && -n "$default_val" ]]; then
        secret_val="$default_val"
    fi

    if [[ -n "$secret_val" ]]; then
        aws ssm put-parameter \
            $PROFILE_ARG \
            --region "$AWS_REGION" \
            --name "$param_name" \
            --type "SecureString" \
            --value "$secret_val" \
            --overwrite \
            --tier "Standard" >/dev/null
        echo "  ✓ Saved $param_name"
    else
        echo "  - Skipped $param_name (empty)"
    fi
}

echo
echo "1. Cloudflare Workers AI Secrets"
put_secret "/video-agent/CLOUDFLARE_ACCOUNT_ID" "Enter CLOUDFLARE_ACCOUNT_ID: " "" false
put_secret "/video-agent/CLOUDFLARE_API_TOKEN" "Enter CLOUDFLARE_API_TOKEN: " "" true

echo
echo "2. Sarvam AI Secret (for Hinglish Speech-to-Text)"
put_secret "/video-agent/SARVAM_API_KEY" "Enter SARVAM_API_KEY: " "" true

echo
echo "3. Application Security & Model Config"
put_secret "/video-agent/APP_ACCESS_TOKEN" "Enter APP_ACCESS_TOKEN (optional, shared secret to guard API, or press enter to leave open): " "" false
put_secret "/video-agent/WHISPER_MODEL" "Enter WHISPER_MODEL [base]: " "base" false

echo
echo "============================================================"
echo "✅ All parameters configured in SSM Parameter Store ($AWS_REGION)."
echo "============================================================"
