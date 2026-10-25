# ============================================================
# Interactive PowerShell script to store Video Agent secrets in AWS SSM
# Standard tier SecureString parameters (Free Tier eligible)
# ============================================================
[CmdletBinding()]
param()

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Video Agent - AWS SSM Parameter Store Setup (SecureString)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Note: Secrets will NEVER be stored in git or CloudFormation templates.`n"

$regionInput = Read-Host "Enter AWS Region [ap-south-1]"
$awsRegion = if ([string]::IsNullOrWhiteSpace($regionInput)) { "ap-south-1" } else { $regionInput.Trim() }

$profileInput = Read-Host "Enter AWS CLI profile (leave empty for default)"
$awsProfile = $profileInput.Trim()

# Read local .env if present to provide seamless defaults
$envDefaults = @{}
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$envPath = Join-Path (Split-Path -Parent $scriptDir) ".env"
if (Test-Path $envPath) {
    Get-Content $envPath | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $parts = $line.Split("=", 2)
            $envDefaults[$parts[0].Trim()] = $parts[1].Trim()
        }
    }
}

function Put-Secret {
    param(
        [string]$ParamName,
        [string]$Prompt,
        [string]$DefaultVal = "",
        [bool]$AsSecure = $false
    )

    $val = ""
    if ($AsSecure) {
        $sec = Read-Host -Prompt $Prompt -AsSecureString
        $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
        $val = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
        [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)
    } else {
        $val = Read-Host -Prompt $Prompt
    }

    if ([string]::IsNullOrWhiteSpace($val) -and -not [string]::IsNullOrWhiteSpace($DefaultVal)) {
        $val = $DefaultVal
    }

    if (-not [string]::IsNullOrWhiteSpace($val)) {
        $argsList = @(
            "ssm", "put-parameter",
            "--region", $awsRegion,
            "--name", $ParamName,
            "--type", "SecureString",
            "--value", $val,
            "--overwrite",
            "--tier", "Standard"
        )
        if (-not [string]::IsNullOrWhiteSpace($awsProfile)) {
            $argsList += @("--profile", $awsProfile)
        }

        & aws @argsList | Out-Null
        Write-Host "  ✓ Saved $ParamName" -ForegroundColor Green
    } else {
        Write-Host "  - Skipped $ParamName (empty)" -ForegroundColor Yellow
    }
}

Write-Host "`n1. Cloudflare Workers AI Secrets" -ForegroundColor White
$cfIdPrompt = if ($envDefaults["CLOUDFLARE_ACCOUNT_ID"]) { "Enter CLOUDFLARE_ACCOUNT_ID [found in .env]" } else { "Enter CLOUDFLARE_ACCOUNT_ID" }
Put-Secret -ParamName "/video-agent/CLOUDFLARE_ACCOUNT_ID" -Prompt $cfIdPrompt -DefaultVal $envDefaults["CLOUDFLARE_ACCOUNT_ID"] -AsSecure $false

$cfTokenPrompt = if ($envDefaults["CLOUDFLARE_API_TOKEN"]) { "Enter CLOUDFLARE_API_TOKEN [found in .env, press Enter to use]" } else { "Enter CLOUDFLARE_API_TOKEN" }
Put-Secret -ParamName "/video-agent/CLOUDFLARE_API_TOKEN" -Prompt $cfTokenPrompt -DefaultVal $envDefaults["CLOUDFLARE_API_TOKEN"] -AsSecure ($null -eq $envDefaults["CLOUDFLARE_API_TOKEN"])

Write-Host "`n2. Sarvam AI Secret (for Hinglish Speech-to-Text)" -ForegroundColor White
$sarvamPrompt = if ($envDefaults["SARVAM_API_KEY"]) { "Enter SARVAM_API_KEY [found in .env, press Enter to use]" } else { "Enter SARVAM_API_KEY" }
Put-Secret -ParamName "/video-agent/SARVAM_API_KEY" -Prompt $sarvamPrompt -DefaultVal $envDefaults["SARVAM_API_KEY"] -AsSecure ($null -eq $envDefaults["SARVAM_API_KEY"])

Write-Host "`n3. Application Security & Model Config" -ForegroundColor White
Put-Secret -ParamName "/video-agent/APP_ACCESS_TOKEN" -Prompt "Enter APP_ACCESS_TOKEN (optional, shared secret to guard API, or press enter to leave open)" -DefaultVal $envDefaults["APP_ACCESS_TOKEN"] -AsSecure $false
$whisperDefault = if ($envDefaults["WHISPER_MODEL"]) { $envDefaults["WHISPER_MODEL"] } else { "base" }
Put-Secret -ParamName "/video-agent/WHISPER_MODEL" -Prompt "Enter WHISPER_MODEL [$whisperDefault]" -DefaultVal $whisperDefault -AsSecure $false

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "✅ All parameters configured in SSM Parameter Store ($awsRegion)." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
