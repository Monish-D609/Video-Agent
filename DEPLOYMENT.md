# Video Agent - AWS Deployment Guide

This guide describes how to deploy **Video Agent** to Amazon Web Services (AWS) using the AWS CDK (Python).

---

## 🏗️ Architecture & Cost Model

The architecture is strictly designed to minimize AWS billing while ensuring fast and reliable video processing:

- **Compute**: A single EC2 `t3.small` instance running Amazon Linux 2023 with Docker.
  - Includes a **2 GB swap file** on gp3 storage to guarantee that local Whisper speech transcription and embedding indexing never trigger Out-Of-Memory (OOM) kills.
- **Storage & Backup**:
  - **EBS gp3**: 25 GB root volume (delete-on-termination).
  - **S3 Bucket**: Private, encrypted (SSE-S3), blocking all public access. Used exclusively for lightweight JSON persistence (`downloads/raw`, `downloads/processed`, `downloads/session`). Large audio files and temporary uploads are explicitly excluded from sync. Objects automatically expire after 30 days.
- **Security & Access**:
  - **IAM**: Least-privilege instance role.
  - **SSM Session Manager**: Direct encrypted browser/CLI terminal access (Port 22 SSH is completely closed).
  - **SSM Parameter Store**: Standard tier SecureString parameters for all external API keys (`/video-agent/*`).
  - **Security Group**: Restricts inbound traffic on port 8000 (and 80) to your specific IP address CIDR.
  - **Optional Token Guard**: Optional `APP_ACCESS_TOKEN` shared secret checked via FastAPI middleware to prevent unauthorized usage of your Cloudflare/Sarvam credits.
- **Cost Alarms**:
  - **AWS Budgets**: Configured to alert you via email at 50%, 80%, and 100% of actual spend, and 100% forecasted spend (default $5.00/month threshold).
- **Zero Cost Idle**:
  - **Zero NAT Gateways** (saving ~$32+/month).
  - **Zero Application Load Balancers** (saving ~$20+/month).
  - **Zero RDS / ElastiCache / ECS / OpenSearch / SageMaker**.

---

## 📋 Prerequisites

Before deploying, ensure you have the following installed on your local machine:

1. **AWS CLI v2**:
   ```bash
   aws --version
   ```
   Configure your credentials:
   ```bash
   aws configure
   # Or configure a named profile:
   # aws configure --profile my-profile
   ```
2. **Node.js 18+** (for AWS CDK CLI):
   ```bash
   node -v
   ```
3. **Python 3.10+**:
   ```bash
   python --version
   ```
4. **Git**: Checked out to the `Cloud-Integrated` branch:
   ```bash
   git status
   ```

---

## 🚀 Step-by-Step Deployment Commands

### Step 1: Install Dependencies

From the repository root:

```bash
# On Linux / macOS:
python3 -m venv .venv
source .venv/bin/activate
pip install -r infra/requirements.txt

# On Windows (PowerShell):
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r infra/requirements.txt
```

---

### Step 2: Store Secrets in AWS SSM Parameter Store

Run the interactive secret setup script. Secrets are sent directly to AWS Systems Manager Parameter Store as **SecureString** parameters—they never appear in Git or CloudFormation templates.

```bash
# On Linux / macOS:
chmod +x scripts/set_secrets.sh
./scripts/set_secrets.sh

# On Windows (PowerShell):
.\scripts\set_secrets.ps1
```

You will be prompted for:
1. `CLOUDFLARE_ACCOUNT_ID`: Your Cloudflare account ID.
2. `CLOUDFLARE_API_TOKEN`: Your Cloudflare Workers AI API token.
3. `SARVAM_API_KEY`: Your Sarvam AI API subscription key.
4. `APP_ACCESS_TOKEN` *(Optional)*: A secret token to protect your app (e.g. `my-secure-token-123`). If provided, anyone accessing the app must provide this token.
5. `WHISPER_MODEL` *(Optional, default: `base`)*: Model size (`base` or `small`).

---

### Step 3: Bootstrap AWS CDK (One-Time Setup)

If this is your first time deploying CDK in region `ap-south-1` (Mumbai):

```bash
# Retrieve your AWS Account ID:
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Bootstrap the CDK environment:
npx aws-cdk bootstrap aws://$ACCOUNT_ID/ap-south-1
```

*(On Windows PowerShell):*
```powershell
$accountId = (aws sts get-caller-identity --query Account --output text).Trim()
npx aws-cdk bootstrap "aws://$accountId/ap-south-1"
```

---

### Step 4: Verify Infrastructure & Cost Constraints

Run synthesis and execute the template verification guard:

```bash
# Synthesize the CloudFormation template
cd infra
npx aws-cdk synth

# Run the strict Cost & Resource Guard check
cd ..
python scripts/verify_template.py
```

The verification script checks every resource in the generated template and ensures:
- 0 NAT Gateways
- 0 Load Balancers (ALB/NLB)
- 0 RDS / OpenSearch / ECS / Secrets Manager
- Only allowed EC2, gp3, S3, IAM, and Budget resources exist.

