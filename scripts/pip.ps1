# Custom pip wrapper script for Django project
# This overrides pip install to update requirements.txt

param (
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Arguments
)

# Check if the command is "install"
if ($Arguments.Length -gt 0 -and $Arguments[0] -eq "install") {
    # Store the package arguments (everything after "install")
    $packageArgs = $Arguments[1..$Arguments.Length]
    
    Write-Host "Installing packages: $packageArgs" -ForegroundColor Cyan
    
    # Run the actual pip install command
    python -m pip install $packageArgs
    
    # Only update requirements.txt if the installation was successful
    if ($LASTEXITCODE -eq 0) {
        foreach ($pkg in $packageArgs) {
            # Extract package name (removing version specifiers or extras)
            if ($pkg -match "^([a-zA-Z0-9\-_.]+)") {
                $pkgName = $Matches[1]
                
                Write-Host "Processing package: $pkgName" -ForegroundColor Cyan
                
                # Get the installed version
                $versionInfo = python -m pip show $pkgName | Select-String "Version:"
                
                if ($versionInfo) {
                    $version = ($versionInfo -split "Version:")[1].Trim()
                    $line = "${pkgName}==${version}"
                    
                    Write-Host "Package version: $version" -ForegroundColor Cyan
                    
                    # Check if requirements.txt exists
                    # $requirementsPath = Join-Path $PSScriptRoot ".." "requirements.txt"
                    # Combine to get the full path to requirements.txt (one level up from script folder)
                    $requirementsPath = Join-Path -Path (Join-Path -Path $PSScriptRoot -ChildPath "..") -ChildPath "requirements.txt"

                    if (Test-Path $requirementsPath) {
                        $requirementsContent = Get-Content $requirementsPath
                        $updatedContent = @()
                        $packageFound = $false
                        
                        # Check line by line and update if package exists
                        foreach ($contentLine in $requirementsContent) {
                            if ($contentLine -match "^$pkgName==") {
                                $updatedContent += $line
                                $packageFound = $true
                                Write-Host "✅ Updated $pkgName to version $version in requirements.txt" -ForegroundColor Green
                            } else {
                                $updatedContent += $contentLine
                            }
                        }
                        
                        # If package wasn't found in the file, add it
                        if (-not $packageFound) {
                            $updatedContent += $line
                            Write-Host "✅ Added $line to requirements.txt" -ForegroundColor Green
                        }
                        
                        # Write the updated content back to file
                        $updatedContent | Set-Content $requirementsPath -Force
                    } else {
                        # Create requirements.txt if it doesn't exist
                        $line | Set-Content $requirementsPath -Force
                        Write-Host "✅ Created requirements.txt with $line" -ForegroundColor Green
                    }
                } else {
                    Write-Host "⚠️ Could not determine version for $pkgName" -ForegroundColor Yellow
                }
            } else {
                Write-Host "⚠️ Could not parse package name from $pkg" -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host "❌ Package installation failed. No changes made to requirements.txt." -ForegroundColor Red
    }
} else {
    # For non-install commands, just pass through to pip
    python -m pip $Arguments
}
