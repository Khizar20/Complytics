# PowerShell script to install Poppler on Windows
# This script downloads and sets up Poppler binaries for PDF OCR support

Write-Host "Installing Poppler for Windows..." -ForegroundColor Green

# Check if poppler is already installed
$popplerPath = "C:\poppler"
$popplerBinPath = "$popplerPath\Library\bin"

if (Test-Path "$popplerBinPath\pdftoppm.exe") {
    Write-Host "Poppler is already installed at $popplerBinPath" -ForegroundColor Yellow
    Write-Host "Checking if it's in PATH..." -ForegroundColor Yellow
    
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($currentPath -notlike "*$popplerBinPath*") {
        Write-Host "Adding Poppler to PATH..." -ForegroundColor Yellow
        [Environment]::SetEnvironmentVariable("Path", "$currentPath;$popplerBinPath", "User")
        Write-Host "Poppler added to PATH. Please restart your terminal." -ForegroundColor Green
    } else {
        Write-Host "Poppler is already in PATH." -ForegroundColor Green
    }
    exit 0
}

# Create poppler directory
if (-not (Test-Path $popplerPath)) {
    New-Item -ItemType Directory -Path $popplerPath -Force | Out-Null
}

# Download URL for latest Poppler release
$downloadUrl = "https://github.com/oschwartz10612/poppler-windows/releases/download/v23.11.0-0/Release-23.11.0-0.zip"
$zipPath = "$env:TEMP\poppler-windows.zip"

Write-Host "Downloading Poppler from GitHub..." -ForegroundColor Yellow
Write-Host "URL: $downloadUrl" -ForegroundColor Gray

try {
    # Download the zip file
    Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath -UseBasicParsing
    Write-Host "Download complete." -ForegroundColor Green
    
    Write-Host "Extracting Poppler..." -ForegroundColor Yellow
    # Extract to temp location first
    $tempExtractPath = "$env:TEMP\poppler-extract"
    if (Test-Path $tempExtractPath) {
        Remove-Item $tempExtractPath -Recurse -Force
    }
    Expand-Archive -Path $zipPath -DestinationPath $tempExtractPath -Force
    
    # Find the extracted folder (usually has a version name)
    $extractedFolder = Get-ChildItem $tempExtractPath -Directory | Select-Object -First 1
    
    if ($extractedFolder) {
        # Move contents to C:\poppler
        Write-Host "Installing to $popplerPath..." -ForegroundColor Yellow
        Copy-Item -Path "$($extractedFolder.FullName)\*" -Destination $popplerPath -Recurse -Force
        
        # Clean up
        Remove-Item $tempExtractPath -Recurse -Force
        Remove-Item $zipPath -Force
        
        Write-Host "Poppler extracted successfully." -ForegroundColor Green
    } else {
        throw "Could not find extracted folder"
    }
    
    # Add to PATH
    Write-Host "Adding Poppler to PATH..." -ForegroundColor Yellow
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    
    if ($currentPath -notlike "*$popplerBinPath*") {
        [Environment]::SetEnvironmentVariable("Path", "$currentPath;$popplerBinPath", "User")
        Write-Host "Poppler added to PATH." -ForegroundColor Green
    } else {
        Write-Host "Poppler is already in PATH." -ForegroundColor Yellow
    }
    
    # Verify installation
    if (Test-Path "$popplerBinPath\pdftoppm.exe") {
        Write-Host "`nPoppler installed successfully!" -ForegroundColor Green
        Write-Host "Location: $popplerBinPath" -ForegroundColor Gray
        Write-Host "`nIMPORTANT: Please restart your terminal/PowerShell for PATH changes to take effect." -ForegroundColor Yellow
        Write-Host "After restarting, test with: pdftoppm -h" -ForegroundColor Gray
    } else {
        Write-Host "Warning: Poppler binaries not found at expected location." -ForegroundColor Red
        Write-Host "Please check the installation manually." -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "Error installing Poppler: $_" -ForegroundColor Red
    Write-Host "`nManual installation steps:" -ForegroundColor Yellow
    Write-Host "1. Download from: https://github.com/oschwartz10612/poppler-windows/releases" -ForegroundColor Gray
    Write-Host "2. Extract to C:\poppler" -ForegroundColor Gray
    Write-Host "3. Add C:\poppler\Library\bin to your PATH environment variable" -ForegroundColor Gray
    exit 1
}


