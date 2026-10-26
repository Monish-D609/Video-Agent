# ============================================================
# Start Video Agent EC2 instance and output application URL
# ============================================================
[CmdletBinding()]
param(
    [string]$Region = "ap-south-1",
    [string]$Profile = ""
)

Write-Host "Finding stopped Video Agent EC2 instance in $Region..." -ForegroundColor Cyan

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

$rawInstance = (& aws @argsList)
$instanceId = if ($rawInstance) { $rawInstance.Trim() } else { "" }

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
    $rawRunning = (& aws @runningArgs)
    $runningId = if ($rawRunning) { $rawRunning.Trim() } else { "" }

    if (-not [string]::IsNullOrWhiteSpace($runningId) -and $runningId -ne "None") {
        $instanceId = $runningId
        Write-Host "[INFO] Instance $instanceId is already running." -ForegroundColor Cyan
    } else {
        Write-Host "[WARN] No Video Agent instance found in stopped or running state." -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "[START] Starting EC2 instance $instanceId ..." -ForegroundColor Green
    $startArgs = @("ec2", "start-instances", "--region", $Region, "--instance-ids", $instanceId)
    if (-not [string]::IsNullOrWhiteSpace($Profile)) {
        $startArgs += @("--profile", $Profile)
    }
    & aws @startArgs | Out-Null

    Write-Host "Waiting for instance to enter running state..." -ForegroundColor Cyan
    $waitArgs = @("ec2", "wait", "instance-running", "--region", $Region, "--instance-ids", $instanceId)
    if (-not [string]::IsNullOrWhiteSpace($Profile)) {
        $waitArgs += @("--profile", $Profile)
    }
    & aws @waitArgs | Out-Null
    Write-Host "[OK] Instance is now running." -ForegroundColor Green
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

# Query Cloudflare HTTPS Tunnel URL via SSM with polling
$tunnelUrl = ""
Write-Host "Connecting to cloud services and retrieving HTTPS tunnel URL..." -ForegroundColor Cyan

$maxAttempts = 12
for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
    Write-Host "  * Checking cloud services (attempt $attempt of $maxAttempts)..." -ForegroundColor Gray
    Start-Sleep -Seconds 4
    try {
        $cmdArgs = @(
            "ssm", "send-command",
            "--region", $Region,
            "--instance-ids", $instanceId,
            "--document-name", "AWS-RunShellScript",
            "--parameters", "commands=[/opt/video-agent/get_tunnel_url.sh]",
            "--query", "Command.CommandId",
            "--output", "text"
        )
        if (-not [string]::IsNullOrWhiteSpace($Profile)) {
            $cmdArgs += @("--profile", $Profile)
        }
        $cmdId = (& aws @cmdArgs 2>$null)
        if ($cmdId) {
            $cmdId = $cmdId.Trim()
            Start-Sleep -Seconds 3
            $invArgs = @(
                "ssm", "get-command-invocation",
                "--region", $Region,
                "--command-id", $cmdId,
                "--instance-id", $instanceId,
                "--query", "StandardOutputContent",
                "--output", "text"
            )
            if (-not [string]::IsNullOrWhiteSpace($Profile)) {
                $invArgs += @("--profile", $Profile)
            }
            $rawOut = (& aws @invArgs 2>$null)
            if ($rawOut) {
                $candidate = $rawOut.Trim()
                if ($candidate.StartsWith("https://")) {
                    $tunnelUrl = $candidate
                    break
                }
            }
        }
    } catch {
        # SSM agent is still completing boot sequence
    }
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "Video Agent is running!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  * Instance ID:     $instanceId" -ForegroundColor White
Write-Host "  * Direct EC2 IP:   $publicIp" -ForegroundColor White
if ($tunnelUrl -and $tunnelUrl.StartsWith("https://")) {
    Write-Host "`n  ------------------------------------------------------------" -ForegroundColor Cyan
    Write-Host "  * Live Vercel App:  https://video-agent-cloud.vercel.app/?api=$tunnelUrl" -ForegroundColor Green
    Write-Host "  * Cloudflare URL:   $tunnelUrl" -ForegroundColor Yellow
    Write-Host "  ------------------------------------------------------------" -ForegroundColor Cyan
    Write-Host "  >>> SHARE THE VERCEL LINK WITH YOUR TEACHER TO OPEN ON PHONE! <<<" -ForegroundColor Yellow
    
    # Automatically open Vercel app in default browser
    try {
        Start-Process "https://video-agent-cloud.vercel.app/?api=$tunnelUrl"
    } catch {}
} else {
    Write-Host "  * Direct Web URL:  http://${publicIp}:8000" -ForegroundColor Gray
}
Write-Host "`n  (Works on any phone or browser with SSL encryption, 0 local setup)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
