# PyOxidizer configuration for SSA_Consulta_Rapida.
# Keep paths without ".." because Tugger rejects parent traversal.

PROJECT_ROOT = VARS.get("SSA_PROJECT_ROOT") or "."
PROJECT_ROOT = PROJECT_ROOT.replace("\\", "/")
PROJECT_PREFIX = (
    ""
    if PROJECT_ROOT in ("", ".")
    else PROJECT_ROOT + "/"
    if not PROJECT_ROOT.endswith("/")
    else PROJECT_ROOT
)


def make_exe():
    dist = default_python_distribution()

    policy = dist.make_python_packaging_policy()
    policy.set_resource_handling_mode("classify")
    policy.resources_location = "in-memory"
    policy.resources_location_fallback = "filesystem-relative:lib"
    policy.include_test = False
    policy.file_scanner_emit_files = False
    policy.file_scanner_classify_files = True
    policy.include_distribution_sources = False
    policy.include_distribution_resources = True
    policy.include_non_distribution_sources = False
    policy.bytecode_optimize_level_zero = True
    policy.extension_module_filter = "all"
    policy.include_classified_resources = True

    python_config = dist.make_python_interpreter_config()
    python_config.run_module = "main"
    python_config.module_search_paths = [
        "$ORIGIN",
        "$ORIGIN/lib",
        "$ORIGIN/lib/python3.10",
    ]
    python_config.oxidized_importer = True
    python_config.filesystem_importer = False
    python_config.sys_frozen = False
    python_config.sys_meipass = False

    exe = dist.to_python_executable(
        name="SSA_Consulta_Rapida",
        packaging_policy=policy,
        config=python_config,
    )

    exe.add_python_resources(
        exe.pip_install(["pandas", "openpyxl", "PyQt6", "numpy", "tabulate"])
    )
    exe.add_python_resources(
        exe.read_package_root(
            path=PROJECT_ROOT,
            packages=[
                "main",
                "armazenamento",
                "core",
                "exportacao",
                "extracao",
                "gui",
                "interface",
                "shared",
                "utils",
            ],
        )
    )
    return exe


def make_embedded_resources(exe):
    return exe.to_embedded_resources()


def make_install(exe):
    files = FileManifest()
    files.add_python_resource(".", exe)

    files.add_manifest(
        glob(
            include=[
                "config/*.json",
                "config/*.sql",
                "config/build_info.json",
                "docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md",
                "themes/**",
                "resources/**",
            ],
            exclude=[
                "launchers/**/__pycache__/**",
                "launchers/dist/**",
                "launchers/logs/**",
                "launchers/platforms/**/temp/**",
                "launchers/platforms/**/venv/**",
            ],
            strip_prefix=PROJECT_PREFIX,
        )
    )
    return files


def make_msi(exe):
    return exe.to_wix_msi_builder(
        "SSA_Consulta_Rapida",
        "SSA Consulta Rapida",
        "1.0.0",
        "Your Company",
    )


register_target("exe", make_exe)
register_target("resources", make_embedded_resources, depends=["exe"])
register_target("install", make_install, depends=["exe"], default=True)
register_target("msi", make_msi, depends=["exe"])

resolve_targets()
