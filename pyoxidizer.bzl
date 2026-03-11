# PyOxidizer configuration for SSA_Consulta_Rapida (repo root path).

PROJECT_ROOT = VARS.get("SSA_PROJECT_ROOT")
PROJECT_ROOT = PROJECT_ROOT.replace("\\", "/")
PROJECT_PREFIX = PROJECT_ROOT + "/"


def _abs(pattern):
    return PROJECT_PREFIX + pattern

def make_exe():
    dist = default_python_distribution()

    policy = dist.make_python_packaging_policy()
    policy.resources_location = "filesystem-relative:lib"
    policy.resources_location_fallback = "filesystem-relative:lib"
    policy.include_test = False
    policy.file_scanner_emit_files = True
    policy.file_scanner_classify_files = True
    policy.include_distribution_resources = True
    policy.include_non_distribution_sources = False
    policy.extension_module_filter = "all"
    policy.include_classified_resources = True

    python_config = dist.make_python_interpreter_config()
    python_config.run_module = "main"
    python_config.filesystem_importer = True
    python_config.sys_frozen = False
    python_config.sys_meipass = False

    exe = dist.to_python_executable(
        name="SSA_Consulta_Rapida",
        packaging_policy=policy,
        config=python_config,
    )

    exe.add_python_resources(exe.pip_install(["pandas", "openpyxl", "PyQt6"]))
    return exe


def make_embedded_resources(exe):
    return exe.to_embedded_resources()


def make_install(exe):
    files = FileManifest()

    files.add_python_resource(".", exe)

    files.add_manifest(glob([_abs("config/**")], strip_prefix=PROJECT_PREFIX))
    files.add_manifest(glob([_abs("themes/**")], strip_prefix=PROJECT_PREFIX))
    files.add_manifest(glob([_abs("resources/**")], strip_prefix=PROJECT_PREFIX))
    files.add_manifest(
        glob(
            [
                _abs("main.py"),
                _abs("core/**"),
                _abs("gui/**"),
                _abs("armazenamento/**"),
                _abs("extracao/**"),
                _abs("utils/**"),
                _abs("interface/**"),
                _abs("exportacao/**"),
                _abs("shared/**"),
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
