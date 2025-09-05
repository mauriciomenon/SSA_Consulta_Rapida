#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess

# Build configurado para Windows; gera executaveis CLI e GUI (onefile)

APP_NAME = "SSA_Consulta_Rapida"
APP_VERSION = "3.10"
ROOT = os.path.abspath(os.path.dirname(__file__))
DIST_DIR = os.path.join(ROOT, "dist")
BUILD_DIR = os.path.join(ROOT, "build")
ICON_PATH = os.path.join(ROOT, "resources", "app_icon.ico")


def run(cmd: list[str]):
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def ensure_dirs():
    os.makedirs(DIST_DIR, exist_ok=True)
    os.makedirs(BUILD_DIR, exist_ok=True)


def build_target(entry: str, name: str, windowed: bool, onefile: bool):
    ensure_dirs()
    pyinstaller = [sys.executable, "-m", "PyInstaller", "--clean"]
    if onefile:
        pyinstaller += ["--onefile"]
    else:
        pyinstaller += ["--onedir"]
    if windowed:
        pyinstaller += ["--windowed"]
    pyinstaller += [
        f"--name={name}",
        f"--icon={ICON_PATH}" if os.path.exists(ICON_PATH) else "",
        "--add-data", f"config{os.pathsep}config",
        "--add-data", f"resources{os.pathsep}resources",
        entry,
    ]
    pyinstaller = [p for p in pyinstaller if p]
    run(pyinstaller)


def write_temp_gui_entry(tmp_path: str):
    code = (
        "import sys\n"
        "import os\n"
        "sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))\n"
        "from main import main as _main\n"
        "if __name__ == '__main__':\n"
        "    raise SystemExit(_main(['--gui']))\n"
    )
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(code)


def package_zip():
    pkg_name = f"{APP_NAME}_v{APP_VERSION}"
    pkg_root = os.path.join(DIST_DIR, pkg_name)
    if os.path.exists(pkg_root):
        shutil.rmtree(pkg_root)
    os.makedirs(pkg_root, exist_ok=True)
    for exe in [
        f"{APP_NAME}_CLI.exe",
        f"{APP_NAME}_GUI.exe",
    ]:
        src = os.path.join(DIST_DIR, exe)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(pkg_root, exe))
    # Documentacao basica
    for path in ("README.md", "INSTRUCOES_LEITURA.md"):
        p = os.path.join(ROOT, path)
        if os.path.exists(p):
            shutil.copy(p, os.path.join(pkg_root, os.path.basename(p)))
    shutil.make_archive(os.path.join(DIST_DIR, pkg_name), "zip", DIST_DIR, pkg_name)


def main():
    cli_name = f"{APP_NAME}_CLI"
    gui_name = f"{APP_NAME}_GUI"

    # CLI (onefile)
    build_target(entry=os.path.join(ROOT, "main.py"), name=cli_name, windowed=False, onefile=True)

    # GUI (onefile) via entry temporario
    gui_entry = os.path.join(BUILD_DIR, "_entry_gui.py")
    write_temp_gui_entry(gui_entry)
    build_target(entry=gui_entry, name=gui_name, windowed=True, onefile=True)

    package_zip()


if __name__ == "__main__":
    main()
