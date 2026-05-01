#!/usr/bin/env bash
set -Eeuo pipefail

export DEBIAN_PLATFORM="debian_arm64"
export DEBIAN_PACKAGE_ARCH="arm64"
export DEBIAN_MACHINE_REGEX='^(aarch64|arm64)$'
export DEBIAN_APPIMAGE_ARCH="aarch64"
export DEBIAN_ARCH_LABEL="arm64/aarch64"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
exec "${SCRIPT_DIR}/package_debian_deb.sh" "$@"
