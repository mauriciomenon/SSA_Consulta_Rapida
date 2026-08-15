#!/usr/bin/env bash
set -Eeuo pipefail

export DEBIAN_PLATFORM="debian_amd64"
export DEBIAN_PACKAGE_ARCH="amd64"
export DEBIAN_MACHINE_REGEX='^(x86_64|amd64)$'
export DEBIAN_APPIMAGE_ARCH="x86_64"
export DEBIAN_ARCH_LABEL="amd64/x86_64"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
exec "${SCRIPT_DIR}/package_debian_appimage.sh" "$@"
