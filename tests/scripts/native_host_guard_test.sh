#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
# shellcheck disable=SC1091
source "$repo_root/scripts/env/native_host_guard.sh"
ssa_native_guard_repo "$repo_root"
[[ "$TMPDIR" == /tmp && "$TMP" == /tmp && "$TEMP" == /tmp ]] || {
  printf 'native guard did not isolate WSL temporary paths\n' >&2
  exit 1
}
ssa_native_guard_tools bash chmod grep ln mkdir mktemp rm stat uv

# shellcheck disable=SC1091
source "$repo_root/scripts/env/direnv_common.sh"
ssa_env::apply native-guard-test
venv_inode_before="$(stat -c %i "$repo_root/.venv")"
[[ "$UV_PYTHON" == "$SSA_ENV_PY_VERSION" ]] || {
  printf 'uv interpreter is not pinned to the harness version\n' >&2
  exit 1
}
[[ "$UV_PROJECT_ENVIRONMENT" == "$repo_root/.venv" ]] || {
  printf 'uv project environment is not pinned to the repository venv\n' >&2
  exit 1
}
uv run --locked python -c 'import sys; raise SystemExit(sys.version_info[:3] != (3, 13, 12))'
[[ "$(stat -c %i "$repo_root/.venv")" == "$venv_inode_before" ]] || {
  printf 'uv run replaced the repository venv\n' >&2
  exit 1
}

fixture_root="$(mktemp -d)"
trap 'rm -rf -- "$fixture_root"' EXIT

expect_blocked() {
  if "$@" >/dev/null 2>&1; then
    printf 'expected native guard rejection: %s\n' "$*" >&2
    exit 1
  fi
}

mkdir -p "$fixture_root/repo" "$fixture_root/fake-bin" "$fixture_root/windows-venv/Scripts"
expect_blocked ssa_native_guard_repo "$fixture_root/repo"

printf 'MZfake executable\n' > "$fixture_root/fake-bin/uv"
chmod +x "$fixture_root/fake-bin/uv"
PATH="$fixture_root/fake-bin:$PATH"
expect_blocked ssa_native_guard_tool uv

ln -s /mnt/c/Windows/System32/cmd.exe "$fixture_root/fake-bin/glab"
expect_blocked ssa_native_guard_tool glab
expect_blocked ssa_native_guard_path /mnt/c/Users/blocked-user/output "$repo_root"

printf '#!/mnt/c/Windows/System32/cmd.exe\n' > "$fixture_root/fake-bin/pytest"
chmod +x "$fixture_root/fake-bin/pytest"
expect_blocked ssa_native_guard_tool pytest

printf 'home = C:\\Users\\blocked-user\\AppData\\Local\\Programs\\Python\n' > "$fixture_root/windows-venv/pyvenv.cfg"
printf 'MZ' > "$fixture_root/windows-venv/Scripts/python.exe"
expect_blocked ssa_native_guard_venv "$fixture_root/windows-venv"

if grep -q -- '--clear' "$repo_root/scripts/env/direnv_common.sh"; then
  printf 'direnv_common.sh still permits destructive uv --clear\n' >&2
  exit 1
fi
if grep -q 'SSA_ENV_REPO_ROOT:-' "$repo_root/scripts/env/direnv_common.sh"; then
  printf 'direnv_common.sh still permits a caller-controlled repository root\n' >&2
  exit 1
fi
if ! grep -Fq 'SSA_VENV_DIR_OVERRIDE must be a .venv name inside the repository' \
  "$repo_root/scripts/env/direnv_common.sh"; then
  printf 'direnv_common.sh does not constrain venv overrides to the repository\n' >&2
  exit 1
fi
# shellcheck disable=SC2016
if ! grep -Fq '$env:UV_PYTHON = $env:SSA_ENV_PY_VERSION' \
  "$repo_root/scripts/env/direnv_common.ps1"; then
  printf 'direnv_common.ps1 does not pin uv to the harness interpreter\n' >&2
  exit 1
fi
# shellcheck disable=SC2016
if grep -Eq 'ConvertTo-WslPath|/mnt/\$drive' "$repo_root/dev_env/build/release_local.ps1"; then
  printf 'release_local.ps1 still maps the Windows repository into WSL\n' >&2
  exit 1
fi
# shellcheck disable=SC2016
if ! grep -Fq 'printf %s "$HOME"' "$repo_root/dev_env/build/release_local.ps1"; then
  printf 'release_local.ps1 does not resolve the native WSL home\n' >&2
  exit 1
fi
if grep -Eiq '(mauri|menon)' \
  "$repo_root/AGENTS.md" \
  "$repo_root/scripts/env/native_host_guard.sh" \
  "$repo_root/scripts/env/native_host_guard.ps1" \
  "$repo_root/dev_env/build/release_local.ps1"; then
  printf 'native harness contains a personal user path\n' >&2
  exit 1
fi
if ! grep -Fq '[native-guard] BLOCKED' "$repo_root/scripts/env/activate_powershell.sh"; then
  printf 'activate_powershell.sh still emulates a Windows environment in Bash\n' >&2
  exit 1
fi

guarded_entrypoints=(
  dev_env/bootstrap.sh
  dev_env/build/build_nuitka_debian.sh
  dev_env/build/build_nuitka_debian_arm64.sh
  dev_env/build/build_pyinstaller_debian.sh
  dev_env/build/build_pyinstaller_debian_arm64.sh
  dev_env/build/build_pyoxidizer_debian.sh
  dev_env/build/build_pyoxidizer_debian_arm64.sh
  dev_env/build/package_debian_arm64_tar.sh
  dev_env/build/release_debian.sh
  dev_env/build/release_debian_arm64.sh
  release.sh
  scripts/ci_quality_gates.sh
  scripts/install_hooks.sh
  scripts/run_import_perf.sh
  scripts/run_perf_analysis.sh
  scripts/run_perf_no_direnv.sh
  scripts/run_tests.sh
  scripts/run_tests_loop.sh
  scripts/run_tests_unbuffered.sh
  scripts/security/scan_secrets.sh
)
for guarded_entrypoint in "${guarded_entrypoints[@]}"; do
  if ! grep -Fq 'native_host_guard.sh' "$repo_root/$guarded_entrypoint"; then
    printf 'entrypoint bypasses native host guard: %s\n' "$guarded_entrypoint" >&2
    exit 1
  fi
done

printf 'native host guard tests: OK\n'
