$path = ".\items"
$ApplicationId = "12345"
$BotToken = "MTM3O...5jv8c"



$uri = "https://discord.com/api/v10/applications/$ApplicationId/emojis"
$hdr = @{
    Authorization = "Bot $BotToken"
    "Content-Type" = "application/json"
    "User-Agent"   = "PS-DiscordEmojiUploader/1.0"
}

$allEmojis = Invoke-RestMethod -Uri $uri -Method Get -Headers $hdr -ErrorAction Stop


function ConvertTo-EmojiName {
    param([string]$objName)
    # strip extension, replace spaces/invalid chars, ensure length, fallback if needed
    $clean = $objName -replace '\s+', '' -replace '[^a-zA-Z0-9]', ''
    $clean = $clean.TrimStart('_')
    if ($clean.Length -lt 2) { $clean = "emoji_$clean" }
    if ($clean.Length -gt 32) { $clean = $clean.Substring(0,32) }
    return $clean.ToLower()
}
$count = 0

Get-ChildItem -Path $path -File -Recurse | Where-Object { $_.Name -eq "META.json" } | ForEach-Object {
    Write-Host $_.FullName
    $fileText = Get-Content -Path $_.FullName -Raw
    Write-Host $fileText
    $obj = ConvertFrom-Json ($fileText)
    $itemName = $obj.name
    Write-Host $itemName
    $itemNameFormatted = ConvertTo-EmojiName -objName $itemName
    Write-Host $itemNameFormatted
    $newEmojiId = ($allEmojis.items | Where-Object { $_.name -eq $itemNameFormatted }).id
    Write-Host $newEmojiId
    $newEmojiString = ("<:" + $itemNameFormatted + ":" + $newEmojiId + ">")
    if ($newEmojiId -ne $null) {
        if ($obj.emoji -eq $null) {
            $obj | Add-Member -MemberType NoteProperty -Name "emoji" -Value $newEmojiString
        }
        else {
            $obj.emoji=$newEmojiString
        }
    }
    $newObjString = (ConvertTo-Json $obj -Depth 5  | % { [System.Text.RegularExpressions.Regex]::Unescape($_) } )
    Write-Host $newObjString
    Out-File -FilePath $_.FullName -InputObject $newObjString -Encoding utf8 -Force
    $count++



}
Write-Host $count
