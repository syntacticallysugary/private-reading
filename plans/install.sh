#!/bin/bash
#
# Private Reading Installation Script
# =============================
#
# This script installs Private Reading for system-level operation as a systemd service.
# It creates the necessary directory structure, sets up the virtual environment,
# installs dependencies, and configures the systemd service.
#
# Usage: sudo ./install.sh
#
# Prerequisites:
#   - Root or sudo privileges
#   - Python 3.8 or higher
#   - pip (Python package manager)
#   - systemd
#
# Exit Codes:
#   0  - Success
#   1  - Error (general)
#   2  - Directory already exists and is not empty
#   3  - Virtual environment creation failed
#   4  - Dependency installation failed
#   5  - Systemd service installation failed
#   6  - Service enablement failed
#   7  - Service start failed
#

set -e  # Exit on any error

# Configuration
INSTALL_DIR="/opt/private-reading"
VENV_DIR="${INSTALL_DIR}/venv"
PYTHON_VERSION="3.11"
SERVICE_NAME="private-reading.service"
INPUT_DIR="${INSTALL_DIR}/input"
OUTPUT_DIR="${INSTALL_DIR}/output"
PROCESSED_DIR="${INSTALL_DIR}/processed"
CONFIG_DIR="${INSTALL_DIR}/config"
LOGS_DIR="${INSTALL_DIR}/logs"

# Colors for output (if terminal supports it)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)."
        log_error "Please run: sudo ${BASH_SOURCE}"
        exit 1
    fi
}

# Check if directory already exists and is not empty
check_existing_installation() {
    if [[ -d "${INSTALL_DIR}" ]]; then
        if [[ -n "$(ls -A "${INSTALL_DIR}" 2>/dev/null)" ]]; then
            log_error "Installation directory already exists and is not empty: ${INSTALL_DIR}"
            log_error "Please remove the directory manually or choose a different path."
            exit 2
        else
            log_info "Installation directory exists but is empty. Proceeding..."
        fi
    fi
}

# Create directory structure
create_directories() {
    log_info "Creating directory structure..."

    mkdir -p "${INPUT_DIR}"
    mkdir -p "${OUTPUT_DIR}"
    mkdir -p "${PROCESSED_DIR}"
    mkdir -p "${CONFIG_DIR}"
    mkdir -p "${LOGS_DIR}"

    log_info "Directories created successfully."
}

# Create virtual environment
create_venv() {
    log_info "Setting up Python virtual environment at ${VENV_DIR}..."

    # Check if Python version is available
    python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" || {
        log_error "Python 3.8+ is required. Current version: $(python3 --version 2>/dev/null || echo 'unknown')"
        exit 1
    }

    # Create venv if it doesn't exist or is invalid
    if [[ ! -d "${VENV_DIR}/bin/activate" ]]; then
        python3 -m venv "${VENV_DIR}"
        log_info "Virtual environment created."
    else
        log_info "Virtual environment already exists."
    fi

    # Upgrade pip and install dependencies
    log_info "Installing dependencies from requirements.txt..."
    source "${VENV_DIR}/bin/activate"
    pip install --upgrade pip --quiet
    pip install -r "${INSTALL_DIR}/requirements.txt" --quiet
    log_info "Dependencies installed successfully."
}

# Copy systemd service files
copy_systemd_files() {
    log_info "Copying systemd service files to /etc/systemd/system/..."

    local service_file="${INSTALL_DIR}/plans/systemd/private-reading.service"
    local path_file="${INSTALL_DIR}/plans/systemd/private-reading-input.path"

    if [[ -f "${service_file}" ]]; then
        cp "${service_file}" /etc/systemd/system/${SERVICE_NAME}
        log_info "Service file copied: ${SERVICE_NAME}"
    else
        log_error "Service file not found: ${service_file}"
        exit 5
    fi

    if [[ -f "${path_file}" ]]; then
        cp "${path_file}" /etc/systemd/system/private-reading-input.path
        log_info "Socket file copied: private-reading-input.path"
    else
        log_warn "Socket file not found: ${path_file} (optional)"
    fi

    log_info "Systemd files copied successfully."
}

# Reload systemd daemon
reload_systemd() {
    log_info "Reloading systemd daemon..."
    systemctl daemon-reload
}

# Enable the service
enable_service() {
    log_info "Enabling Private Reading service..."
    systemctl enable "${SERVICE_NAME}" || {
        log_error "Failed to enable service."
        exit 6
    }
    log_info "Service enabled."
}

# Start the service
start_service() {
    log_info "Starting Private Reading service..."
    systemctl start "${SERVICE_NAME}" || {
        log_error "Failed to start service. Check logs: journalctl -u ${SERVICE_NAME}"
        exit 7
    }
    log_info "Service started successfully."
}

# Display status
show_status() {
    echo ""
    echo "========================================"
    echo "       Private Reading Installation Summary"
    echo "========================================"
    echo ""
    echo "Installation Directory: ${INSTALL_DIR}"
    echo "Virtual Environment:    ${VENV_DIR}"
    echo "Service:                ${SERVICE_NAME}"
    echo ""
    echo "Directories:"
    echo "  - Input:      ${INPUT_DIR}"
    echo "  - Output:     ${OUTPUT_DIR}"
    echo "  - Processed:  ${PROCESSED_DIR}"
    echo "  - Config:     ${CONFIG_DIR}"
    echo "  - Logs:       ${LOGS_DIR}"
    echo ""
    echo "To view service status:"
    echo "  systemctl status ${SERVICE_NAME}"
    echo ""
    echo "To view service logs:"
    echo "  journalctl -u ${SERVICE_NAME} -f"
    echo ""
    echo "========================================"
}

# Main installation function
main() {
    log_info "Starting Private Reading installation..."
    echo ""

    # Check for root privileges
    check_root

    # Check for existing installation
    check_existing_installation

    # Create directories
    create_directories

    # Create/set up virtual environment
    create_venv

    # Copy systemd files
    copy_systemd_files

    # Reload systemd
    reload_systemd

    # Enable and start service
    enable_service
    start_service

    # Show summary
    show_status

    log_info "Installation completed successfully!"
}

# Run main function
main "$@"
