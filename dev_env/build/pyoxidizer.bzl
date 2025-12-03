# PyOxidizer configuration for SSA_Consulta_Rapida

def make_exe():
    dist = default_python_distribution()

    policy = dist.make_python_packaging_policy()
    # Allow loading resources from filesystem
    policy.resources_location = "filesystem-relative:lib"
    policy.resources_location_fallback = "filesystem-relative:lib"
    # Exclude test files that cause numpy to think it's in source directory
    policy.include_test = False
    policy.file_scanner_emit_files = True
    policy.file_scanner_classify_files = True
    policy.include_distribution_resources = True
    policy.include_non_distribution_sources = False
    # Include extension modules and shared libraries
    policy.extension_module_filter = "all"
    policy.include_classified_resources = True

    python_config = dist.make_python_interpreter_config()
    # Run main.py as script
    python_config.run_module = "main"
    python_config.filesystem_importer = True
    python_config.sys_frozen = False
    python_config.sys_meipass = False

    exe = dist.to_python_executable(
        name="SSA_Consulta_Rapida",
        packaging_policy=policy,
        config=python_config,
    )

    # Add all Python packages via pip_install
    # Using a more permissive policy should include .libs directories
    exe.add_python_resources(exe.pip_install(["pandas", "openpyxl", "PyQt6"]))

    # Add main.py explicitly as a module
    # Force project sources to filesystem as well
    for resource in exe.read_package_root(
        path=".",
        packages=["core", "gui", "armazenamento", "extracao", "utils", "interface", "exportacao", "shared", "main"],
    ):
        resource.add_location = "filesystem-relative:lib"
        exe.add_python_resource(resource)

    return exe

def make_embedded_resources(exe):
    return exe.to_embedded_resources()

def make_install(exe):
    files = FileManifest()

    # Add executable
    files.add_python_resource(".", exe)

    # Add external directories that need to stay accessible
    files.add_manifest(glob(
        include=["config/**"],
    ))

    files.add_manifest(glob(
        include=["themes/**"],
    ))

    # Note: docs_entrada/ and data/ directories will be created by the application at runtime if needed

    return files

# Register a target to install packages and capture .libs directories
def make_pip_install_simple(dist):
    """Alternative installer that uses a temporary venv to get all files including .libs"""
    return dist.pip_install(["pandas==2.3.3", "openpyxl==3.1.5", "PyQt6==6.10.0"])

def make_msi(exe):
    return exe.to_wix_msi_builder(
        "SSA_Consulta_Rapida",
        "SSA Consulta Rapida",
        "1.0.0",
        "Your Company"
    )

register_target("exe", make_exe)
register_target("resources", make_embedded_resources, depends=["exe"])
register_target("install", make_install, depends=["exe"], default=True)
register_target("msi", make_msi, depends=["exe"])

resolve_targets()