---

### Step 5: Deploy the Stack

Deploy the stack to AWS. You can restrict the security group to your current public IP address and configure email alerts:

```bash
# Find your current public IP:
MY_IP="$(curl -s https://checkip.amazonaws.com)/32"

# Deploy via CDK:
cd infra
npx aws-cdk deploy \
  -c allowedCidr="$MY_IP" \
  -c budgetEmail="your-email@example.com" \
  -c budgetUsd="5"
```

*(On Windows PowerShell):*
```powershell
$myIp = "$((Invoke-RestMethod -Uri https://checkip.amazonaws.com).Trim())/32"

cd infra
npx aws-cdk deploy `
  -c allowedCidr=$myIp `
  -c budgetEmail="your-email@example.com" `
  -c budgetUsd=5
```

*Optional Flags:*
- `-c instanceType="t3.small"` (default: `t3.small`)
- `-c enableCloudFront=true` (creates a CloudFront distribution with `*.cloudfront.net` domain for free HTTPS)

When the deployment finishes, CDK outputs:
- `AppUrl`: The public web URL of your instance (`http://<PublicIp>:8000`).
- `InstanceId`: The EC2 instance ID.
- `BucketName`: The S3 bucket name.

---

## 🌐 Opening the App

Open your browser and navigate to the `AppUrl` displayed in the CDK output:

```
http://<Public-IP>:8000
```

- **If you set `APP_ACCESS_TOKEN`**: Open the URL with the token query parameter once:
  ```
  http://<Public-IP>:8000/?token=YOUR_ACCESS_TOKEN
  ```
  The frontend automatically saves the token in your browser's local storage and attaches it to all subsequent API calls.

---

## 💰 Cost Control: Stopping, Starting, and Destroying

### 1. Stopping the Instance (When Not In Use)

When you are done using Video Agent, stop the instance to avoid paying for EC2 compute:

```bash
# On Linux / macOS:
./scripts/stop.sh

# On Windows (PowerShell):
.\scripts\stop.ps1
```

**Billing While Stopped:**
- **EC2 Compute (vCPU & RAM)**: **$0.00** (100% saved).
- **Public IPv4 Address**: Released by AWS (**$0.00** saved).
- **EBS gp3 (25 GB)**: Billed at ~$0.08/GB-month = ~$2.00/month (or **$0.00** if within the 30 GB AWS Free Tier).
- **S3 State Storage**: Billed at ~$0.023/GB-month (< $0.05/month).

### 2. Starting the Instance

To resume work:

```bash
# On Linux / macOS:
./scripts/start.sh

# On Windows (PowerShell):
.\scripts\start.ps1
```

The script starts the instance, waits for it to become ready, and prints the new `http://<New-Public-IP>:8000` URL. The Docker service automatically boots, restores any S3 backup, and launches the container.

### 3. Destroying Everything (Zero Cost)

To tear down all resources completely so that ongoing costs drop to **$0.00**:

```bash
# On Linux / macOS:
./scripts/destroy.sh

# On Windows (PowerShell):
.\scripts\destroy.ps1
```

---

## 🔄 Updating the App

To deploy updates from the `Cloud-Integrated` branch:

1. Connect to your instance via AWS SSM Session Manager:
   ```bash
   aws ssm start-session --target <INSTANCE_ID>
   ```
2. Pull the latest code and rebuild the container:
   ```bash
   cd /opt/video-agent
   git pull origin Cloud-Integrated
   docker compose up -d --build
   ```

---

## ⚠️ Known Limitations & Troubleshooting

### 1. YouTube Datacenter IP Blocking
- **What happens**: YouTube frequently blocks or challenges audio/video downloads originating from cloud datacenters (AWS, GCP, Azure) with error messages such as `Sign in to confirm you're not a bot` or `HTTP Error 429: Too Many Requests`.
- **Built-in Fallback**: The app detects this condition and clearly prompts you to use the **Upload File** tab. Simply download the video or audio file to your local computer and drag-and-drop it into the web interface. Uploads are processed reliably through FFmpeg and Whisper.

### 2. Whisper Memory Headroom
- On a `t3.small` (2 GB RAM), running Whisper `small` alongside the embeddings model can occasionally approach memory limits.
- **Solution applied**:
  1. A **2 GB swap file** on gp3 EBS is configured automatically in the instance user-data.
  2. The default model is set to `WHISPER_MODEL=base`, which transcribes with high accuracy while consuming only ~500 MB RAM. If you prefer the `small` model, ensure swap is active.

### 3. S3 Persistence Verification
- Sync runs every 10 minutes via systemd timer `video-agent-backup.timer` and runs synchronously on shutdown/reboot.
- To trigger an immediate manual backup:
  ```bash
  /opt/video-agent/scripts/s3_sync.sh backup
  ```
- To view backup service logs:
  ```bash
  systemctl status video-agent-backup.service
  ```
