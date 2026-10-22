# ============================================================
# Destroy Video Agent CDK stack and all associated AWS resources
# Ensures zero ongoing costs when you no longer need the project.
# ============================================================
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ExtraArgs
)

Write-Host "⚠️  WARNING: This will destroy all AWS infrastructure created by the Video Agent stack." -ForegroundColor Red
Write-Host "   (EC2 instance, EBS root volume, Security Groups, IAM roles, S3 bucket contents).`n" -ForegroundColor Yellow

$confirm = Read-Host "Are you sure you want to proceed? (y/N)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "Aborted." -ForegroundColor Yellow
    exit 0
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$infraDir = Join-Path (Split-Path -Parent $scriptDir) "infra"

Set-Location $infraDir

$cdkCmd = if (Get-Command "cdk" -ErrorAction SilentlyContinue) { "cdk" } else { "npx" }
$cdkArgs = if ($cdkCmd -eq "npx") { @("aws-cdk", "destroy", "--force") } else { @("destroy", "--force") }
if ($ExtraArgs) {
    $cdkArgs += $ExtraArgs
}

Write-Host "🧨 Running cdk destroy..." -ForegroundColor Yellow
& $cdkCmd @cdkArgs

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "✅ All Video Agent AWS resources have been destroyed." -ForegroundColor Green
Write-Host "   Ongoing monthly cost is now `$0.00." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
