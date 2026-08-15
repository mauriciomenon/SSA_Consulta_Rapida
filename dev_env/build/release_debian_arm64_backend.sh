#!/usr/bin/env bash

MANDATORY_RELEASE_FILES=(
  "config/build_info.json"
  "docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md"
)

mandatory_release_file_label() {
  basename -- "$1"
}

assert_mandatory_release_files_exist() {
  local payload_root="$1"
  local required_file
  for required_file in "${MANDATORY_RELEASE_FILES[@]}"; do
    [[ -f "${payload_root}/${required_file}" ]] || die "$(mandatory_release_file_label "${required_file}") ausente em ${payload_root}"
  done
}

assert_mandatory_release_files_listed() {
  local listing="$1"
  local context="$2"
  local required_file
  for required_file in "${MANDATORY_RELEASE_FILES[@]}"; do
    grep -F "$(mandatory_release_file_label "${required_file}")" <<<"${listing}" >/dev/null || die "$(mandatory_release_file_label "${required_file}") ausente em ${context}"
  done
}

validate_source_protection() {
  local root="$1"
  local artifact="$2"
  uv run --python 3.13 python "${root}/dev_env/build/release_platform_report.py" \
    source-protection \
    --repo-root "${root}" \
    --artifact "${artifact}"
}

validate_build_payload() {
  local root="$1"
  local backend="$2"
  local app_version="$3"
  local git_commit="$4"
  local build_root=""
  local bundle_root=""
  local bundle_roots=()

  case "${backend}" in
    pyinstaller)
      build_root="${root}/launchers/dist/${PLATFORM}"
      [[ -d "${build_root}" ]] || build_root="${root}/builds/pyinstaller/${PLATFORM}"
      bundle_roots=(
        "${build_root}/SSA_CLI_v${app_version}_${PLATFORM}"
        "${build_root}/SSA_GUI_v${app_version}_${PLATFORM}"
      )
      ;;
    nuitka)
      build_root="${root}/builds/nuitka/${PLATFORM}"
      bundle_roots=(
        "${build_root}/cli_entry.dist"
        "${build_root}/gui_entry.dist"
      )
      ;;
    pyoxidizer)
      build_root="${root}/builds/pyoxidizer/${PLATFORM}"
      bundle_roots=("${build_root}")
      ;;
    *)
      die "backend desconhecido: ${backend}"
      ;;
  esac

  [[ -d "${build_root}" ]] || die "artefato ${backend} nao encontrado: ${build_root}"

  for bundle_root in "${bundle_roots[@]}"; do
    local payload_root="${bundle_root}"
    if [[ -d "${bundle_root}/_internal" ]]; then
      payload_root="${bundle_root}/_internal"
    fi
    [[ -d "${bundle_root}" ]] || die "bundle ${backend} ausente: ${bundle_root}"
    assert_mandatory_release_files_exist "${payload_root}"

    uv run --python 3.13 python "${root}/dev_env/build/release_platform_report.py" \
      validate-build-info \
      --build-info "${payload_root}/config/build_info.json" \
      --backend "${backend}" \
      --platform "${PLATFORM}" \
      --app-version "${app_version}" \
      --git-commit "${git_commit}"
    validate_source_protection "${root}" "${bundle_root}"
  done
}

resolve_import_smoke_executable() {
  local root="$1"
  local backend="$2"
  local app_version="$3"
  local smoke_exe=""
  case "${backend}" in
    pyinstaller)
      smoke_exe="${root}/launchers/dist/${PLATFORM}/SSA_CLI_v${app_version}_${PLATFORM}/SSA_CLI_v${app_version}_${PLATFORM}"
      if [[ ! -x "${smoke_exe}" ]]; then
        smoke_exe="${root}/builds/pyinstaller/${PLATFORM}/SSA_CLI_v${app_version}_${PLATFORM}/SSA_CLI_v${app_version}_${PLATFORM}"
      fi
      ;;
    nuitka)
      smoke_exe="${root}/builds/nuitka/${PLATFORM}/cli_entry.dist/SSA_CLI_v${app_version}_${PLATFORM}"
      ;;
    pyoxidizer)
      smoke_exe="${root}/builds/pyoxidizer/${PLATFORM}/SSA_Consulta_Rapida"
      ;;
    *)
      die "backend sem executavel para smoke de importacao: ${backend}"
      ;;
  esac
  [[ -x "${smoke_exe}" ]] || die "executavel ausente para smoke ${backend}: ${smoke_exe}"
  printf '%s\n' "${smoke_exe}"
}

