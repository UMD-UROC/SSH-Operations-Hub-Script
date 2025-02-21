#!/bin/bash

# SSH Operations Hub Installer
#
# INSTALLATION PROCESS:
# 1. Verifies sudo privileges
# 2. Creates secure directory structure:
#    - /usr/local/bin (system binaries)
#    - ~/.config/ssh-operations-hub (user config)
# 3. Sets up proper file permissions:
#    - Executable: 755 for main script
#    - Config dir: 700 for user access only
#    - Config files: 600 for secure reading
# 4. Creates system-wide symlink for global access
#
# For complete documentation:
# https://cdenihan.gitbook.io/ssh-operations-hub-script-docs

# This script installs the SSH Operations Hub tool and sets up the necessary
# directory structure and permissions for secure operation.
set -e

# Verify sudo access first
if ! sudo -v; then
    echo "Error: This script requires sudo privileges"
    exit 1
fi

# Define installation paths
# INSTALL_DIR: System-wide installation directory requiring sudo access
# CONFIG_DIR: User-specific configuration directory in their home folder
# SCRIPT_NAME: The name of the executable command
# SCRIPT_SOURCE: The source script to be installed
INSTALL_DIR="/usr/local/bin"
CONFIG_DIR="$HOME/.config/ssh-operations-hub"
SCRIPT_NAME="ssh-operations-hub"
SCRIPT_SOURCE="$(dirname "$0")/ssh-operations-hub.bash"

# Verify source script exists
if [ ! -f "$SCRIPT_SOURCE" ]; then
    echo "Error: Source script not found at $SCRIPT_SOURCE"
    exit 1
fi

# Create necessary directories
sudo mkdir -p "$INSTALL_DIR" || { echo "Error creating $INSTALL_DIR"; exit 1; }
mkdir -p "$CONFIG_DIR" || { echo "Error creating $CONFIG_DIR"; exit 1; }

# Backup existing files
if [ -f "$INSTALL_DIR/$SCRIPT_NAME" ]; then
    sudo mv "$INSTALL_DIR/$SCRIPT_NAME" "$INSTALL_DIR/$SCRIPT_NAME.backup"
fi

# Copy main script to installation directory
sudo cp "$SCRIPT_SOURCE" "$INSTALL_DIR/$SCRIPT_NAME" || { echo "Error copying script"; exit 1; }
sudo chmod +x "$INSTALL_DIR/$SCRIPT_NAME" || { echo "Error setting permissions"; exit 1; }

# Copy configuration files if they exist
CONFIG_SOURCE="$(dirname "$0")/../config"
if [ -d "$CONFIG_SOURCE" ]; then
    cp -r "$CONFIG_SOURCE/"* "$CONFIG_DIR/" || { echo "Error copying config files"; exit 1; }
fi

# Set appropriate permissions for user config
chmod 700 "$CONFIG_DIR"
find "$CONFIG_DIR" -type f -exec chmod 600 {} \;

# Create system-wide symlink for easier access
if ! sudo ln -sf "$INSTALL_DIR/$SCRIPT_NAME" "/usr/bin/$SCRIPT_NAME"; then
    echo "Warning: Failed to create symlink in /usr/bin"
fi

echo "Installation completed successfully!"
echo "The SSH Operations Hub is now available as '$SCRIPT_NAME'"