# This script is a wrapper for pip install that updates requirements.txt
# with the installed package versions. It checks if the package is already
# listed in requirements.txt and updates the version if necessary.
# It also handles the case where pip install fails, ensuring that
# requirements.txt is not modified in that case.
# This script is a wrapper for pip install that updates requirements.txt
#!/bin/bash

# Only proceed if the first argument is "install"
if [[ "$1" == "install" ]]; then
    shift  # Remove the "install" from arguments

    # Install packages
    pip install "$@"

    # If pip install was successful, update requirements.txt
    if [[ $? -eq 0 ]]; then
        for pkg in "$@"; do
            pkg_name=$(echo "$pkg" | cut -d'=' -f1 | cut -d'[' -f1)
            version=$(pip show "$pkg_name" 2>/dev/null | grep Version | awk '{print $2}')
            line="${pkg_name}==${version}"

            # Check if the package is already in requirements.txt
            if grep -q "^$pkg_name==" requirements.txt; then
                # Replace the old version with the new one using a temporary file
                awk -v pkg="$pkg_name" -v line="$line" '{if ($1 ~ "^" pkg"==") print line; else print $0}' requirements.txt > temp.txt && mv temp.txt requirements.txt
                echo "✅ Updated $pkg_name to $line in requirements.txt"
            else
                # If it doesn't exist, add it
                echo "$line" >> requirements.txt
                echo "✅ Added $line to requirements.txt"
            fi
        done
    else
        echo "❌ Package installation failed. No changes made to requirements.txt."
    fi
else
    # Fallback to regular pip
    pip "$@"
fi
