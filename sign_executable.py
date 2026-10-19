"""
Liha Assistant - Windows Authenticode Code Signing Utility
Signs Windows executables and DLLs for Smart App Control and SmartScreen compliance.
Supports:
  1. Production PFX file (via LIHA_SIGN_PFX_PATH and LIHA_SIGN_PFX_PASSWORD env vars)
  2. Windows Certificate Store (via LIHA_SIGN_CERT_THUMBPRINT env var)
  3. Trusted Local Development Certificate (via --dev flag)
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

DEFAULT_TIMESTAMP_URL = os.environ.get("LIHA_TIMESTAMP_SERVER", "http://timestamp.digicert.com")

def verify_signature(target_path: Path) -> bool:
    """Check whether the binary has a valid Authenticode signature."""
    ps_cmd = f"(Get-AuthenticodeSignature -FilePath '{target_path}').Status.ToString()"
    res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True)
    status = res.stdout.strip()
    print(f"[SignTool] Signature status for {target_path.name}: {status}")
    return status == "Valid"

def sign_with_pfx(target_path: Path, pfx_path: str, password: str, timestamp_url: str = DEFAULT_TIMESTAMP_URL) -> bool:
    """Sign an executable using a PFX certificate file."""
    if not os.path.exists(pfx_path):
        print(f"[SignTool] Error: PFX file not found at: {pfx_path}")
        return False

    print(f"[SignTool] Signing {target_path.name} with PFX certificate...")
    # Use PowerShell to safely load PFX in memory without writing passwords to disk
    ps_script = f"""
$pfxPath = '{pfx_path}'
$password = $env:LIHA_SIGN_PFX_PASSWORD
$secPassword = ConvertTo-SecureString $password -AsPlainText -Force
$cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($pfxPath, $secPassword)
$sig = Set-AuthenticodeSignature -FilePath '{target_path}' -Certificate $cert -HashAlgorithm SHA256 -TimestampServer '{timestamp_url}'
Write-Output $sig.Status
"""
    env = os.environ.copy()
    env["LIHA_SIGN_PFX_PASSWORD"] = password
    res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], env=env, capture_output=True, text=True)
    out = res.stdout.strip()
    if "Valid" in out:
        print(f"[SignTool] Successfully signed {target_path.name} with production certificate.")
        return True
    else:
        print(f"[SignTool] Signing result: {out}\n{res.stderr}")
        return False

def sign_with_thumbprint(target_path: Path, thumbprint: str, timestamp_url: str = DEFAULT_TIMESTAMP_URL) -> bool:
    """Sign an executable using a certificate installed in the Windows Certificate Store."""
    print(f"[SignTool] Signing {target_path.name} with certificate thumbprint: {thumbprint}...")
    ps_script = f"""
$thumb = '{thumbprint}'.Trim()
$cert = Get-ChildItem Cert:\\CurrentUser\\My, Cert:\\LocalMachine\\My | Where-Object {{ $_.Thumbprint -eq $thumb }} | Select-Object -First 1
if (-not $cert) {{
    Write-Error "Certificate with thumbprint $thumb not found in Certificate Store."
    exit 1
}}
$sig = Set-AuthenticodeSignature -FilePath '{target_path}' -Certificate $cert -HashAlgorithm SHA256 -TimestampServer '{timestamp_url}'
Write-Output $sig.Status
"""
    res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True)
    out = res.stdout.strip()
    if "Valid" in out:
        print(f"[SignTool] Successfully signed {target_path.name} with store certificate.")
        return True
    else:
        print(f"[SignTool] Signing result: {out}\n{res.stderr}")
        return False

def ensure_dev_certificate() -> str:
    """
    Generate and trust a local self-signed code signing certificate in CurrentUser store.
    Returns the certificate thumbprint.
    """
    print("[SignTool] Checking for existing Liha Assistant Development certificate...")
    find_cmd = """
