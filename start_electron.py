import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time

# Paths
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend-web")
DIST_DIR = os.path.join(FRONTEND_DIR, "dist")

# Child processes
processes = []
is_cleaning_up = False


def configure_windows_console_utf8():
    """Configure the current Windows console to use UTF-8 when possible."""
    if sys.platform != "win32":
        return

    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleCP(65001)
        kernel32.SetConsoleOutputCP(65001)
    except Exception:
        pass

    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"


def get_npm_executable() -> str:
    """Return the npm executable name for the current platform."""
    return "npm.cmd" if sys.platform == "win32" else "npm"


def get_node_executable() -> str:
    """Return the node executable name for the current platform."""
    return "node.exe" if sys.platform == "win32" else "node"


def get_local_bin(tool_name: str) -> str | None:
    """Return the local executable path for a tool if it exists."""
    bin_name = f"{tool_name}.cmd" if sys.platform == "win32" else tool_name
    tool_path = os.path.join(FRONTEND_DIR, "node_modules", ".bin", bin_name)
    return tool_path if os.path.exists(tool_path) else None


def get_electron_cli_entry() -> str | None:
    """Return the Electron CLI entry path if it exists."""
    cli_path = os.path.join(FRONTEND_DIR, "node_modules", "electron", "cli.js")
    return cli_path if os.path.exists(cli_path) else None


def get_vite_js_entry() -> str | None:
    """Return the Vite JS entry path if it exists."""
    vite_path = os.path.join(FRONTEND_DIR, "node_modules", "vite", "bin", "vite.js")
    return vite_path if os.path.exists(vite_path) else None


def has_local_electron() -> bool:
    """Return whether a platform-specific local Electron executable exists."""
    return get_local_bin("electron") is not None


def has_local_vite() -> bool:
    """Return whether a platform-specific local Vite executable exists."""
    return get_local_bin("vite") is not None


def get_node_package_version(package_name: str) -> str | None:
    """Read a local node package version from node_modules/package.json."""
    package_json_path = os.path.join(
        FRONTEND_DIR,
        "node_modules",
        *package_name.split("/"),
        "package.json",
    )
    if not os.path.exists(package_json_path):
        return None

    try:
        with open(package_json_path, "r", encoding="utf-8") as file:
            return json.load(file).get("version")
    except Exception:
        return None


