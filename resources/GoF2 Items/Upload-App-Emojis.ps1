<#
.SYNOPSIS
    Upload PNG files as Discord Application Emojis using the Discord API

.DESCRIPTION
    This script recursively searches for PNG files in subdirectories and uploads them
    as application emojis to Discord using the Discord API. It converts filenames to
    valid emoji names by stripping invalid characters and enforcing Discord’s naming
    rules (2–32 chars, alphanumeric and underscores only).

.NOTES
    Author: PowerShell Discord Emoji Uploader (modified)
    Version: 1.0
    Requirements:
      - PowerShell 5.1+
      - Discord Application with a valid Bot Token
      - PNG files (≤256 KB each) under the chosen folder
    API Reference: https://discord.com/developers/docs/resources/emoji#create-application-emoji
#>

#region Configuration — Edit these and then run

# Your Discord Application (Client) ID
$ApplicationId = "12345"

# Your Discord Bot Token (keep this secret!)
$BotToken       = "MTM3O...5jv8c"

# Folder to scan for PNGs (can be absolute or relative)
$SearchPath     = ".\"

# Maximum file size in KB (Discord limit: 256 KB)
$MaxFileSizeKB  = 256

# Set to $true to only simulate (no uploads); $false to actually upload
$DryRun         = $true

#endregion

#region Helper Functions

function Test-EmojiName {
    param([string]$Name)
    if ($Name.Length -lt 2 -or $Name.Length -gt 32) { return $false }
    return ($Name -match '^[a-zA-Z0-9_]+$')
}

function ConvertTo-EmojiName {
    param([string]$FileName)
    # strip extension, replace spaces/invalid chars, ensure length, fallback if needed
    $base = [IO.Path]::GetFileNameWithoutExtension($FileName)
    $clean = $base -replace '\s+', '' -replace '[^a-zA-Z0-9]', ''
    $clean = $clean.TrimStart('_')
    if ($clean.Length -lt 2) { $clean = "emoji_$clean" }
    if ($clean.Length -gt 32) { $clean = $clean.Substring(0,32) }
    if (-not (Test-EmojiName $clean)) {
        Write-Warning "→ Invalid emoji name from '$FileName'; using random fallback."
        $clean = "emoji_$([int](Get-Random -Minimum 100 -Maximum 999))"
    }
    return $clean.ToLower()
}

function ConvertTo-Base64DataUri {
    param([string]$Path)
    try {
        $bytes = [IO.File]::ReadAllBytes($Path)
        $b64   = [Convert]::ToBase64String($bytes)
        # Write-Host ("Base-64 Encoded: " + $b64)
        return "data:image/png;base64,$b64"
    } catch {
        Write-Error "Failed to convert '$Path' to Base64: $_"
        return $null
    }
}

function Invoke-DiscordEmojiUpload {
    param($AppId, $Token, $Name, $ImageData)
    $uri = "https://discord.com/api/v10/applications/$AppId/emojis"
    $hdr = @{
        Authorization = "Bot $Token"
        "Content-Type" = "application/json"
        "User-Agent"   = "PS-DiscordEmojiUploader/1.0"
    }
    $body = @{ name = $Name; image = $ImageData } | ConvertTo-Json
    try {
        return Invoke-RestMethod -Uri $uri -Method Post -Headers $hdr -Body $body -ErrorAction Stop
    } catch {
        $resp = $_.Exception.Response
        if ($resp) {
            $code = [int]$resp.StatusCode
            $msg  = ($resp.GetResponseStream() | 
                     %{ New-Object IO.StreamReader($_) } | 
                     %{ $_.ReadToEnd() } |
                     ConvertFrom-Json).message
        } else {
            $code = "N/A"; $msg = $_.Exception.Message
        }
        throw "HTTP $code — $msg"
    }
}

function Wait-RateLimit {
    param($Count)
    # pause every 30 requests
    if ($Count % 30 -eq 0) { Start-Sleep -Seconds 1 }
}

#endregion

# ——————————————————————————————————————————————————
# Main
# ——————————————————————————————————————————————————

Write-Host "`n=== Discord Emoji Uploader ===" -ForegroundColor Cyan
Write-Host "App ID: $ApplicationId" -ForegroundColor Green
Write-Host "Scan Path: $SearchPath" -ForegroundColor Green
Write-Host "Max Size: $MaxFileSizeKB KB" -ForegroundColor Green
if ($DryRun) { Write-Host "DRY RUN: No uploads will occur." -ForegroundColor Yellow }

if (-not (Test-Path $SearchPath)) {
    Write-Error "Search path '$SearchPath' does not exist."; exit 1
}

$pngs = Get-ChildItem -Path $SearchPath -Filter *.png -Recurse -File
if ($pngs.Count -eq 0) {
    Write-Warning "No PNGs found under '$SearchPath'."; exit 0
}

Write-Host "Found $($pngs.Count) PNG file(s)." -ForegroundColor Cyan
[int]$i=0; $succ=0; $skp=0; $err=0

foreach ($f in $pngs) {
    $i++
    Write-Host "`n[$i/$($pngs.Count)] Processing '$($f.Name)'" -NoNewline
    $sizeKB = [math]::Round($f.Length/1KB,2)
    Write-Host " ($sizeKB KB)" -ForegroundColor DarkGray

    if ($sizeKB -gt $MaxFileSizeKB) {
        Write-Warning "Skipping: exceeds limit."
        $skp++; continue
    }

    $ename = ConvertTo-EmojiName $f.Name
    Write-Host "→ Emoji Name: $ename" -ForegroundColor DarkGray

    $data = ConvertTo-Base64DataUri $f.FullName
    if (-not $data) { Write-Error "Conversion failed."; $err++; continue }
    Wait-RateLimit $i
    try {
        if ($DryRun) {
            Write-Host "[DRY] Would upload." -ForegroundColor Yellow
        }
        else {
            $resp = Invoke-DiscordEmojiUpload -AppId $ApplicationId -Token $BotToken -Name $ename -ImageData $data
            Write-Host "Success! ID: $($resp.id)" -ForegroundColor Green
        }
        $succ++
    } catch {
        Write-Error "Upload failed: $_"
        $err++
    }

}

# Summary
Write-Host "`n=== Summary ===" -ForegroundColor Cyan
Write-Host "Processed: $i" -ForegroundColor White
Write-Host "Uploaded:  $succ" -ForegroundColor Green
Write-Host "Skipped:   $skp" -ForegroundColor Yellow
Write-Host "Errors:    $err" -ForegroundColor Red

if ($DryRun) {
    Write-Host "`nDry run complete. Set `$DryRun = `$false at the top to perform real uploads." -ForegroundColor Yellow
}
