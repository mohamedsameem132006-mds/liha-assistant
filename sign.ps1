# Liha Assistant Authenticode Signing Script
param(
    [string]$TargetExe = ".\dist\LihaAssistant\LihaAssistant.exe"
)

$target = Resolve-Path $TargetExe
Write-Host "Target: $target"

$cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert | Where-Object { $_.Subject -like '*Liha AI Assistant*' } | Select-Object -First 1

if (-not $cert) {
    Write-Host "Creating new local CodeSigning certificate..."
    $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject "CN=Liha AI Assistant, O=Liha AI, C=US" -CertStoreLocation "Cert:\CurrentUser\My" -NotAfter (Get-Date).AddYears(5)
    
    $cerPath = Join-Path $env:TEMP "LihaCert.cer"
    Export-Certificate -Cert $cert -FilePath $cerPath | Out-Null
    Import-Certificate -FilePath $cerPath -CertStoreLocation "Cert:\CurrentUser\Root" | Out-Null
    Import-Certificate -FilePath $cerPath -CertStoreLocation "Cert:\CurrentUser\TrustedPublisher" | Out-Null
    Remove-Item $cerPath -ErrorAction SilentlyContinue
    Write-Host "Created and trusted certificate: $($cert.Thumbprint)"
} else {
    Write-Host "Using existing certificate: $($cert.Thumbprint)"
}

$sig = Set-AuthenticodeSignature -FilePath $target -Certificate $cert -HashAlgorithm SHA256
Write-Host "Signature Status: $($sig.Status)"
Get-AuthenticodeSignature $target | Format-List