def extract_missing_module_name(output: str) -> str | None:
    """Extract a missing module name from a Node.js error message."""
    patterns = [
        r"Cannot find module ['\"]([^'\"]+)['\"]",
        r"Cannot find module ([^ \r\n]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, output)
        if match:
            return match.group(1).strip().rstrip(".,:;")
    return None


def resolve_runtime_package_spec(package_name: str) -> str:
    """Build a package spec for platform runtime packages when a version pin is known."""
    version = None
    if package_name.startswith("@rollup/rollup-"):
        version = get_node_package_version("rollup")
    elif package_name.startswith("@esbuild/"):
        version = get_node_package_version("esbuild")

    return f"{package_name}@{version}" if version else package_name


def run_frontend_npm_install(args: list[str]) -> bool:
    """Run an npm install command inside frontend-web."""
    npm_bin = get_npm_executable()
    if shutil.which(npm_bin) is None:
        print("[!] npm was not found. Please install Node.js 18+ (20 LTS recommended).")
        return False

    env = os.environ.copy()
    env["NODE_ENV"] = "development"

    result = subprocess.run(
        [npm_bin, *args],
        cwd=FRONTEND_DIR,
        shell=False,
        env=env,
    )
    if result.returncode != 0:
        print(f"[!] Command failed: {npm_bin} {' '.join(args)} (exit code: {result.returncode})")
        return False
    return True


def get_vite_probe_command() -> list[str] | None:
    """Build a lightweight command used to verify Vite runtime dependencies."""
    vite_entry = get_vite_js_entry()
    if sys.platform == "win32" and vite_entry:
        node_bin = get_node_executable()
        if shutil.which(node_bin) is None:
            print("[!] node was not found. Please install Node.js 18+ (20 LTS recommended).")
            return None
        return [node_bin, vite_entry, "--version"]

    local_vite = get_local_bin("vite")
    if local_vite:
        return [local_vite, "--version"]

    if vite_entry:
        node_bin = get_node_executable()
        if shutil.which(node_bin) is None:
            print("[!] node was not found. Please install Node.js 18+ (20 LTS recommended).")
            return None
        return [node_bin, vite_entry, "--version"]

    return None


def ensure_vite_runtime_dependencies() -> bool:
    """Verify that Vite can actually start, and repair missing platform packages when possible."""
    probe_cmd = get_vite_probe_command()
    if probe_cmd is None:
        return False

    repaired_modules: set[str] = set()
    for _ in range(3):
        result = subprocess.run(
            probe_cmd,
            cwd=FRONTEND_DIR,
            shell=False,
            env={**os.environ.copy(), "NODE_ENV": "development"},
            capture_output=True,
            text=True,
            errors="replace",
        )
        output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()

        if result.returncode == 0:
            return True

        missing_module = extract_missing_module_name(output)
        if not missing_module or missing_module in repaired_modules:
            print("[!] Vite runtime self-check failed.")
            if output:
                first_line = output.splitlines()[0].strip()
                if first_line:
                    print(f"[!] {first_line}")
            return False

        repaired_modules.add(missing_module)
        if missing_module.startswith("@rollup/rollup-") or missing_module.startswith("@esbuild/"):
            print(
                f"[*] Detected missing optional platform runtime package {missing_module}. "
                "This usually means npm omitted optionalDependencies. "
                "Running: npm install --include=dev --include=optional"
            )
            if not run_frontend_npm_install(["install", "--include=dev", "--include=optional"]):
                return False
            continue

        package_spec = resolve_runtime_package_spec(missing_module)
        print(
            f"[*] Detected missing frontend runtime package {missing_module}. "
            f"Installing {package_spec}..."
        )
        if not run_frontend_npm_install(["install", "--no-save", "--no-package-lock", package_spec]):
            return False

    print("[!] Vite runtime dependencies could not be repaired automatically.")
    return False


def validate_project_layout() -> bool:
    """Validate the required frontend layout before startup."""
    required_paths = [
        FRONTEND_DIR,
        os.path.join(FRONTEND_DIR, "package.json"),
        os.path.join(FRONTEND_DIR, "electron", "main.cjs"),
    ]
    missing = [path for path in required_paths if not os.path.exists(path)]
    if not missing:
        return True

    print("[!] Project layout is incomplete. Cannot start Electron:")
    for path in missing:
        print(f"    - {path}")
    return False


def ensure_frontend_dependencies(mode: str, require_build_tools: bool = False) -> bool:
    """Ensure Electron frontend dependencies are installed for this platform."""
    requires_vite = mode == "dev" or require_build_tools
    electron_ready = has_local_electron()
    vite_ready = True if not requires_vite else has_local_vite()

    if electron_ready and vite_ready and (not requires_vite or ensure_vite_runtime_dependencies()):
        return True

    missing = []
    if sys.platform == "win32" and get_electron_cli_entry() and not electron_ready:
        missing.append("electron.cmd")
    elif not electron_ready:
        missing.append("electron")

    if requires_vite:
        if sys.platform == "win32" and get_vite_js_entry() and not vite_ready:
            missing.append("vite.cmd")
        elif not vite_ready:
            missing.append("vite")

    missing_text = ", ".join(missing) if missing else "Electron frontend dependencies"
    print(f"[*] Missing platform-ready {missing_text}. Repairing frontend dependencies...")
    if not run_frontend_npm_install(["install", "--include=dev", "--include=optional"]):
        return False

    electron_ready = has_local_electron()
    vite_ready = True if not requires_vite else has_local_vite()
    if not electron_ready or not vite_ready:
        print("[!] npm install completed, but Electron/Vite is still not available for this platform.")
        print("[!] Try running: cd frontend-web && npm install --include=dev --include=optional")
        return False

    if requires_vite and not ensure_vite_runtime_dependencies():
        print("[!] Vite exists, but its runtime dependencies are still incomplete for this platform.")
        return False

    print("[+] Electron frontend dependencies are ready")
    return True


def has_dist_build() -> bool:
    """Return whether the production dist build exists."""
    index_file = os.path.join(DIST_DIR, "index.html")
    return os.path.exists(index_file)


def ensure_frontend_build(force_build: bool) -> bool:
    """Ensure the production dist build exists."""
    if not force_build and has_dist_build():
        return True

    npm_bin = get_npm_executable()
    if shutil.which(npm_bin) is None:
        print("[!] npm was not found. Please install Node.js 18+ (20 LTS recommended).")
        return False

    if force_build:
        print("[*] Rebuilding Electron frontend assets...")
    else:
        print("[*] dist build was not found. Running npm run build...")

    build_cmd = [npm_bin, "run", "build"]
    result = subprocess.run(
        build_cmd,
        cwd=FRONTEND_DIR,
        shell=False,
        env=os.environ.copy(),
    )
    if result.returncode != 0:
        print(f"[!] Command failed: {' '.join(build_cmd)} (exit code: {result.returncode})")
        return False

    if not has_dist_build():
        print("[!] Build finished, but dist/index.html is still missing")
        return False

    print("[+] Electron frontend build artifacts are ready")
    return True


def get_electron_command(mode: str) -> list[str]:
    """Build the Electron startup command."""
    electron_args = [".", "--dev" if mode == "dev" else "--prod"]

    local_electron = get_local_bin("electron")
    if local_electron:
        return [local_electron, *electron_args]

    electron_cli = get_electron_cli_entry()
    if electron_cli:
        node_bin = get_node_executable()
        if shutil.which(node_bin) is None:
            raise RuntimeError("node was not found. Please install Node.js 18+ (20 LTS recommended).")
        return [node_bin, electron_cli, *electron_args]

    raise RuntimeError("Local Electron was not found. Run: cd frontend-web && npm install --include=dev --include=optional")


def start_electron(mode: str):
    """Start the Electron main process."""
    print(f"[*] Starting Electron ({'dev' if mode == 'dev' else 'prod'} mode)...")

    env = os.environ.copy()
    env["NODE_ENV"] = "development" if mode == "dev" else "production"
    env["ELECTRON_ENABLE_LOGGING"] = "1"

    cmd = get_electron_command(mode)
    process = subprocess.Popen(
        cmd,
        cwd=FRONTEND_DIR,
        shell=False,
        env=env,
    )
    processes.append(process)
    return process


def shutdown(exit_code: int = 0):
    """Terminate child processes and exit."""
    global is_cleaning_up

    if is_cleaning_up:
        sys.exit(exit_code)
    is_cleaning_up = True

    if processes:
        print("\n[!] Stopping Electron services...")
    for process in processes:
        try:
            if process.poll() is not None:
                continue
            if sys.platform == "win32":
                subprocess.call(["taskkill", "/F", "/T", "/PID", str(process.pid)])
            else:
                process.terminate()
        except Exception as error:
            print(f"Failed to stop process: {error}")

    sys.exit(exit_code)


def cleanup(signum=None, frame=None):
    """Handle termination signals."""
    shutdown(0)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="AFN Electron launcher")
    parser.add_argument(
        "--prod",
        action="store_true",
        help="start Electron with production assets (default is dev mode)",
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="force npm run build before launching in prod mode",
    )
    return parser.parse_args()


