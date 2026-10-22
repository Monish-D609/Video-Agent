# ============================================================
# Start Video Agent EC2 instance and output application URL
# ============================================================
[CmdletBinding()]
param(
    [string]$Region = "ap-south-1",
    [string]$Profile = ""
)

Write-Host "🔍 Finding stopped Video Agent EC2 instance in $Region..." -ForegroundColor Cyan

$argsList = @(
    "ec2", "describe-instances",
    "--region", $Region,
    "--filters", "Name=tag:Project,Values=video-agent", "Name=instance-state-name,Values=stopped",
    "--query", "Reservations[].Instances[].InstanceId",
    "--output", "text"
)
if (-not [string]::IsNullOrWhiteSpace($Profile)) {
    $argsList += @("--profile", $Profile)
}

$instanceId = (& aws @argsList).Trim()

if ([string]::IsNullOrWhiteSpace($instanceId) -or $instanceId -eq "None") {
    $runningArgs = @(
        "ec2", "describe-instances",
        "--region", $Region,
        "--filters", "Name=tag:Project,Values=video-agent", "Name=instance-state-name,Values=running",
        "--query", "Reservations[].Instances[].InstanceId",
        "--output", "text"
    )
    if (-not [string]::IsNullOrWhiteSpace($Profile)) {
        $runningArgs += @("--profile", $Profile)
    }
    $runningId = (& aws @runningArgs).Trim()

    if (-not [string]::IsNullOrWhiteSpace($runningId) -and $runningId -ne "None") {
        $instanceId = $runningId
        Write-Host "ℹ️  Instance $instanceId is already running." -ForegroundColor Cyan
    } else {
        Write-Host "⚠️  No Video Agent instance found in stopped or running state." -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "▶️  Starting EC2 instance $instanceId ..." -ForegroundColor Green
    $startArgs = @("ec2", "start-instances", "--region", $Region, "--instance-ids", $instanceId)
    if (-not [string]::IsNullOrWhiteSpace($Profile)) {
        $startArgs += @("--profile", $Profile)
    }
    & aws @startArgs | Out-Null

    Write-Host "⏳ Waiting for instance to enter running state..." -ForegroundColor Cyan
    $waitArgs = @("ec2", "wait", "instance-running", "--region", $Region, "--instance-ids", $instanceId)
    if (-not [string]::IsNullOrWhiteSpace($Profile)) {
        $waitArgs += @("--profile", $Profile)
    }
    & aws @waitArgs | Out-Null
    Write-Host "✓ Instance is now running." -ForegroundColor Green
}

$ipArgs = @(
    "ec2", "describe-instances",
    "--region", $Region,
    "--instance-ids", $instanceId,
    "--query", "Reservations[0].Instances[0].PublicIpAddress",
    "--output", "text"
)
if (-not [string]::IsNullOrWhiteSpace($Profile)) {
    $ipArgs += @("--profile", $Profile)
}
$publicIp = (& aws @ipArgs).Trim()

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "🚀 Video Agent is running!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  • Instance ID: $instanceId" -ForegroundColor White
Write-Host "  • Public IP:   $publicIp" -ForegroundColor White
Write-Host "  • App URL:     http://${publicIp}:8000" -ForegroundColor Yellow
Write-Host "`n  (If you configured APP_ACCESS_TOKEN, append: ?token=YOUR_TOKEN)" -ForegroundColor Gray
Write-Host "  (Docker service auto-starts and restores backup from S3 at boot)" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Cyan