$cert = Get-ChildItem Cert:\\CurrentUser\\My -CodeSigningCert | Where-Object { $_.Subject -like '*Liha Assistant Development*' } | Select-Object -First 1
if ($cert) { Write-Output $cert.Thumbprint }
"""
    res = subprocess.run(["powershell", "-NoProfile", "-Command", find_cmd], capture_output=True, text=True)
    existing = res.stdout.strip()
    if existing and len(existing) >= 32:
        print(f"[SignTool] Reusing existing development certificate: {existing}")
        return existing

    print("[SignTool] Generating new trusted local code-signing certificate for Liha Assistant...")
    create_cmd = """
$cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject "CN=Liha Assistant Development, O=Liha AI, C=US" -CertStoreLocation "Cert:\\CurrentUser\\My" -NotAfter (Get-Date).AddYears(5)
$tmpCer = Join-Path $env:TEMP "LihaDevCert.cer"
Export-Certificate -Cert $cert -FilePath $tmpCer | Out-Null
Import-Certificate -FilePath $tmpCer -CertStoreLocation "Cert:\\CurrentUser\\Root" | Out-Null
Import-Certificate -FilePath $tmpCer -CertStoreLocation "Cert:\\CurrentUser\\TrustedPublisher" | Out-Null
Remove-Item $tmpCer -ErrorAction SilentlyContinue
Write-Output $cert.Thumbprint
"""
    res = subprocess.run(["powershell", "-NoProfile", "-Command", create_cmd], capture_output=True, text=True)
    thumb = res.stdout.strip()
    if thumb and len(thumb) >= 32:
        print(f"[SignTool] Successfully created and trusted development certificate: {thumb}")
        return thumb
    else:
        print(f"[SignTool] Failed to create certificate: {res.stderr}")
        return ""

def sign_file(target_path: Path, allow_dev: bool = True) -> bool:
    """Automatically choose the appropriate signing method based on environment."""
    if not target_path.exists():
        print(f"[SignTool] Error: Target file not found: {target_path}")
        return False

    pfx_path = os.environ.get("LIHA_SIGN_PFX_PATH")
    pfx_pass = os.environ.get("LIHA_SIGN_PFX_PASSWORD")
    thumbprint = os.environ.get("LIHA_SIGN_CERT_THUMBPRINT")

    if pfx_path and pfx_pass:
        return sign_with_pfx(target_path, pfx_path, pfx_pass)
    elif thumbprint:
        return sign_with_thumbprint(target_path, thumbprint)
    elif allow_dev:
        thumb = ensure_dev_certificate()
        if thumb:
            # Local dev cert cannot be timestamped with an external public CA, so sign without timestamp server
            ps_script = f"""
$thumb = '{thumb}'
$cert = Get-ChildItem Cert:\\CurrentUser\\My | Where-Object {{ $_.Thumbprint -eq $thumb }} | Select-Object -First 1
$sig = Set-AuthenticodeSignature -FilePath '{target_path}' -Certificate $cert -HashAlgorithm SHA256
Write-Output $sig.Status
"""
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True)
            out = res.stdout.strip()
            if "Valid" in out:
                print(f"[SignTool] Successfully signed {target_path.name} with trusted local development certificate.")
                return True
            else:
                print(f"[SignTool] Signing output: {out}\n{res.stderr}")
                return False
    else:
        print("[SignTool] No signing credentials provided (LIHA_SIGN_PFX_PATH or LIHA_SIGN_CERT_THUMBPRINT) and dev signing is disabled.")
        return False

def main():
    parser = argparse.ArgumentParser(description="Liha Assistant Windows Code Signing Utility")
    parser.add_argument("file", help="Path to executable or DLL to sign")
    parser.add_argument("--dev", action="store_true", default=True, help="Use or generate a trusted local development certificate if no production certificate is supplied")
    parser.add_argument("--verify", action="store_true", help="Verify signature only")
    args = parser.parse_args()

    target = Path(args.file).resolve()
    if args.verify:
        is_valid = verify_signature(target)
        sys.exit(0 if is_valid else 1)

    ok = sign_file(target, allow_dev=args.dev)
    if ok:
        verify_signature(target)
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
