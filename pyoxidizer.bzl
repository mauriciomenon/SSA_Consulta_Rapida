# PyOxidizer configuration for SSA_Consulta_Rapida.
# Keep paths without ".." because Tugger rejects parent traversal.

PROJECT_ROOT = VARS.get("SSA_PROJECT_ROOT") or "."
PROJECT_ROOT = PROJECT_ROOT.replace("\\", "/")
PROJECT_PREFIX = PROJECT_ROOT + "/" if not PROJECT_ROOT.endswith("/") else PROJECT_ROOT


def make_exe():
    dist = default_python_distribution()

    policy = dist.make_python_packaging_policy()
    policy.resources_location = "filesystem-relative:lib"
    policy.resources_location_fallback = "filesystem-relative:lib"
    policy.include_test = False
    policy.file_scanner_emit_files = True
    policy.file_scanner_classify_files = True
    policy.include_distribution_resources = True
    policy.include_non_distribution_sources = True
    policy.extension_module_filter = "all"
    policy.include_classified_resources = True

    python_config = dist.make_python_interpreter_config()
    python_config.run_module = "main"
    python_config.module_search_paths = [
        "$ORIGIN",
        "$ORIGIN/lib",
        "$ORIGIN/lib/python3.10",
    ]
    python_config.oxidized_importer = False
    python_config.filesystem_importer = True
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
    return exe


def make_embedded_resources(exe):
    return exe.to_embedded_resources()


def make_install(exe):
    files = FileManifest()
    files.add_python_resource(".", exe)

    files.add_manifest(
        glob(
            include=[
                "main.py",
                "core/*.py",
                "core/**/*.py",
                "gui/*.py",
                "gui/**/*.py",
                "armazenamento/*.py",
                "armazenamento/**/*.py",
                "extracao/*.py",
                "extracao/**/*.py",
                "utils/*.py",
                "utils/**/*.py",
                "interface/*.py",
                "interface/**/*.py",
                "exportacao/*.py",
                "exportacao/**/*.py",
                "shared/*.py",
                "shared/**/*.py",
                "launchers/*.py",
                "launchers/**/*.py",
                "config/**",
                "themes/**",
                "resources/**",
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