def main():
    # Register signal handlers
    configure_windows_console_utf8()
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    args = parse_args()
    mode = "prod" if args.prod else "dev"
    needs_build = mode == "prod" and (args.build or not has_dist_build())

    if args.build and mode != "prod":
        print("[i] --build only applies to --prod mode and will be ignored.")

    try:
        if not validate_project_layout():
            shutdown(1)

        if not ensure_frontend_dependencies(mode, require_build_tools=needs_build):
            print("[!] Electron frontend dependencies are not ready. Startup aborted.")
            shutdown(1)

        if mode == "prod" and not ensure_frontend_build(force_build=args.build):
            print("[!] Electron production assets are not ready. Startup aborted.")
            shutdown(1)

        electron_proc = start_electron(mode)
        time.sleep(2)
        if electron_proc.poll() is not None:
            print("[!] Electron exited immediately after startup")
            print("[!] If dependencies are missing, run: cd frontend-web && npm install --include=dev --include=optional")
            if mode == "prod":
                print("[!] If build artifacts are missing, run: cd frontend-web && npm run build")
            print("[!] If the backend environment is missing, run: python setup_env.py --force --web")
            shutdown(1)

        print("\n" + "=" * 50)
        print(" [+] AFN Electron started successfully")
        print(f"     Mode: {'dev' if mode == 'dev' else 'prod'}")
        print("     Electron will start backend and frontend services internally")
        print("=" * 50 + "\n")
        print("Press Ctrl+C to stop")

        while True:
            time.sleep(1)
            if electron_proc.poll() is not None:
                print("[!] Electron process exited unexpectedly")
                shutdown(1)

    except KeyboardInterrupt:
        shutdown(0)
    except Exception as error:
        print(f"[!] Error: {error}")
        shutdown(1)


if __name__ == "__main__":
    main()