run_functional_import_smoke() {
  local root="$1"
  local backend="$2"
  local app_version="$3"
  local smoke_exe
  local smoke_json
  local smoke_err

  smoke_exe="$(resolve_import_smoke_executable "${root}" "${backend}" "${app_version}")"
  smoke_json="$(mktemp)"
  smoke_err="$(mktemp)"
  if ! uv run --python 3.13 python "${root}/scripts/smoke_cli.py" --executable "${smoke_exe}" --json >"${smoke_json}" 2>"${smoke_err}"; then
    local stdout_text=""
    local stderr_text=""
    [[ -f "${smoke_json}" ]] && stdout_text="$(cat -- "${smoke_json}")"
    [[ -f "${smoke_err}" ]] && stderr_text="$(cat -- "${smoke_err}")"
    rm -f -- "${smoke_json}" "${smoke_err}"
    die "smoke importacao falhou ${backend}. stdout=${stdout_text} stderr=${stderr_text}"
  fi
  rm -f -- "${smoke_json}" "${smoke_err}"
  log "smoke importacao ${backend}: funcional"
}

run_build_backend() {
  local root="$1"
  local backend="$2"
  local args=(--silent)
  if [[ "${WITH_LOCAL_DATA}" == "1" ]]; then
    args+=(--with-local-data)
  fi
  case "${backend}" in
    pyinstaller) bash "${root}/dev_env/build/build_pyinstaller_debian_arm64.sh" "${args[@]}" ;;
    nuitka) bash "${root}/dev_env/build/build_nuitka_debian_arm64.sh" "${args[@]}" ;;
    pyoxidizer) bash "${root}/dev_env/build/build_pyoxidizer_debian_arm64.sh" "${args[@]}" ;;
    *) die "backend desconhecido: ${backend}" ;;
  esac
}

is_supported_package_pair() {
  release_target_supported "$1" "$2"
}

run_package_backend() {
  local root="$1"
  local backend="$2"
  local package_kind="$3"
  if ! is_supported_package_pair "${backend}" "${package_kind}"; then
    die "$(release_target_reason "${backend}" "${package_kind}")"
  fi
  case "${package_kind}:${backend}" in
    deb:*)
      bash "${root}/dev_env/build/package_debian_arm64_deb.sh" --build-system "${backend}"
      ;;
    appimage:*)
      bash "${root}/dev_env/build/package_debian_arm64_appimage.sh" --build-system "${backend}"
      ;;
    tar:*)
      bash "${root}/dev_env/build/package_debian_arm64_tar.sh" --build-system "${backend}"
      ;;
    *)
      die "pacote invalido: ${package_kind}:${backend}"
      ;;
  esac
}

validate_tar_payload() {
  local package_file="$1"
  local package_contents
  [[ -f "${package_file}" ]] || die "pacote tar ausente: ${package_file}"
  validate_source_protection "${REPO_ROOT:?REPO_ROOT ausente}" "${package_file}"
  package_contents="$(tar -tzf "${package_file}")"
  assert_mandatory_release_files_listed "${package_contents}" "tar ${package_file}"
}

validate_package_payload() {
  local root="$1"
  local backend="$2"
  local package_kind="$3"
  local app_version="$4"
  local package_dir="${root}/builds/packages/${PLATFORM}"
  local package_contents=""
  local package_file=""
  case "${package_kind}:${backend}" in
    deb:*)
      package_file="${package_dir}/ssa-consulta-rapida-${backend}-${PACKAGE_ARCH}_${app_version}_${PACKAGE_ARCH}.deb"
      [[ -f "${package_file}" ]] || die "pacote .deb ausente: ${package_file}"
      package_contents="$(dpkg-deb -c "${package_file}")"
      assert_mandatory_release_files_listed "${package_contents}" ".deb ${backend}"
      ;;
    appimage:*)
      package_file="${package_dir}/SSA_Consulta_Rapida_v${app_version}_${PLATFORM}_${backend}.AppImage"
      [[ -x "${package_file}" ]] || die "AppImage ausente ou sem execucao: ${package_file}"
      ;;
    tar:pyinstaller)
      validate_tar_payload "${package_dir}/SSA_Consulta_Rapida_v${app_version}_${PLATFORM}_pyinstaller_cli.tar.gz"
      validate_tar_payload "${package_dir}/SSA_Consulta_Rapida_v${app_version}_${PLATFORM}_pyinstaller_gui.tar.gz"
      ;;
    tar:nuitka)
      validate_tar_payload "${package_dir}/SSA_Consulta_Rapida_v${app_version}_${PLATFORM}_nuitka_cli.tar.gz"
      validate_tar_payload "${package_dir}/SSA_Consulta_Rapida_v${app_version}_${PLATFORM}_nuitka_gui.tar.gz"
      ;;
    tar:pyoxidizer)
      validate_tar_payload "${package_dir}/SSA_Consulta_Rapida_v${app_version}_${PLATFORM}_pyoxidizer.tar.gz"
      ;;
  esac
}
