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
Put-Secret -ParamName "/video-agent/CLOUDFLARE_ACCOUNT_ID" -Prompt "Enter CLOUDFLARE_ACCOUNT_ID" -AsSecure $false
Put-Secret -ParamName "/video-agent/CLOUDFLARE_API_TOKEN" -Prompt "Enter CLOUDFLARE_API_TOKEN" -AsSecure $true

Write-Host "`n2. Sarvam AI Secret (for Hinglish Speech-to-Text)" -ForegroundColor White
Put-Secret -ParamName "/video-agent/SARVAM_API_KEY" -Prompt "Enter SARVAM_API_KEY" -AsSecure $true

Write-Host "`n3. Application Security & Model Config" -ForegroundColor White
Put-Secret -ParamName "/video-agent/APP_ACCESS_TOKEN" -Prompt "Enter APP_ACCESS_TOKEN (optional, shared secret to guard API, or press enter to leave open)" -AsSecure $false
Put-Secret -ParamName "/video-agent/WHISPER_MODEL" -Prompt "Enter WHISPER_MODEL [base]" -DefaultVal "base" -AsSecure $false

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "✅ All parameters configured in SSM Parameter Store ($awsRegion)." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
