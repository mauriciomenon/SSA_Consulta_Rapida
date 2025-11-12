# PyOxidizer configuration for SSA_Consulta_Rapida

def make_exe():
    dist = default_python_distribution()

    policy = dist.make_python_packaging_policy()
    # Allow loading resources from filesystem
    policy.resources_location = "filesystem-relative:lib"
    policy.resources_location_fallback = "filesystem-relative:lib"

    python_config = dist.make_python_interpreter_config()
    python_config.run_command = "import sys; sys.path.insert(0, '.'); from main import main; main()"
    python_config.filesystem_importer = True

    exe = dist.to_python_executable(
        name="SSA_Consulta_Rapida",
        packaging_policy=policy,
        config=python_config,
    )

    # Add all Python source files (will be compiled to bytecode)
    exe.add_python_resources(exe.pip_install([
        "pandas",
        "openpyxl",
        "PyQt6",
    ]))

    # Add project source files
    for pattern in [
        "main.py",
        "core/**/*.py",
        "gui/**/*.py",
        "armazenamento/**/*.py",
        "extracao/**/*.py",
        "utils/**/*.py",
        "interface/**/*.py",
        "exportacao/**/*.py",
        "shared/**/*.py",
    ]:
        exe.add_python_resources(exe.read_package_root(
            path=".",
            packages=[""],
        ))

    return exe

def make_embedded_resources(exe):
    return exe.to_embedded_resources()

def make_install(exe):
    files = FileManifest()

    # Add executable
    files.add_python_resource(".", exe)

    # Add external directories that need to stay accessible
    files.add_manifest(glob(
        include=["config/**/*.json"],
    ))

    files.add_manifest(glob(
        include=["themes/**/*.json"],
    ))

    # Create empty directories for runtime data
    files.add_manifest(glob(
        include=["docs_entrada/.gitkeep"],
    ))

    files.add_manifest(glob(
        include=["data/.gitkeep"],
    ))

    return files

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
