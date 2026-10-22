# ============================================================
# Stop Video Agent EC2 instance to minimize AWS billing
# ============================================================
[CmdletBinding()]
param(
    [string]$Region = "ap-south-1",
    [string]$Profile = ""
)

Write-Host "🔍 Finding Video Agent EC2 instance in $Region..." -ForegroundColor Cyan

$argsList = @(
    "ec2", "describe-instances",
    "--region", $Region,
    "--filters", "Name=tag:Project,Values=video-agent", "Name=instance-state-name,Values=running,pending",
    "--query", "Reservations[].Instances[].InstanceId",
    "--output", "text"
)
if (-not [string]::IsNullOrWhiteSpace($Profile)) {
    $argsList += @("--profile", $Profile)
}

$instanceId = (& aws @argsList).Trim()

if ([string]::IsNullOrWhiteSpace($instanceId) -or $instanceId -eq "None") {
    Write-Host "⚠️  No running Video Agent instance found." -ForegroundColor Yellow
    exit 0
}

Write-Host "🛑 Stopping EC2 instance $instanceId ..." -ForegroundColor Yellow
$stopArgs = @("ec2", "stop-instances", "--region", $Region, "--instance-ids", $instanceId)
if (-not [string]::IsNullOrWhiteSpace($Profile)) {
    $stopArgs += @("--profile", $Profile)
}
& aws @stopArgs | Out-Null
Write-Host "✓ Stop command issued." -ForegroundColor Green

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "💡 COST & BILLING NOTICE WHILE STOPPED:" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  • EC2 Compute (t3.small): `$0.00 / hour (100% saved!)" -ForegroundColor Green
Write-Host "  • Public IPv4 Address:    RELEASED (`$0.00 / hour saved)" -ForegroundColor Green
Write-Host "  • SSM Parameter Store:    `$0.00 (Standard tier free)" -ForegroundColor Green
Write-Host "  • EBS gp3 Root Volume:    Billed at ~`$0.08/GB-mo (~`$2.00/mo for 25GB" -ForegroundColor Yellow
Write-Host "                            or `$0.00 if within AWS 30GB Free Tier)" -ForegroundColor Yellow
Write-Host "  • S3 Backup Storage:      Billed at ~`$0.023/GB-mo (fractions of a cent)" -ForegroundColor Yellow
Write-Host "`n  NOTE: When you start the instance again via scripts/start.ps1," -ForegroundColor Cyan
Write-Host "  AWS assigns a new public IPv4 address. The script will output the new URL." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
