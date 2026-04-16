from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


class LauncherError(Exception):
    """Friendly error used for actionable launcher failures."""


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    backend: Path
    frontend: Path
    backend_manage: Path
    backend_requirements: Path
    frontend_package: Path
    root_env: Path
    root_env_example: Path
    backend_env: Path
    backend_env_example: Path
    frontend_env: Path
    frontend_env_example: Path
    docker_compose: Path
    state_dir: Path
    state_file: Path


@dataclass(frozen=True)
class PythonInterpreter:
    command: str
    source: str


@dataclass(frozen=True)
class ToolStatus:
    name: str
    found: bool
    command: str | None
    version: str | None


@dataclass(frozen=True)
class RuntimeMode:
    name: str
    app_mode: str
    django_settings_module: str
    use_infra: bool
    redis_required: bool
    sqlite_enabled: bool


ROOT = Path(__file__).resolve().parent
PATHS = ProjectPaths(
    root=ROOT,
    backend=ROOT / 'apps' / 'backend',
    frontend=ROOT / 'apps' / 'frontend',
    backend_manage=ROOT / 'apps' / 'backend' / 'manage.py',
    backend_requirements=ROOT / 'apps' / 'backend' / 'requirements.txt',
    frontend_package=ROOT / 'apps' / 'frontend' / 'package.json',
    root_env=ROOT / '.env',
    root_env_example=ROOT / '.env.example',
    backend_env=ROOT / 'apps' / 'backend' / '.env',
    backend_env_example=ROOT / 'apps' / 'backend' / '.env.example',
    frontend_env=ROOT / 'apps' / 'frontend' / '.env',
    frontend_env_example=ROOT / 'apps' / 'frontend' / '.env.example',
    docker_compose=ROOT / 'docker-compose.yml',
    state_dir=ROOT / '.tmp',
    state_file=ROOT / '.tmp' / 'start-state.json',
)

DEFAULT_PORTS = {
    'backend': 8000,
    'frontend': 5173,
    'postgres': 5432,
    'redis': 6379,
}
STARTUP_TIMEOUTS = {
    'backend_http': 60.0,
    'frontend_http': 60.0,
    'postgres_port': 45.0,
    'redis_port': 30.0,
}
DEFAULT_BROWSER_OPEN = True
DEFAULT_STARTUP_MODE = 'single-console'
DEFAULT_BROWSER_URL = f"http://localhost:{DEFAULT_PORTS['frontend']}/system"
VERBOSE_ENV_VARS = ('START_VERBOSE', 'MTB_START_VERBOSE')
DOCKER_DEFAULT_TIMEOUT_SECONDS = 120.0
OLLAMA_DEFAULT_TIMEOUT_SECONDS = 60.0
OLLAMA_HEALTH_URL = 'http://127.0.0.1:11434/api/tags'
STATUS_OK = 'OK'
STATUS_STARTING = 'STARTING'
STATUS_FAILED = 'FAILED'
STATUS_SKIPPED = 'SKIPPED'
LAUNCHER_OLLAMA_ENV_DEFAULTS = {
    'OLLAMA_ENABLED': 'true',
    'OLLAMA_BASE_URL': 'http://127.0.0.1:11434',
    'OLLAMA_MODEL': 'llama3.2:3b',
    'OLLAMA_CHAT_MODEL': 'llama3.2:3b',
    'OLLAMA_EMBED_MODEL': 'nomic-embed-text',
    'OLLAMA_TIMEOUT_SECONDS': '30',
    'OLLAMA_AUX_SIGNAL_ENABLED': 'false',
    'LLM_PROVIDER': 'ollama',
    'LLM_ENABLED': 'true',
}
FULL_MODE = RuntimeMode(
    name='FULL',
    app_mode='full',
    django_settings_module='config.settings.local',
    use_infra=True,
    redis_required=True,
    sqlite_enabled=False,
)
LITE_MODE = RuntimeMode(
    name='LITE',
    app_mode='lite',
    django_settings_module='config.settings.lite',
    use_infra=False,
    redis_required=False,
    sqlite_enabled=True,
)


def info(message: str) -> None:
    print(f'[INFO] {message}')


def ok(message: str) -> None:
    print(f'[OK] {message}')


def warn(message: str) -> None:
    print(f'[WARN] {message}')


def fail(message: str) -> None:
    raise LauncherError(message)


def env_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {'1', 'true', 'yes', 'on', 'y'}


def verbose_logging_enabled(args: argparse.Namespace) -> bool:
    if getattr(args, 'verbose', False):
        return True
    for name in VERBOSE_ENV_VARS:
        if env_truthy(os.environ.get(name)):
            return True
    return False


def build_paths() -> ProjectPaths:
    return PATHS


def ensure_project_structure(paths: ProjectPaths) -> None:
    required_paths = {
        'apps/backend': paths.backend,
        'apps/frontend': paths.frontend,
        'apps/backend/manage.py': paths.backend_manage,
        'apps/backend/requirements.txt': paths.backend_requirements,
        'apps/frontend/package.json': paths.frontend_package,
        'docker-compose.yml': paths.docker_compose,
    }
    missing = [name for name, path in required_paths.items() if not path.exists()]
    if missing:
        fail(
            'Repository structure is incomplete. Missing: '
            + ', '.join(missing)
            + '. Please confirm the monorepo still uses apps/backend and apps/frontend.'
        )


def subprocess_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault('PYTHONUNBUFFERED', '1')
    if os.name == 'nt':
        env['PATH'] = os.environ.get('PATH', env.get('PATH', ''))
        env['PATHEXT'] = os.environ.get('PATHEXT', env.get('PATHEXT', ''))
    if extra:
        env.update(extra)
    return env


def run_command(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    capture_output: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    safe_env = subprocess_env(env)
    try:
        return subprocess.run(
            [str(part) for part in command],
            cwd=cwd,
            env=safe_env,
            check=check,
            text=True,
            capture_output=capture_output,
        )
    except FileNotFoundError:
        fail(
            f'Command not found: {command[0]}. '
            'Please verify it from the same terminal with the exact command shown above.'
        )
    except subprocess.CalledProcessError as exc:
        if capture_output:
            output = '\n'.join(part for part in [exc.stdout, exc.stderr] if part).strip()
            detail = f'\n{output}' if output else ''
            fail(f"Command failed ({' '.join(str(part) for part in command)}).{detail}")
        fail(f"Command failed ({' '.join(str(part) for part in command)}).")


def parse_env_file(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        values[key.strip()] = value.strip()
    return values


def command_candidates(name: str) -> tuple[str, ...]:
    if os.name != 'nt':
        return (name,)
    windows_aliases = {
        'node': ('node', 'node.exe'),
        'npm': ('npm', 'npm.cmd'),
        'py': ('py', 'py.exe'),
        'python': ('python', 'python.exe'),
    }
    return windows_aliases.get(name, (name,))


def resolve_command(name: str) -> str | None:
    for candidate in command_candidates(name):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def has_command(name: str) -> bool:
    return resolve_command(name) is not None


def npm_exec() -> str:
    return shutil.which('npm') or shutil.which('npm.cmd') or 'npm'


def node_exec() -> str:
    return shutil.which('node') or shutil.which('node.exe') or 'node'


def command_version_candidates(candidates: Sequence[str]) -> str | None:
    for candidate in candidates:
        try:
            result = subprocess.run(
                [candidate, '--version'],
                check=False,
                text=True,
                capture_output=True,
                env=subprocess_env(),
            )
        except (FileNotFoundError, OSError):
            continue
        if result.returncode == 0:
            output = '\n'.join(part for part in [result.stdout, result.stderr] if part).strip()
            return output.splitlines()[0] if output else 'available'
    return None


def node_version() -> str | None:
    return command_version_candidates(command_candidates('node'))


def npm_version() -> str | None:
    candidates = ['npm']
    if os.name == 'nt':
        candidates.append('npm.cmd')
    return command_version_candidates(candidates)


def inspect_node_tooling() -> dict[str, ToolStatus]:
    node_command = resolve_command('node')
    npm_command = shutil.which('npm') or shutil.which('npm.cmd')
    return {
        'node': ToolStatus(
            name='node',
            found=node_command is not None,
            command=node_command,
            version=node_version(),
        ),
        'npm': ToolStatus(
            name='npm',
            found=npm_command is not None,
            command=npm_command,
            version=npm_version(),
        ),
    }


def ensure_node_tooling() -> dict[str, ToolStatus]:
    tooling = inspect_node_tooling()
    node = tooling['node']
    npm = tooling['npm']

    if node.found and npm.found:
        ok(
            'Node.js tooling detected '
            f"(node: {node.version or 'available'}, npm: {npm.version or 'available'})."
        )
        return tooling

    diagnostics = [
        'Frontend tooling is required but Node.js/npm could not be resolved correctly.',
        f"node found: {'yes' if node.found else 'no'}; resolved command: {node.command or 'not found'}; version: {node.version or 'unavailable'}.",
        f"npm found: {'yes' if npm.found else 'no'}; resolved command: {npm.command or 'not found'}; version: {npm.version or 'unavailable'}.",
        'From the same PowerShell or VS Code terminal, verify:',
        '  node --version',
        '  npm --version',
    ]
    if os.name == 'nt':
        diagnostics.extend(
            [
                'On Windows this launcher also checks npm.cmd and node.exe explicitly.',
                'If those commands work interactively, reopen the terminal so PATH/PATHEXT refresh correctly.',
            ]
        )
    fail(' '.join(diagnostics))


def is_valid_python_interpreter(command: str) -> bool:
    try:
        result = subprocess.run(
            [command, '--version'],
            check=False,
            text=True,
            capture_output=True,
            env=subprocess_env(),
        )
    except (FileNotFoundError, OSError):
        return False
    return result.returncode == 0


def resolve_python_interpreter() -> PythonInterpreter | None:
    candidates: list[PythonInterpreter] = []

    if sys.executable:
        candidates.append(PythonInterpreter(command=sys.executable, source='sys.executable'))

    candidates.extend(
        PythonInterpreter(command=name, source=name)
        for name in ('python', 'python3')
    )

    if os.name == 'nt':
        candidates.append(PythonInterpreter(command='py', source='py'))

    seen: set[str] = set()
    for candidate in candidates:
        if candidate.command in seen:
            continue
        seen.add(candidate.command)
        if is_valid_python_interpreter(candidate.command):
            return candidate
    return None


def detect_docker_compose() -> tuple[list[str] | None, str]:
    docker = shutil.which('docker')
    if docker:
        result = subprocess.run(
            [docker, 'compose', 'version'],
            check=False,
            text=True,
            capture_output=True,
            env=subprocess_env(),
        )
        if result.returncode == 0:
            return [docker, 'compose'], 'docker compose'

    docker_compose = shutil.which('docker-compose')
    if docker_compose:
        return [docker_compose], 'docker-compose'
    return None, 'missing'


def ensure_python_available() -> PythonInterpreter:
    python = resolve_python_interpreter()
    if python is None:
        fail(
            'Python is required but no valid interpreter was found. '
            'Try running this launcher with py, python, or python3.'
        )
    return python


def ensure_docker_available() -> tuple[list[str], str]:
    compose_command, compose_mode = detect_docker_compose()
    if compose_command is None:
        fail(
            'Docker Compose is required to start PostgreSQL and Redis but was not found. '
            'Please verify `docker --version` and `docker compose version` in this terminal.'
        )
    return compose_command, compose_mode


def command_output(command: Sequence[str]) -> str:
    result = run_command(command, capture_output=True, check=False)
    output = '\n'.join(part for part in [result.stdout, result.stderr] if part).strip()
    return output.splitlines()[0] if output else 'available'


def verify_prerequisites(*, require_node: bool, require_docker: bool) -> dict[str, Any]:
    python = ensure_python_available()
    node_tooling = ensure_node_tooling() if require_node else inspect_node_tooling()
    compose_command, compose_mode = detect_docker_compose()

    if require_docker and compose_command is None:
        fail(
            'Docker Compose is required to start PostgreSQL and Redis but was not found. '
            'Please verify `docker --version` and `docker compose version`.'
        )

    return {
        'python': python,
        'node_tooling': node_tooling,
        'docker_compose': compose_command,
        'docker_compose_mode': compose_mode,
    }


def runtime_mode_from_args(args: argparse.Namespace) -> RuntimeMode:
    return LITE_MODE if getattr(args, 'lite', False) else FULL_MODE


def announce_runtime_mode(mode: RuntimeMode, *, skip_infra: bool) -> None:
    info(f'Running in {mode.name} mode.')
    if mode.sqlite_enabled:
        info('SQLite enabled.')
    if skip_infra:
        info('Docker skipped.')
    if mode.redis_required:
        info('Redis required in this mode.')
    else:
        info('Redis disabled/optional in lite mode.')


def ensure_env_file(target: Path, template: Path) -> bool:
    if target.exists():
        ok(f'Environment file already present: {target.relative_to(PATHS.root)}')
        return False

    if not template.exists():
        warn(f'Environment template not found for {target.relative_to(PATHS.root)}')
        return False

    shutil.copyfile(template, target)
    ok(f'Created {target.relative_to(PATHS.root)} from {template.relative_to(PATHS.root)}')
    return True


def ensure_env_files() -> None:
    info('Ensuring environment files are present...')
    ensure_env_file(PATHS.root_env, PATHS.root_env_example)
    ensure_env_file(PATHS.backend_env, PATHS.backend_env_example)
    ensure_env_file(PATHS.frontend_env, PATHS.frontend_env_example)


def read_combined_local_env(paths: ProjectPaths) -> dict[str, str]:
    combined: dict[str, str] = {}
    for env_path in (paths.root_env, paths.backend_env, paths.frontend_env):
        combined.update(parse_env_file(env_path))
    return combined


def launcher_runtime_env(paths: ProjectPaths, mode: RuntimeMode) -> dict[str, str]:
    combined_env = read_combined_local_env(paths)
    runtime_defaults = {
        **LAUNCHER_OLLAMA_ENV_DEFAULTS,
        'APP_MODE': mode.app_mode,
        'DJANGO_SETTINGS_MODULE': mode.django_settings_module,
    }
    for key, default_value in runtime_defaults.items():
        combined_env.setdefault(key, default_value)
    return combined_env


def resolve_ollama_backend_enabled(args: argparse.Namespace, mode: RuntimeMode) -> bool:
    selected = str(getattr(args, 'ollama', '') or '').strip().lower()
    if selected == 'enabled':
        return True
    if selected == 'disabled':
        return False
    return mode is FULL_MODE


def apply_ollama_backend_policy(runtime_env: dict[str, str], *, enabled: bool) -> dict[str, str]:
    resolved = dict(runtime_env)
    if enabled:
        resolved['OLLAMA_ENABLED'] = 'true'
        resolved['LLM_ENABLED'] = 'true'
        resolved['LLM_PROVIDER'] = 'ollama'
        resolved.setdefault('OLLAMA_BASE_URL', LAUNCHER_OLLAMA_ENV_DEFAULTS['OLLAMA_BASE_URL'])
        resolved.setdefault('OLLAMA_MODEL', LAUNCHER_OLLAMA_ENV_DEFAULTS['OLLAMA_MODEL'])
        resolved.setdefault('OLLAMA_CHAT_MODEL', resolved.get('OLLAMA_MODEL', LAUNCHER_OLLAMA_ENV_DEFAULTS['OLLAMA_CHAT_MODEL']))
        resolved.setdefault('OLLAMA_TIMEOUT_SECONDS', LAUNCHER_OLLAMA_ENV_DEFAULTS['OLLAMA_TIMEOUT_SECONDS'])
        return resolved

    resolved['OLLAMA_ENABLED'] = 'false'
    resolved['OLLAMA_AUX_SIGNAL_ENABLED'] = 'false'
    resolved['LLM_ENABLED'] = 'false'
    return resolved


def get_backend_venv_python(paths: ProjectPaths) -> Path:
    if os.name == 'nt':
        return paths.backend / '.venv' / 'Scripts' / 'python.exe'
    return paths.backend / '.venv' / 'bin' / 'python'


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ensure_backend_venv(paths: ProjectPaths) -> Path:
    venv_python = get_backend_venv_python(paths)
    if venv_python.exists():
        ok('Backend virtual environment already present.')
        return venv_python

    interpreter = ensure_python_available()
    info(f'Creating backend virtual environment with {interpreter.command}...')
    run_command([interpreter.command, '-m', 'venv', str(paths.backend / '.venv')], cwd=paths.backend)
    ok('Backend virtual environment created.')
    return venv_python


def ensure_backend_dependencies(paths: ProjectPaths, *, skip_install: bool) -> Path:
    venv_python = ensure_backend_venv(paths)
    stamp = paths.backend / '.venv' / '.mtb-requirements.sha256'
    requirements_hash = hash_file(paths.backend_requirements)
    installed_hash = stamp.read_text(encoding='utf-8').strip() if stamp.exists() else None

    if skip_install:
        warn('Skipping backend dependency installation because --skip-install was used.')
        return venv_python

    if installed_hash == requirements_hash:
        ok('Backend dependencies already match requirements.txt.')
        return venv_python

    info('Installing backend dependencies...')
    run_command([str(venv_python), '-m', 'pip', 'install', '--upgrade', 'pip'], cwd=paths.backend)
    run_command([str(venv_python), '-m', 'pip', 'install', '-r', str(paths.backend_requirements)], cwd=paths.backend)
    stamp.write_text(requirements_hash, encoding='utf-8')
    ok('Backend dependencies installed.')
    return venv_python


def ensure_frontend_deps(paths: ProjectPaths, *, skip_install: bool) -> None:
    if not paths.frontend_package.exists():
        fail(
            'Frontend package.json is missing at apps/frontend/package.json. '
            'Please confirm the monorepo structure before running frontend commands.'
        )

    ensure_node_tooling()

    node_modules = paths.frontend / 'node_modules'
    package_lock = paths.frontend / 'package-lock.json'
    stamp = node_modules / '.mtb-package.sha256'
    hash_input = paths.frontend_package.read_text(encoding='utf-8')
    if package_lock.exists():
        hash_input += package_lock.read_text(encoding='utf-8')
    package_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
    installed_hash = stamp.read_text(encoding='utf-8').strip() if stamp.exists() else None

    if skip_install:
        warn('Skipping frontend dependency installation because --skip-install was used.')
        return

    if not node_modules.exists():
        info('apps/frontend/node_modules is missing, so npm install will run now...')
    elif installed_hash != package_hash:
        info('Frontend dependency manifest changed, so npm install will run now...')
    else:
        ok('Frontend dependencies already installed.')
        return

    run_command([npm_exec(), 'install'], cwd=paths.frontend)
    node_modules.mkdir(parents=True, exist_ok=True)
    stamp.write_text(package_hash, encoding='utf-8')
    ok('Frontend dependencies installed.')


def backend_command_env(
    paths: ProjectPaths,
    mode: RuntimeMode,
    *,
    runtime_env: dict[str, str] | None = None,
) -> dict[str, str]:
    runtime_env = runtime_env or launcher_runtime_env(paths, mode)
    runtime_env['DJANGO_SETTINGS_MODULE'] = os.environ.get(
        'DJANGO_SETTINGS_MODULE',
        runtime_env.get('DJANGO_SETTINGS_MODULE', mode.django_settings_module),
    )
    return subprocess_env(runtime_env)


def frontend_command_env() -> dict[str, str]:
    return subprocess_env()


def run_backend_manage(
    paths: ProjectPaths,
    mode: RuntimeMode,
    args: Sequence[str],
    *,
    capture_output: bool = False,
    check: bool = True,
    runtime_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    venv_python = get_backend_venv_python(paths)
    if not venv_python.exists():
        fail('Backend virtual environment is missing. Run python start.py setup first.')
    return run_command(
        [str(venv_python), str(paths.backend_manage), *args],
        cwd=paths.backend,
        env=backend_command_env(paths, mode, runtime_env=runtime_env),
        capture_output=capture_output,
        check=check,
    )


def port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        return sock.connect_ex((host, port)) == 0


def wait_for_port(host: str, port: int, *, timeout: float, label: str) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if port_open(host, port):
            ok(f'{label} is reachable on {host}:{port}.')
            return
        time.sleep(1)
    fail(f'Timed out waiting for {label} on {host}:{port}.')


def http_ready(url: str, *, timeout: float = 2.0) -> bool:
    request = urllib.request.Request(url, method='GET')
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 500
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
        return False


def wait_until(predicate: Any, *, timeout: float, interval: float = 1.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def docker_daemon_ready() -> bool:
    docker = shutil.which('docker')
    if not docker:
        return False
    try:
        result = subprocess.run(
            [docker, 'info', '--format', '{{.ServerVersion}}'],
            check=False,
            text=True,
            capture_output=True,
            env=subprocess_env(),
        )
    except (FileNotFoundError, OSError):
        return False
    return result.returncode == 0


def try_start_windows_app(paths: Sequence[Path]) -> bool:
    if os.name != 'nt':
        return False
    for path in paths:
        if not path.exists():
            continue
        try:
            os.startfile(str(path))  # type: ignore[attr-defined]
            return True
        except OSError:
            continue
    return False


def ensure_docker_daemon_ready(*, timeout: float) -> tuple[str, str]:
    if docker_daemon_ready():
        return STATUS_OK, 'Docker daemon is already reachable.'

    started = try_start_windows_app(
        [
            Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'Docker' / 'Docker' / 'Docker Desktop.exe',
            Path(os.environ.get('ProgramW6432', r'C:\Program Files')) / 'Docker' / 'Docker' / 'Docker Desktop.exe',
        ]
    )
    if started:
        info('Docker was not reachable. Docker Desktop launch was requested; waiting for daemon startup...')
    else:
        warn('Docker daemon is not reachable and Docker Desktop could not be auto-opened from default paths.')

    if wait_until(docker_daemon_ready, timeout=timeout, interval=2.0):
        return STATUS_OK, 'Docker daemon became reachable.'
    return STATUS_FAILED, (
        'Docker daemon is still not reachable. Start Docker Desktop manually and verify `docker info`.'
    )


def ollama_ready() -> bool:
    return http_ready(OLLAMA_HEALTH_URL, timeout=1.5)


def find_ollama_command() -> str | None:
    return shutil.which('ollama') or shutil.which('ollama.exe')


def ensure_ollama_ready(*, timeout: float, managed_processes: list[dict[str, Any]]) -> tuple[str, str]:
    if ollama_ready():
        return STATUS_OK, 'Ollama API is already reachable.'

    launched = False
    launch_notes: list[str] = []

    if os.name == 'nt':
        launched = try_start_windows_app(
            [
                Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'Ollama' / 'Ollama.exe',
            ]
        )
        if launched:
            launch_notes.append('Ollama desktop app launch requested.')

    ollama_command = find_ollama_command()
    if ollama_command:
        try:
            serve_process, log_path = spawn_detached_process(
                'ollama',
                [ollama_command, 'serve'],
                cwd=PATHS.root,
                log_name='ollama.log',
            )
            managed_processes.append(
                {
                    'label': 'ollama',
                    'pid': serve_process.pid,
                    'command': f'{ollama_command} serve',
                    'cwd': str(PATHS.root),
                    'mode': 'detached-process',
                    'log_file': str(log_path),
                }
            )
            launched = True
            launch_notes.append('`ollama serve` started by launcher.')
        except Exception:
            launch_notes.append('Failed to start `ollama serve` from launcher.')

    if not launched:
        return STATUS_FAILED, (
            'Ollama is not reachable and could not be auto-started. '
            'Install Ollama or run `ollama serve` manually.'
        )

    info('Ollama was not reachable; waiting for local Ollama API startup...')
    if wait_until(ollama_ready, timeout=timeout, interval=1.5):
        details = ' '.join(launch_notes) if launch_notes else 'Ollama became reachable.'
        return STATUS_OK, details
    return STATUS_FAILED, (
        'Ollama did not become reachable on localhost:11434 within timeout.'
    )


def wait_for_http(url: str, *, timeout: float, label: str) -> None:
    info(f'Waiting for {label} at {url}...')
    deadline = time.time() + timeout
    while time.time() < deadline:
        if http_ready(url):
            ok(f'{label} is responding at {url}.')
            return
        time.sleep(1)
    fail(
        f'Timed out waiting for {label} at {url}. '
        f'Check the launcher logs under {launcher_log_dir()} and run `python start.py status` for more details.'
    )


def open_browser(url: str, *, enabled: bool) -> bool:
    if not enabled:
        info('Browser auto-open is disabled by flag.')
        return False

    try:
        opened = webbrowser.open(url, new=2)
    except webbrowser.Error as exc:
        warn(f'Could not open the browser automatically: {exc}')
        return False

    if opened:
        ok(f'Browser opened: {url}')
    else:
        warn(f'Browser could not be opened automatically. Open this URL manually: {url}')
    return opened


def print_launcher_summary(
    *,
    mode: RuntimeMode,
    docker_status: str,
    ollama_status: str,
    backend_status: str,
    frontend_status: str,
    browser_url: str,
    browser_opened: bool,
    root_env: dict[str, str] | None = None,
    startup_mode: str = DEFAULT_STARTUP_MODE,
    ollama_backend_status: str = 'DISABLED',
    ollama_runtime_env: dict[str, str] | None = None,
) -> None:
    if root_env is None:
        root_env = parse_env_file(PATHS.root_env)

    frontend_port = DEFAULT_PORTS['frontend']
    backend_port = DEFAULT_PORTS['backend']

    print('\n=== Launcher summary ===')
    print(f'Mode:            {mode.name}')
    print(f'Startup mode:    {startup_mode}')
    print(f'Docker:          {docker_status}')
    print(f'Ollama:          {ollama_status}')
    print(f'Ollama service:  {ollama_status}')
    print(f'Ollama backend:  {ollama_backend_status}')
    print(f'Backend:         {backend_status}')
    print(f'Frontend:        {frontend_status}')
    print(f"Browser opened:  {'yes' if browser_opened else 'no'}")
    print(f'Primary URL:     {browser_url}')
    print('System available at:')
    if frontend_status == STATUS_OK:
        print(f'  - http://localhost:{frontend_port}/')
        print(f'  - http://localhost:{frontend_port}/system')
        print(f'  - http://localhost:{frontend_port}/markets')
    if backend_status == STATUS_OK:
        print(f'  - http://localhost:{backend_port}/api/health/')
        print(f'  - http://localhost:{backend_port}/admin/')
    print('Stop with:')
    if os.name == 'nt':
        print('  - py start.py down')
    else:
        print('  - python start.py down')

    if not browser_opened and frontend_status == STATUS_OK:
        print(f'Browser target:  {browser_url}')
    if ollama_runtime_env is not None:
        print('Ollama backend config:')
        print(f"  - enabled:      {ollama_runtime_env.get('OLLAMA_ENABLED', 'unset')}")
        print(f"  - base URL:     {ollama_runtime_env.get('OLLAMA_BASE_URL', 'unset')}")
        print(f"  - model:        {ollama_runtime_env.get('OLLAMA_MODEL', 'unset')}")
        print(f"  - timeout sec:  {ollama_runtime_env.get('OLLAMA_TIMEOUT_SECONDS', 'unset')}")
        print(f"  - aux signal:   {ollama_runtime_env.get('OLLAMA_AUX_SIGNAL_ENABLED', 'unset')}")
        print(f"  - llm enabled:  {ollama_runtime_env.get('LLM_ENABLED', 'unset')}")

    print('')
    if mode.use_infra:
        postgres_port = int(root_env.get('POSTGRES_PORT', DEFAULT_PORTS['postgres']))
        redis_port = int(root_env.get('REDIS_PORT', DEFAULT_PORTS['redis']))
        print('Infra ports:')
        print(f'  - PostgreSQL: {postgres_port}')
        print(f'  - Redis:      {redis_port}')
    else:
        print('Infra: Docker skipped; SQLite enabled; Redis optional/disabled.')


def start_infrastructure(paths: ProjectPaths, compose_command: Sequence[str]) -> None:
    root_env = parse_env_file(paths.root_env)
    postgres_port = int(root_env.get('POSTGRES_PORT', DEFAULT_PORTS['postgres']))
    redis_port = int(root_env.get('REDIS_PORT', DEFAULT_PORTS['redis']))

    info('Starting PostgreSQL and Redis with Docker Compose...')
    run_command([*compose_command, 'up', '-d', 'postgres', 'redis'], cwd=paths.root)
    wait_for_port('127.0.0.1', postgres_port, timeout=STARTUP_TIMEOUTS['postgres_port'], label='PostgreSQL')
    wait_for_port('127.0.0.1', redis_port, timeout=STARTUP_TIMEOUTS['redis_port'], label='Redis')


def stop_infrastructure(paths: ProjectPaths, compose_command: Sequence[str] | None) -> None:
    if compose_command is None:
        warn('Docker Compose is not available; skipping infrastructure shutdown.')
        return

    info('Stopping Docker Compose services...')
    run_command([*compose_command, 'down'], cwd=paths.root)
    ok('Docker Compose services stopped.')


def prepare_backend(paths: ProjectPaths, mode: RuntimeMode, *, skip_install: bool) -> Path:
    info('Preparing backend...')
    venv_python = ensure_backend_dependencies(paths, skip_install=skip_install)
    info('Running backend migrations...')
    run_backend_manage(paths, mode, ['migrate'])
    ok('Backend migrations completed.')
    return venv_python


def prepare_frontend(paths: ProjectPaths, *, skip_install: bool) -> None:
    info('Preparing frontend...')
    ensure_frontend_deps(paths, skip_install=skip_install)


def prepare_dev_environment(
    paths: ProjectPaths,
    mode: RuntimeMode,
    *,
    skip_backend: bool,
    skip_frontend: bool,
    skip_install: bool,
    no_seed: bool,
) -> None:
    if not skip_backend:
        prepare_backend(paths, mode, skip_install=skip_install)
        maybe_seed(paths, mode, no_seed=no_seed)
    else:
        warn('Skipping backend preparation.')

    if not skip_frontend:
        prepare_frontend(paths, skip_install=skip_install)
    else:
        warn('Skipping frontend preparation.')


def should_seed_demo(paths: ProjectPaths, mode: RuntimeMode) -> bool:
    result = run_backend_manage(
        paths,
        mode,
        ['shell', '-c', 'from apps.markets.models import Market; print("yes" if Market.objects.exists() else "no")'],
        capture_output=True,
    )
    status = result.stdout.strip().splitlines()[-1].strip().lower() if result.stdout.strip() else 'no'
    return status != 'yes'


def run_seed(paths: ProjectPaths, mode: RuntimeMode) -> None:
    info('Running demo seed...')
    run_backend_manage(paths, mode, ['seed_markets_demo'])
    ok('Demo market seed completed.')


def maybe_seed(paths: ProjectPaths, mode: RuntimeMode, *, no_seed: bool) -> None:
    if no_seed:
        warn('Skipping demo seed because --no-seed was used.')
        return

    if should_seed_demo(paths, mode):
        info('No market data detected, running demo seed automatically...')
        run_seed(paths, mode)
        return

    ok('Market data already exists; automatic demo seed skipped.')


def process_kwargs(new_console: bool = False) -> dict[str, Any]:
    kwargs: dict[str, Any] = {'text': True}
    if os.name == 'nt':
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        if new_console:
            creationflags |= subprocess.CREATE_NEW_CONSOLE
        kwargs['creationflags'] = creationflags
    else:
        kwargs['start_new_session'] = True
    return kwargs


def launcher_log_dir() -> Path:
    return PATHS.state_dir / 'logs'


def load_state_file() -> dict[str, Any]:
    if not PATHS.state_file.exists():
        return {}
    try:
        return json.loads(PATHS.state_file.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        warn(f'Launcher state file is invalid JSON and will be ignored: {PATHS.state_file}')
        return {}


def process_running(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def running_process_entries(processes: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    return [process for process in processes if process_running(process.get('pid'))]


def cleanup_state_file() -> dict[str, Any]:
    state = load_state_file()
    if not state:
        return {}

    processes = state.get('processes', [])
    running = running_process_entries(processes)
    if running:
        if len(running) != len(processes):
            state['processes'] = running
            write_state_file(
                running,
                startup_mode=state.get('startup_mode', DEFAULT_STARTUP_MODE),
                browser_auto_open=state.get('browser_auto_open', DEFAULT_BROWSER_OPEN),
                browser_url=state.get('browser_url', DEFAULT_BROWSER_URL),
                metadata=state.get('metadata'),
            )
        return state

    remove_state_file()
    return {}


def write_state_file(
    processes: list[dict[str, Any]],
    *,
    startup_mode: str,
    browser_auto_open: bool,
    browser_url: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    PATHS.state_dir.mkdir(parents=True, exist_ok=True)
    state = {
        'processes': processes,
        'startup_mode': startup_mode,
        'browser_auto_open': browser_auto_open,
        'browser_url': browser_url,
        'metadata': metadata or {},
    }
    PATHS.state_file.write_text(json.dumps(state, indent=2), encoding='utf-8')


def remove_state_file() -> None:
    if PATHS.state_file.exists():
        PATHS.state_file.unlink()


def ensure_no_running_launcher_processes() -> None:
    state = cleanup_state_file()
    running = running_process_entries(state.get('processes', []))
    if not running:
        return

    labels = ', '.join(process.get('label', 'process') for process in running)
    fail(
        'Launcher-managed services are already running '
        f'({labels}). Stop them first with `python start.py down`, '
        'or use `python start.py status` to inspect the current state.'
    )


def detached_process_kwargs(log_file: Path) -> dict[str, Any]:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    stream = open(log_file, 'a', encoding='utf-8')
    kwargs: dict[str, Any] = {
        'text': True,
        'stdout': stream,
        'stderr': subprocess.STDOUT,
        'stdin': subprocess.DEVNULL,
    }
    if os.name == 'nt':
        kwargs['creationflags'] = (
            subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NO_WINDOW
        )
    else:
        kwargs['start_new_session'] = True
    return kwargs


def spawn_process(label: str, command: Sequence[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.Popen[str]:
    info(f"Starting {label}: {' '.join(str(part) for part in command)}")
    return subprocess.Popen(
        [str(part) for part in command],
        cwd=cwd,
        env=subprocess_env(env),
        **process_kwargs(),
    )


def spawn_detached_process(
    label: str,
    command: Sequence[str],
    cwd: Path,
    *,
    env: dict[str, str] | None = None,
    log_name: str | None = None,
) -> tuple[subprocess.Popen[str], Path]:
    log_path = launcher_log_dir() / (log_name or f'{label.replace(" ", "-")}.log')
    kwargs = detached_process_kwargs(log_path)
    stdout_stream = kwargs['stdout']
    info(f"Starting {label} in detached mode: {' '.join(str(part) for part in command)}")
    try:
        process = subprocess.Popen(
            [str(part) for part in command],
            cwd=cwd,
            env=subprocess_env(env),
            **kwargs,
        )
    finally:
        stdout_stream.close()
    return process, log_path


def open_new_console_windows(process_specs: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    launched: list[dict[str, Any]] = []
    for spec in process_specs:
        label = spec['label']
        command = [str(part) for part in spec['command']]
        cwd = str(spec['cwd'])
        title = spec.get('title', label)
        info(f"Opening new console for {label}: {' '.join(command)}")
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=subprocess_env(spec.get('env')),
            **process_kwargs(new_console=True),
        )
        launched.append(
            {
                'label': label,
                'pid': process.pid,
                'command': ' '.join(command),
                'cwd': cwd,
                'mode': 'windows-console',
                'title': title,
            }
        )
    return launched


def stop_managed_processes() -> None:
    state = load_state_file()
    if not state:
        warn('No launcher-managed process state file was found.')
        return

    stop_process_entries(state.get('processes', []))
    remove_state_file()


def stop_process_entries(processes: Sequence[dict[str, Any]]) -> None:
    for process in processes:
        pid = process.get('pid')
        label = process.get('label', 'process')
        if not pid:
            continue
        try:
            if os.name == 'nt':
                subprocess.run(
                    ['taskkill', '/PID', str(pid), '/T', '/F'],
                    check=False,
                    capture_output=True,
                    text=True,
                    env=subprocess_env(),
                )
            else:
                os.killpg(pid, signal.SIGTERM)
            ok(f'Stopped {label} (pid {pid}).')
        except ProcessLookupError:
            warn(f'{label} (pid {pid}) was already stopped.')
        except PermissionError:
            warn(f'Permission denied while stopping {label} (pid {pid}).')


def print_urls(root_env: dict[str, str] | None = None) -> None:
    frontend_port = DEFAULT_PORTS['frontend']
    backend_port = DEFAULT_PORTS['backend']
    if root_env is None:
        root_env = parse_env_file(PATHS.root_env)
    postgres_port = int(root_env.get('POSTGRES_PORT', DEFAULT_PORTS['postgres']))
    redis_port = int(root_env.get('REDIS_PORT', DEFAULT_PORTS['redis']))

    print('\n=== Local URLs ===')
    print(f'Frontend:    http://localhost:{frontend_port}/')
    print(f'Backend API: http://localhost:{backend_port}/api/')
    print(f'Admin:       http://localhost:{backend_port}/admin/')
    print(f'System page: http://localhost:{frontend_port}/system')
    print(f'Markets:     http://localhost:{frontend_port}/markets')
    print('')
    print('=== Expected local ports ===')
    print(f'Backend:  {backend_port}')
    print(f'Frontend: {frontend_port}')
    print(f'Postgres: {postgres_port}')
    print(f'Redis:    {redis_port}')


def service_urls() -> dict[str, str]:
    return {
        'backend_health': f"http://localhost:{DEFAULT_PORTS['backend']}/api/health/",
        'frontend_root': f"http://localhost:{DEFAULT_PORTS['frontend']}/",
        'frontend_system': DEFAULT_BROWSER_URL,
        'frontend_markets': f"http://localhost:{DEFAULT_PORTS['frontend']}/markets",
    }


def launcher_status_snapshot(paths: ProjectPaths) -> dict[str, Any]:
    state = cleanup_state_file()
    processes = state.get('processes', [])
    labels = {process.get('label'): process for process in processes}
    root_env_values = parse_env_file(paths.root_env)
    postgres_port = int(root_env_values.get('POSTGRES_PORT', DEFAULT_PORTS['postgres']))
    redis_port = int(root_env_values.get('REDIS_PORT', DEFAULT_PORTS['redis']))
    urls = service_urls()

    return {
        'state': state,
        'backend_process_running': process_running(labels.get('backend', {}).get('pid')),
        'frontend_process_running': process_running(labels.get('frontend', {}).get('pid')),
        'sim_loop_running': process_running(labels.get('simulation loop', {}).get('pid')),
        'infra_running': port_open('127.0.0.1', postgres_port) and port_open('127.0.0.1', redis_port),
        'backend_health_ready': http_ready(urls['backend_health']),
        'frontend_ready': http_ready(urls['frontend_root']),
        'postgres_port': postgres_port,
        'redis_port': redis_port,
        'urls': urls,
    }


def backend_run_command(paths: ProjectPaths) -> list[str]:
    return [str(get_backend_venv_python(paths)), str(paths.backend_manage), 'runserver', '0.0.0.0:8000']


def frontend_run_command() -> list[str]:
    return [npm_exec(), 'run', 'dev', '--', '--host', '0.0.0.0', '--port', str(DEFAULT_PORTS['frontend'])]


def build_dev_process_specs(
    paths: ProjectPaths,
    mode: RuntimeMode,
    *,
    include_backend: bool,
    include_frontend: bool,
    with_sim_loop: bool,
    backend_runtime_env: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    process_specs: list[dict[str, Any]] = []
    if include_backend:
        process_specs.append(
            {
                'label': 'backend',
                'title': 'market-trading-bot backend',
                'command': backend_run_command(paths),
                'cwd': paths.backend,
                'env': backend_command_env(paths, mode, runtime_env=backend_runtime_env),
            }
        )
    if include_frontend:
        process_specs.append(
            {
                'label': 'frontend',
                'title': 'market-trading-bot frontend',
                'command': frontend_run_command(),
                'cwd': paths.frontend,
                'env': frontend_command_env(),
            }
        )
    if with_sim_loop:
        process_specs.append(
            {
                'label': 'simulation loop',
                'title': 'market-trading-bot simulation loop',
                'command': [str(get_backend_venv_python(paths)), str(paths.backend_manage), 'simulate_markets_loop'],
                'cwd': paths.backend,
                'env': backend_command_env(paths, mode, runtime_env=backend_runtime_env),
            }
        )
    return process_specs


def start_dev_servers_verbose(
    process_specs: Sequence[dict[str, Any]]
) -> tuple[list[dict[str, Any]], subprocess.Popen[str] | None]:
    launched: list[dict[str, Any]] = []
    backend_process: subprocess.Popen[str] | None = None
    try:
        for spec in process_specs:
            if spec['label'] == 'backend':
                process = spawn_process(
                    spec['label'],
                    spec['command'],
                    spec['cwd'],
                    env=spec.get('env'),
                )
                backend_process = process
                launched.append(
                    {
                        'label': spec['label'],
                        'pid': process.pid,
                        'command': ' '.join(str(part) for part in spec['command']),
                        'cwd': str(spec['cwd']),
                        'mode': 'console-attached',
                        'log_file': None,
                    }
                )
                continue

            process, log_path = spawn_detached_process(
                spec['label'],
                spec['command'],
                spec['cwd'],
                env=spec.get('env'),
                log_name=spec.get('log_name'),
            )
            launched.append(
                {
                    'label': spec['label'],
                    'pid': process.pid,
                    'command': ' '.join(str(part) for part in spec['command']),
                    'cwd': str(spec['cwd']),
                    'mode': 'detached-process',
                    'log_file': str(log_path),
                }
            )
    except Exception:
        stop_process_entries(launched)
        raise
    return launched, backend_process


def start_dev_servers(
    process_specs: Sequence[dict[str, Any]],
    *,
    startup_mode: str,
    browser_auto_open: bool,
    browser_url: str,
) -> list[dict[str, Any]]:
    if startup_mode == 'separate-windows':
        launched = open_new_console_windows(process_specs)
        write_state_file(
            launched,
            startup_mode=startup_mode,
            browser_auto_open=browser_auto_open,
            browser_url=browser_url,
        )
        return launched

    launched: list[dict[str, Any]] = []
    try:
        for spec in process_specs:
            process, log_path = spawn_detached_process(
                spec['label'],
                spec['command'],
                spec['cwd'],
                env=spec.get('env'),
                log_name=spec.get('log_name'),
            )
            launched.append(
                {
                    'label': spec['label'],
                    'pid': process.pid,
                    'command': ' '.join(str(part) for part in spec['command']),
                    'cwd': str(spec['cwd']),
                    'mode': 'detached-process',
                    'log_file': str(log_path),
                }
            )
    except Exception:
        stop_process_entries(launched)
        raise
    write_state_file(
        launched,
        startup_mode=startup_mode,
        browser_auto_open=browser_auto_open,
        browser_url=browser_url,
    )
    return launched


def command_up(args: argparse.Namespace) -> int:
    paths = build_paths()
    ensure_project_structure(paths)
    ensure_no_running_launcher_processes()
    mode = runtime_mode_from_args(args)
    ollama_backend_enabled = resolve_ollama_backend_enabled(args, mode)
    backend_runtime_env = apply_ollama_backend_policy(
        launcher_runtime_env(paths, mode),
        enabled=ollama_backend_enabled,
    )
    if mode is LITE_MODE and not args.skip_infra:
        warn('Lite mode selected; forcing --skip-infra so Docker is not required.')
        args.skip_infra = True
    announce_runtime_mode(mode, skip_infra=args.skip_infra)
    prereqs = verify_prerequisites(require_node=not args.skip_frontend, require_docker=not args.skip_infra)
    ensure_env_files()
    launcher_managed_bootstrap: list[dict[str, Any]] = []
    docker_status = STATUS_SKIPPED if args.skip_infra else STATUS_STARTING
    ollama_status = STATUS_SKIPPED if (args.skip_ollama or not ollama_backend_enabled) else STATUS_STARTING
    backend_status = STATUS_SKIPPED if args.skip_backend else STATUS_STARTING
    frontend_status = STATUS_SKIPPED if args.skip_frontend else STATUS_STARTING

    if not args.skip_infra:
        docker_status, docker_message = ensure_docker_daemon_ready(timeout=args.docker_timeout)
        info(f'Docker check: {docker_message}')
        if docker_status != STATUS_OK:
            fail(docker_message)
        start_infrastructure(paths, prereqs['docker_compose'])
    else:
        warn('Skipping infrastructure startup because --skip-infra was used.')

    try:
        if ollama_backend_enabled and not args.skip_ollama:
            ollama_status, ollama_message = ensure_ollama_ready(
                timeout=args.ollama_timeout,
                managed_processes=launcher_managed_bootstrap,
            )
            info(f'Ollama check: {ollama_message}')
            if ollama_status != STATUS_OK:
                fail(ollama_message)
        elif ollama_backend_enabled and args.skip_ollama:
            warn('Ollama backend enabled but --skip-ollama was used; readiness probe/startup skipped.')
        else:
            info('Ollama backend integration is disabled for this launch.')

        prepare_dev_environment(
            paths,
            mode,
            skip_backend=args.skip_backend,
            skip_frontend=args.skip_frontend,
            skip_install=args.skip_install,
            no_seed=args.no_seed,
        )

        include_backend = not args.skip_backend
        include_frontend = not args.skip_frontend
        if args.with_sim_loop and not include_backend:
            warn('Simulation loop was requested, but backend startup is skipped, so the loop was not started.')
        process_specs = build_dev_process_specs(
            paths,
            mode,
            include_backend=include_backend,
            include_frontend=include_frontend,
            with_sim_loop=args.with_sim_loop and include_backend,
            backend_runtime_env=backend_runtime_env,
        )

        startup_mode = 'separate-windows' if args.separate_windows else DEFAULT_STARTUP_MODE
        browser_url = DEFAULT_BROWSER_URL
        verbose_logs = verbose_logging_enabled(args)
        attached_backend: subprocess.Popen[str] | None = None
        started_processes: list[dict[str, Any]] = list(launcher_managed_bootstrap)
        if process_specs:
            if verbose_logs and startup_mode != 'separate-windows':
                launched_processes, attached_backend = start_dev_servers_verbose(process_specs)
                started_processes.extend(launched_processes)
                write_state_file(
                    started_processes,
                    startup_mode='verbose-console',
                    browser_auto_open=not args.no_browser,
                    browser_url=browser_url,
                    metadata={
                        'verbose_logging': True,
                        'ollama_service_status': ollama_status,
                        'backend_ollama_enabled': ollama_backend_enabled,
                        'backend_ollama_runtime_env': {
                            key: backend_runtime_env.get(key, 'unset')
                            for key in (
                                'OLLAMA_ENABLED',
                                'OLLAMA_BASE_URL',
                                'OLLAMA_MODEL',
                                'OLLAMA_TIMEOUT_SECONDS',
                                'OLLAMA_AUX_SIGNAL_ENABLED',
                                'LLM_PROVIDER',
                                'LLM_ENABLED',
                            )
                        },
                    },
                )
                info('Verbose logging enabled: backend logs are attached to this terminal.')
            else:
                if verbose_logs and startup_mode == 'separate-windows':
                    warn(
                        'Verbose logging is ignored with --separate-windows '
                        'because each service already has its own console.'
                    )
                launched_processes = start_dev_servers(
                    process_specs,
                    startup_mode=startup_mode,
                    browser_auto_open=not args.no_browser,
                    browser_url=browser_url,
                )
                started_processes.extend(launched_processes)
                write_state_file(
                    started_processes,
                    startup_mode=startup_mode,
                    browser_auto_open=not args.no_browser,
                    browser_url=browser_url,
                    metadata={
                        'ollama_service_status': ollama_status,
                        'backend_ollama_enabled': ollama_backend_enabled,
                        'backend_ollama_runtime_env': {
                            key: backend_runtime_env.get(key, 'unset')
                            for key in (
                                'OLLAMA_ENABLED',
                                'OLLAMA_BASE_URL',
                                'OLLAMA_MODEL',
                                'OLLAMA_TIMEOUT_SECONDS',
                                'OLLAMA_AUX_SIGNAL_ENABLED',
                                'LLM_PROVIDER',
                                'LLM_ENABLED',
                            )
                        },
                    },
                )
        elif started_processes:
            write_state_file(
                started_processes,
                startup_mode=startup_mode,
                browser_auto_open=not args.no_browser,
                browser_url=browser_url,
                metadata={
                    'ollama_service_status': ollama_status,
                    'backend_ollama_enabled': ollama_backend_enabled,
                    'backend_ollama_runtime_env': {
                        key: backend_runtime_env.get(key, 'unset')
                        for key in (
                            'OLLAMA_ENABLED',
                            'OLLAMA_BASE_URL',
                            'OLLAMA_MODEL',
                            'OLLAMA_TIMEOUT_SECONDS',
                            'OLLAMA_AUX_SIGNAL_ENABLED',
                            'LLM_PROVIDER',
                            'LLM_ENABLED',
                        )
                    },
                },
            )
        else:
            warn('Both backend and frontend startup were skipped; nothing was started.')

        urls = service_urls()
        if include_backend:
            wait_for_http(
                urls['backend_health'],
                timeout=STARTUP_TIMEOUTS['backend_http'],
                label='Backend healthcheck',
            )
            backend_status = STATUS_OK
        if include_frontend:
            wait_for_http(
                urls['frontend_root'],
                timeout=STARTUP_TIMEOUTS['frontend_http'],
                label='Frontend dev server',
            )
            frontend_status = STATUS_OK
        if docker_status == STATUS_STARTING:
            docker_status = STATUS_OK
        if ollama_status == STATUS_STARTING:
            ollama_status = STATUS_OK
        browser_opened = open_browser(browser_url, enabled=include_frontend and not args.no_browser)
        print_launcher_summary(
            mode=mode,
            docker_status=docker_status,
            ollama_status=ollama_status,
            backend_status=backend_status,
            frontend_status=frontend_status,
            browser_url=browser_url,
            browser_opened=browser_opened,
            startup_mode=startup_mode,
            ollama_backend_status='ENABLED' if ollama_backend_enabled else 'DISABLED',
            ollama_runtime_env=backend_runtime_env,
        )
        if started_processes:
            ok(
                'Launcher finished successfully in '
                f'{startup_mode} mode. Use `{"py" if os.name == "nt" else "python"} start.py down` when you want to stop everything.'
            )
        if attached_backend is not None:
            info('Backend is running in foreground for live logs. Press Ctrl+C to stop launcher-managed services.')
            attached_backend.wait()
            stop_managed_processes()
            if not args.skip_infra:
                stop_infrastructure(paths, prereqs['docker_compose'])
            return 0
        return 0
    except KeyboardInterrupt:
        warn('Startup interrupted. Stopping launcher-managed processes...')
        stop_process_entries(launcher_managed_bootstrap)
        stop_managed_processes()
        if not args.skip_infra:
            stop_infrastructure(paths, prereqs['docker_compose'])
        return 0
    except LauncherError:
        stop_process_entries(launcher_managed_bootstrap)
        stop_managed_processes()
        if not args.skip_infra:
            stop_infrastructure(paths, prereqs['docker_compose'])
        raise
    return 0


def command_full(args: argparse.Namespace) -> int:
    args.skip_infra = False
    args.lite = False
    if getattr(args, 'ollama', None) is None:
        args.ollama = 'enabled'
    return command_up(args)


def command_lite(args: argparse.Namespace) -> int:
    args.lite = True
    args.skip_infra = True
    if getattr(args, 'ollama', None) is None:
        args.ollama = 'disabled'
    return command_up(args)


def command_setup(args: argparse.Namespace) -> int:
    paths = build_paths()
    ensure_project_structure(paths)
    mode = runtime_mode_from_args(args)
    if mode is LITE_MODE and not args.skip_infra:
        warn('Lite mode selected; forcing --skip-infra so Docker is not required.')
        args.skip_infra = True
    announce_runtime_mode(mode, skip_infra=args.skip_infra)
    prereqs = verify_prerequisites(require_node=not args.skip_frontend, require_docker=not args.skip_infra)
    ensure_env_files()
    if not args.skip_infra:
        start_infrastructure(paths, prereqs['docker_compose'])
    prepare_dev_environment(
        paths,
        mode,
        skip_backend=args.skip_backend,
        skip_frontend=args.skip_frontend,
        skip_install=args.skip_install,
        no_seed=args.no_seed,
    )
    print_urls()
    ok('Setup completed. Use python start.py up when you want to start the servers.')
    return 0


def command_status(args: argparse.Namespace) -> int:
    paths = build_paths()
    ensure_project_structure(paths)
    python = resolve_python_interpreter()
    node_tooling = inspect_node_tooling()
    compose_command, compose_mode = detect_docker_compose()
    mode = runtime_mode_from_args(args)
    status = launcher_status_snapshot(paths)
    state = status['state']
    metadata = state.get('metadata', {}) if isinstance(state, dict) else {}
    root_env_values = parse_env_file(paths.root_env)
    backend_venv_python = get_backend_venv_python(paths)
    docker_found = shutil.which('docker') is not None
    ollama_command = find_ollama_command()
    combined_env = launcher_runtime_env(paths, mode)
    resolved_ollama_enabled = resolve_ollama_backend_enabled(args, mode)
    backend_env_preview = apply_ollama_backend_policy(combined_env, enabled=resolved_ollama_enabled)
    docker_live = docker_daemon_ready()
    ollama_live = ollama_ready()

    print('=== market-trading-bot local status ===')
    print(f'Runtime mode:             {mode.name}')
    print(f'App mode env:             {mode.app_mode}')
    print(f'Django settings default:  {mode.django_settings_module}')
    print(f'Repo root:               {paths.root}')
    print(f'Python current interpreter: {sys.executable or "not detected"}')
    print(f'Python launcher interpreter: {(python.command if python else "not detected")}')
    print(f'Python launcher source:  {(python.source if python else "not detected")}')
    print(f'Backend venv python:     {backend_venv_python} ({"present" if backend_venv_python.exists() else "missing"})')
    if python:
        print(f'Python version:          {command_output([python.command, "--version"])}')
    print('')
    print('Node / npm:')
    print(f"  Node found:            {'yes' if node_tooling['node'].found else 'no'}")
    print(f"  Node resolved command: {node_tooling['node'].command or 'not found'}")
    print(f"  Node version:          {node_tooling['node'].version or 'unavailable'}")
    print(f"  npm found:             {'yes' if node_tooling['npm'].found else 'no'}")
    print(f"  npm resolved command:  {node_tooling['npm'].command or 'not found'}")
    print(f"  npm version:           {node_tooling['npm'].version or 'unavailable'}")
    print('')
    print('Docker:')
    print(f"  Docker found:          {'yes' if docker_found else 'no'}")
    print(f"  Docker daemon ready:   {'yes' if docker_live else 'no'}")
    print(f"  Docker Compose mode:   {compose_mode}")
    print(f"  Docker Compose command:{' ' + ' '.join(compose_command) if compose_command else ' not found'}")
    print('')
    print('Ollama:')
    print(f"  Ollama command found:  {'yes' if bool(ollama_command) else 'no'}")
    print(f"  Ollama command:        {ollama_command or 'not found'}")
    print(f"  Ollama API ready:      {'yes' if ollama_live else 'no'}")
    print(f'  Ollama endpoint:       {OLLAMA_HEALTH_URL}')
    print(f"  Ollama in backend:     {'enabled' if env_truthy(backend_env_preview.get('OLLAMA_ENABLED')) else 'disabled'}")
    print('')
    print('Launcher runtime env (resolved defaults):')
    for key in (
        'APP_MODE',
        'DJANGO_SETTINGS_MODULE',
        'OLLAMA_ENABLED',
        'OLLAMA_BASE_URL',
        'OLLAMA_MODEL',
        'OLLAMA_CHAT_MODEL',
        'OLLAMA_EMBED_MODEL',
        'OLLAMA_TIMEOUT_SECONDS',
        'OLLAMA_AUX_SIGNAL_ENABLED',
        'LLM_PROVIDER',
        'LLM_ENABLED',
    ):
        print(f'  {key}: {combined_env.get(key, "unset")}')
    print('')
    print('Backend env passed by launcher (effective):')
    for key in (
        'OLLAMA_ENABLED',
        'OLLAMA_BASE_URL',
        'OLLAMA_MODEL',
        'OLLAMA_TIMEOUT_SECONDS',
        'OLLAMA_AUX_SIGNAL_ENABLED',
        'LLM_PROVIDER',
        'LLM_ENABLED',
    ):
        print(f'  {key}: {backend_env_preview.get(key, "unset")}')
    if metadata:
        print('')
        print('Last launch metadata:')
        print(f"  Ollama service status: {metadata.get('ollama_service_status', 'unknown')}")
        print(f"  Backend Ollama:        {'ENABLED' if metadata.get('backend_ollama_enabled') else 'DISABLED'}")
        runtime_from_state = metadata.get('backend_ollama_runtime_env', {})
        if isinstance(runtime_from_state, dict) and runtime_from_state:
            print('  Backend Ollama runtime:')
            for key in (
                'OLLAMA_ENABLED',
                'OLLAMA_BASE_URL',
                'OLLAMA_MODEL',
                'OLLAMA_TIMEOUT_SECONDS',
                'OLLAMA_AUX_SIGNAL_ENABLED',
                'LLM_PROVIDER',
                'LLM_ENABLED',
            ):
                if key in runtime_from_state:
                    print(f'    - {key}: {runtime_from_state[key]}')
    print('')
    print('Environment files:')
    print(f"  .env:                  {'present' if paths.root_env.exists() else 'missing'}")
    print(f"  apps/backend/.env:     {'present' if paths.backend_env.exists() else 'missing'}")
    print(f"  apps/frontend/.env:    {'present' if paths.frontend_env.exists() else 'missing'}")
    print('')
    print('Dependency state:')
    print(f"  apps/backend/.venv:    {'present' if (paths.backend / '.venv').exists() else 'missing'}")
    print(f"  apps/frontend/node_modules: {'present' if (paths.frontend / 'node_modules').exists() else 'missing'}")
    print('')
    print('Ports:')
    print(f"  backend:               {DEFAULT_PORTS['backend']}")
    print(f"  frontend:              {DEFAULT_PORTS['frontend']}")
    print(f"  postgres:              {status['postgres_port']}")
    print(f"  redis:                 {status['redis_port']}")
    print('')
    print('Launcher runtime:')
    print(f"  backend process running: {'yes' if status['backend_process_running'] else 'no'}")
    print(f"  frontend process running: {'yes' if status['frontend_process_running'] else 'no'}")
    print(f"  simulation loop running: {'yes' if status['sim_loop_running'] else 'no'}")
    print(f"  infra running:          {'yes' if status['infra_running'] else 'no'}")
    print(f"  backend ready:          {'yes' if status['backend_health_ready'] else 'no'}")
    print(f"  frontend ready:         {'yes' if status['frontend_ready'] else 'no'}")
    print(f"  browser auto-open default: {'yes' if state.get('browser_auto_open', DEFAULT_BROWSER_OPEN) else 'no'}")
    print(f"  startup mode:           {state.get('startup_mode', DEFAULT_STARTUP_MODE)}")
    print('')
    print('Quick service summary:')
    print(f"  Docker:                {STATUS_OK if docker_live else STATUS_FAILED}")
    print(f"  Ollama service:        {STATUS_OK if ollama_live else STATUS_FAILED}")
    print(
        "  Ollama backend:        "
        + ('ENABLED' if env_truthy(backend_env_preview.get('OLLAMA_ENABLED')) else 'DISABLED')
    )
    print(f"  Ollama:                {STATUS_OK if ollama_live else STATUS_FAILED}")
    print(f"  Backend:               {STATUS_OK if status['backend_health_ready'] else STATUS_FAILED}")
    print(f"  Frontend:              {STATUS_OK if status['frontend_ready'] else STATUS_FAILED}")
    print_urls(root_env_values)
    print('')
    print('Recommended commands:')
    print('  python start.py status')
    print('  python start.py full')
    print('  python start.py lite')
    print('  python start.py logs')
    print('  python start.py stop')
    print('  python start.py setup')
    print('  python start.py up')
    print('  python start.py seed')
    print('  python start.py simulate-tick')
    print('  python start.py simulate-loop')
    print('  python start.py down')
    print('')
    if PATHS.state_file.exists():
        print(f'Launcher state file:     present at {PATHS.state_file}')
        for process in state.get('processes', []):
            log_file = process.get('log_file', 'n/a')
            print(
                f"  - {process.get('label', 'process')}: pid {process.get('pid', 'n/a')}, "
                f"mode {process.get('mode', 'unknown')}, log {log_file}"
            )
    else:
        print('Launcher state file:     not present')
    return 0


def command_down(_: argparse.Namespace) -> int:
    paths = build_paths()
    compose_command, _ = detect_docker_compose()
    stop_managed_processes()
    stop_infrastructure(paths, compose_command)
    return 0


def command_stop(args: argparse.Namespace) -> int:
    return command_down(args)


def tail_file(path: Path, lines: int = 120) -> str:
    if not path.exists():
        return ''
    data = path.read_text(encoding='utf-8', errors='replace').splitlines()
    return '\n'.join(data[-lines:])


def command_logs(args: argparse.Namespace) -> int:
    state = cleanup_state_file()
    processes = state.get('processes', [])
    if not processes:
        warn('No launcher-managed processes found in state. Start with `python start.py full` or `python start.py lite`.')
        return 0

    requested = (args.service or 'all').lower()
    allowed = {'all', 'backend', 'frontend', 'ollama', 'simulation loop'}
    if requested not in allowed:
        fail(f'Unsupported service for logs: {requested}. Use one of: {", ".join(sorted(allowed))}.')

    printed = 0
    for process in processes:
        label = str(process.get('label', '')).lower()
        if requested != 'all' and label != requested:
            continue
        log_file = process.get('log_file')
        if not log_file:
            warn(f'No log file tracked for {process.get("label", "process")} (mode: {process.get("mode", "unknown")}).')
            continue
        log_path = Path(log_file)
        print(f'\n=== {process.get("label", "process")} logs ({log_path}) ===')
        content = tail_file(log_path, lines=args.lines)
        if content:
            print(content)
        else:
            print('(log file is empty or missing)')
        printed += 1

    if printed == 0:
        warn('No matching logs were found for the requested service.')
    return 0


def command_seed(args: argparse.Namespace) -> int:
    paths = build_paths()
    ensure_project_structure(paths)
    mode = runtime_mode_from_args(args)
    if mode is LITE_MODE and not args.skip_infra:
        warn('Lite mode selected; forcing --skip-infra so Docker is not required.')
        args.skip_infra = True
    announce_runtime_mode(mode, skip_infra=args.skip_infra)
    prereqs = verify_prerequisites(require_node=False, require_docker=not args.skip_infra)
    ensure_env_files()
    if not args.skip_infra:
        start_infrastructure(paths, prereqs['docker_compose'])
    prepare_backend(paths, mode, skip_install=args.skip_install)
    run_seed(paths, mode)
    return 0


def command_simulate_tick(args: argparse.Namespace) -> int:
    paths = build_paths()
    ensure_project_structure(paths)
    mode = runtime_mode_from_args(args)
    if mode is LITE_MODE and not args.skip_infra:
        warn('Lite mode selected; forcing --skip-infra so Docker is not required.')
        args.skip_infra = True
    announce_runtime_mode(mode, skip_infra=args.skip_infra)
    prereqs = verify_prerequisites(require_node=False, require_docker=not args.skip_infra)
    ensure_env_files()
    if not args.skip_infra:
        start_infrastructure(paths, prereqs['docker_compose'])
    prepare_backend(paths, mode, skip_install=args.skip_install)
    run_backend_manage(paths, mode, ['simulate_markets_tick'])
    ok('Simulation tick completed.')
    return 0


def command_simulate_loop(args: argparse.Namespace) -> int:
    paths = build_paths()
    ensure_project_structure(paths)
    mode = runtime_mode_from_args(args)
    if mode is LITE_MODE and not args.skip_infra:
        warn('Lite mode selected; forcing --skip-infra so Docker is not required.')
        args.skip_infra = True
    announce_runtime_mode(mode, skip_infra=args.skip_infra)
    prereqs = verify_prerequisites(require_node=False, require_docker=not args.skip_infra)
    ensure_env_files()
    if not args.skip_infra:
        start_infrastructure(paths, prereqs['docker_compose'])
    prepare_backend(paths, mode, skip_install=args.skip_install)
    run_backend_manage(paths, mode, ['simulate_markets_loop'])
    ok('Simulation loop finished.')
    return 0


def command_backend(args: argparse.Namespace) -> int:
    paths = build_paths()
    ensure_project_structure(paths)
    ensure_no_running_launcher_processes()
    mode = runtime_mode_from_args(args)
    ollama_backend_enabled = resolve_ollama_backend_enabled(args, mode)
    backend_runtime_env = apply_ollama_backend_policy(
        launcher_runtime_env(paths, mode),
        enabled=ollama_backend_enabled,
    )
    if mode is LITE_MODE and not args.skip_infra:
        warn('Lite mode selected; forcing --skip-infra so Docker is not required.')
        args.skip_infra = True
    announce_runtime_mode(mode, skip_infra=args.skip_infra)
    prereqs = verify_prerequisites(require_node=False, require_docker=not args.skip_infra)
    ensure_env_files()
    if not args.skip_infra:
        start_infrastructure(paths, prereqs['docker_compose'])
    if ollama_backend_enabled and not args.skip_ollama:
        ollama_status, ollama_message = ensure_ollama_ready(timeout=args.ollama_timeout, managed_processes=[])
        info(f'Ollama check: {ollama_message}')
        if ollama_status != STATUS_OK:
            fail(ollama_message)
    elif ollama_backend_enabled:
        warn('Ollama backend enabled but --skip-ollama was used; readiness probe/startup skipped.')
    prepare_backend(paths, mode, skip_install=args.skip_install)
    if args.no_seed:
        warn('Skipping automatic seed for backend-only startup because --no-seed was used.')
    else:
        maybe_seed(paths, mode, no_seed=False)
    process_specs = [
        {
            'label': 'backend',
            'title': 'market-trading-bot backend',
            'command': backend_run_command(paths),
            'cwd': paths.backend,
            'env': backend_command_env(paths, mode, runtime_env=backend_runtime_env),
        }
    ]
    startup_mode = 'separate-windows' if args.separate_windows else DEFAULT_STARTUP_MODE
    verbose_logs = verbose_logging_enabled(args)
    attached_backend: subprocess.Popen[str] | None = None
    try:
        if verbose_logs and startup_mode != 'separate-windows':
            started_processes, attached_backend = start_dev_servers_verbose(process_specs)
            write_state_file(
                started_processes,
                startup_mode='verbose-console',
                browser_auto_open=False,
                browser_url=service_urls()['backend_health'],
                metadata={
                    'verbose_logging': True,
                    'backend_ollama_enabled': ollama_backend_enabled,
                    'backend_ollama_runtime_env': {
                        key: backend_runtime_env.get(key, 'unset')
                        for key in (
                            'OLLAMA_ENABLED',
                            'OLLAMA_BASE_URL',
                            'OLLAMA_MODEL',
                            'OLLAMA_TIMEOUT_SECONDS',
                            'OLLAMA_AUX_SIGNAL_ENABLED',
                            'LLM_PROVIDER',
                            'LLM_ENABLED',
                        )
                    },
                },
            )
            info('Verbose logging enabled: backend logs are attached to this terminal.')
        else:
            if verbose_logs and startup_mode == 'separate-windows':
                warn(
                    'Verbose logging is ignored with --separate-windows '
                    'because each service already has its own console.'
                )
            started_processes = start_dev_servers(
                process_specs,
                startup_mode=startup_mode,
                browser_auto_open=False,
                browser_url=service_urls()['backend_health'],
            )
            write_state_file(
                started_processes,
                startup_mode=startup_mode,
                browser_auto_open=False,
                browser_url=service_urls()['backend_health'],
                metadata={
                    'backend_ollama_enabled': ollama_backend_enabled,
                    'backend_ollama_runtime_env': {
                        key: backend_runtime_env.get(key, 'unset')
                        for key in (
                            'OLLAMA_ENABLED',
                            'OLLAMA_BASE_URL',
                            'OLLAMA_MODEL',
                            'OLLAMA_TIMEOUT_SECONDS',
                            'OLLAMA_AUX_SIGNAL_ENABLED',
                            'LLM_PROVIDER',
                            'LLM_ENABLED',
                        )
                    },
                },
            )
        wait_for_http(
            service_urls()['backend_health'],
            timeout=STARTUP_TIMEOUTS['backend_http'],
            label='Backend healthcheck',
        )
        print_launcher_summary(
            mode=mode,
            docker_status=STATUS_SKIPPED if args.skip_infra else STATUS_OK,
            ollama_status=STATUS_OK if ollama_backend_enabled else STATUS_SKIPPED,
            backend_status=STATUS_OK,
            frontend_status=STATUS_SKIPPED,
            browser_url=service_urls()['backend_health'],
            browser_opened=False,
            startup_mode=startup_mode,
            ollama_backend_status='ENABLED' if ollama_backend_enabled else 'DISABLED',
            ollama_runtime_env=backend_runtime_env,
        )
        ok(
            'Backend launched successfully in '
            f'{startup_mode} mode. Use `{"py" if os.name == "nt" else "python"} start.py down` to stop it.'
        )
        if attached_backend is not None:
            info('Backend is running in foreground for live logs. Press Ctrl+C to stop launcher-managed services.')
            attached_backend.wait()
            stop_managed_processes()
            if not args.skip_infra:
                stop_infrastructure(paths, prereqs['docker_compose'])
            return 0
        return 0
    except LauncherError:
        stop_managed_processes()
        raise


def command_frontend(args: argparse.Namespace) -> int:
    paths = build_paths()
    ensure_project_structure(paths)
    ensure_no_running_launcher_processes()
    mode = runtime_mode_from_args(args)
    announce_runtime_mode(mode, skip_infra=True)
    verify_prerequisites(require_node=True, require_docker=False)
    ensure_env_files()
    prepare_frontend(paths, skip_install=args.skip_install)
    process_specs = [
        {
            'label': 'frontend',
            'title': 'market-trading-bot frontend',
            'command': frontend_run_command(),
            'cwd': paths.frontend,
            'env': frontend_command_env(),
        }
    ]
    startup_mode = 'separate-windows' if args.separate_windows else DEFAULT_STARTUP_MODE
    try:
        start_dev_servers(
            process_specs,
            startup_mode=startup_mode,
            browser_auto_open=not args.no_browser,
            browser_url=service_urls()['frontend_system'],
        )
        wait_for_http(
            service_urls()['frontend_root'],
            timeout=STARTUP_TIMEOUTS['frontend_http'],
            label='Frontend dev server',
        )
        browser_opened = open_browser(service_urls()['frontend_system'], enabled=not args.no_browser)
        print_launcher_summary(
            mode=mode,
            docker_status=STATUS_SKIPPED,
            ollama_status=STATUS_SKIPPED,
            backend_status=STATUS_SKIPPED,
            frontend_status=STATUS_OK,
            browser_url=service_urls()['frontend_system'],
            browser_opened=browser_opened,
            startup_mode=startup_mode,
        )
        ok(
            'Frontend launched successfully in '
            f'{startup_mode} mode. Use `{"py" if os.name == "nt" else "python"} start.py down` to stop it.'
        )
        return 0
    except LauncherError:
        stop_managed_processes()
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Local-first launcher for the market-trading-bot monorepo.')
    parser.add_argument('--lite', action='store_true', help='Run in lite mode (SQLite, no Docker-required infra).')
    parser.add_argument('--no-browser', action='store_true', help='Do not open the browser automatically after startup.')
    parser.add_argument('--separate-windows', action='store_true', help='Open backend/frontend in separate console windows instead of detached mode.')
    parser.add_argument('--with-sim-loop', action='store_true', help='Start simulate_markets_loop alongside backend startup.')
    parser.add_argument('--skip-infra', action='store_true', help='Skip Docker Compose startup for postgres/redis.')
    parser.add_argument('--skip-ollama', action='store_true', help='Skip Ollama local startup/probe.')
    parser.add_argument('--ollama', choices=['enabled', 'disabled'], help='Control whether backend starts with Ollama env enabled.')
    parser.add_argument('--docker-timeout', type=float, default=DOCKER_DEFAULT_TIMEOUT_SECONDS, help='Max seconds to wait for Docker daemon readiness.')
    parser.add_argument('--ollama-timeout', type=float, default=OLLAMA_DEFAULT_TIMEOUT_SECONDS, help='Max seconds to wait for Ollama readiness.')
    parser.add_argument('--skip-seed', '--no-seed', dest='no_seed', action='store_true', help='Do not auto-run the demo seed.')
    parser.add_argument('--verbose', action='store_true', help='Attach backend logs to this terminal for paper-testing diagnostics.')
    subparsers = parser.add_subparsers(dest='command')

    common_setup = argparse.ArgumentParser(add_help=False)
    common_setup.add_argument('--skip-install', action='store_true', help='Skip pip/npm install steps.')
    common_setup.add_argument('--skip-backend', action='store_true', help='Skip backend preparation/startup.')
    common_setup.add_argument('--skip-frontend', action='store_true', help='Skip frontend preparation/startup.')
    common_setup.add_argument('--skip-infra', action='store_true', help='Skip Docker Compose startup for postgres/redis.')
    common_setup.add_argument('--skip-ollama', action='store_true', help='Skip Ollama local startup/probe.')
    common_setup.add_argument('--ollama', choices=['enabled', 'disabled'], help='Control whether backend starts with Ollama env enabled.')
    common_setup.add_argument('--docker-timeout', type=float, default=DOCKER_DEFAULT_TIMEOUT_SECONDS, help='Max seconds to wait for Docker daemon readiness.')
    common_setup.add_argument('--ollama-timeout', type=float, default=OLLAMA_DEFAULT_TIMEOUT_SECONDS, help='Max seconds to wait for Ollama readiness.')
    common_setup.add_argument('--skip-seed', '--no-seed', dest='no_seed', action='store_true', help='Do not auto-run the demo seed.')
    common_setup.add_argument('--lite', action='store_true', help='Run in lite mode (SQLite, no Docker-required infra).')
    common_setup.add_argument('--verbose', action='store_true', help='Attach backend logs to this terminal for paper-testing diagnostics.')

    backend_only = argparse.ArgumentParser(add_help=False)
    backend_only.add_argument('--skip-install', action='store_true', help='Skip pip install before running the command.')
    backend_only.add_argument('--skip-infra', action='store_true', help='Skip Docker Compose startup before running the command.')
    backend_only.add_argument('--separate-windows', action='store_true', help='Open the backend in a separate console window instead of detached mode.')
    backend_only.add_argument('--skip-seed', '--no-seed', dest='no_seed', action='store_true', help='Do not auto-run the demo seed before backend startup.')
    backend_only.add_argument('--lite', action='store_true', help='Run in lite mode (SQLite, no Docker-required infra).')
    backend_only.add_argument('--verbose', action='store_true', help='Attach backend logs to this terminal for paper-testing diagnostics.')
    backend_only.add_argument('--skip-ollama', action='store_true', help='Skip Ollama local startup/probe.')
    backend_only.add_argument('--ollama', choices=['enabled', 'disabled'], help='Control whether backend starts with Ollama env enabled.')

    frontend_only = argparse.ArgumentParser(add_help=False)
    frontend_only.add_argument('--skip-install', action='store_true', help='Skip npm install before running the command.')
    frontend_only.add_argument('--no-browser', action='store_true', help='Do not open the browser automatically after startup.')
    frontend_only.add_argument('--separate-windows', action='store_true', help='Open the frontend in a separate console window instead of detached mode.')
    frontend_only.add_argument('--lite', action='store_true', help='Run in lite mode (frontend still unchanged).')

    up_parser = subparsers.add_parser('up', parents=[common_setup], help='Prepare the project and start backend + frontend.')
    up_parser.add_argument('--with-sim-loop', action='store_true', help='Start simulate_markets_loop alongside the backend.')
    up_parser.add_argument('--no-browser', action='store_true', help='Do not open the browser automatically after startup.')
    up_parser.add_argument('--separate-windows', action='store_true', help='Open backend/frontend in separate console windows instead of detached mode.')
    up_parser.set_defaults(func=command_up)

    full_parser = subparsers.add_parser('full', parents=[common_setup], help='Windows-first full startup: Docker + Ollama + backend + frontend.')
    full_parser.add_argument('--with-sim-loop', action='store_true', help='Start simulate_markets_loop alongside the backend.')
    full_parser.add_argument('--no-browser', action='store_true', help='Do not open the browser automatically after startup.')
    full_parser.add_argument('--separate-windows', action='store_true', help='Open backend/frontend in separate console windows instead of detached mode.')
    full_parser.set_defaults(func=command_full)

    lite_parser = subparsers.add_parser('lite', parents=[common_setup], help='Lite startup: backend + frontend without Docker/Ollama.')
    lite_parser.add_argument('--with-sim-loop', action='store_true', help='Start simulate_markets_loop alongside the backend.')
    lite_parser.add_argument('--no-browser', action='store_true', help='Do not open the browser automatically after startup.')
    lite_parser.add_argument('--separate-windows', action='store_true', help='Open backend/frontend in separate console windows instead of detached mode.')
    lite_parser.set_defaults(func=command_lite)

    setup_parser = subparsers.add_parser('setup', parents=[common_setup], help='Prepare local dependencies without starting the servers.')
    setup_parser.set_defaults(func=command_setup)

    status_parser = subparsers.add_parser('status', help='Show a local environment summary for this repo.')
    status_parser.add_argument('--lite', action='store_true', help='Show status using lite-mode defaults.')
    status_parser.add_argument('--ollama', choices=['enabled', 'disabled'], help='Show status with Ollama backend policy enabled or disabled.')
    status_parser.set_defaults(func=command_status)

    down_parser = subparsers.add_parser('down', help='Stop launcher-managed processes and Docker Compose services.')
    down_parser.set_defaults(func=command_down)

    stop_parser = subparsers.add_parser('stop', help='Alias for down.')
    stop_parser.set_defaults(func=command_stop)

    logs_parser = subparsers.add_parser('logs', help='Show tail logs for launcher-managed services.')
    logs_parser.add_argument('--service', choices=['all', 'backend', 'frontend', 'ollama', 'simulation loop'], default='all', help='Service logs to display.')
    logs_parser.add_argument('--lines', type=int, default=120, help='How many lines to show from the end of each log.')
    logs_parser.set_defaults(func=command_logs)

    seed_parser = subparsers.add_parser('seed', parents=[backend_only], help='Run seed_markets_demo.')
    seed_parser.set_defaults(func=command_seed)

    tick_parser = subparsers.add_parser('simulate-tick', parents=[backend_only], help='Run simulate_markets_tick.')
    tick_parser.set_defaults(func=command_simulate_tick)

    loop_parser = subparsers.add_parser('simulate-loop', parents=[backend_only], help='Run simulate_markets_loop.')
    loop_parser.set_defaults(func=command_simulate_loop)

    backend_parser = subparsers.add_parser('backend', parents=[backend_only], help='Prepare and start only the Django backend.')
    backend_parser.set_defaults(func=command_backend)

    frontend_parser = subparsers.add_parser('frontend', parents=[frontend_only], help='Prepare and start only the Vite frontend.')
    frontend_parser.set_defaults(func=command_frontend)

    parser.set_defaults(
        command='up',
        func=command_up,
        skip_install=False,
        skip_backend=False,
        skip_frontend=False,
        no_seed=False,
        with_sim_loop=False,
        no_browser=False,
        separate_windows=False,
        skip_infra=False,
        skip_ollama=False,
        docker_timeout=DOCKER_DEFAULT_TIMEOUT_SECONDS,
        ollama_timeout=OLLAMA_DEFAULT_TIMEOUT_SECONDS,
        ollama=None,
        lite=False,
        verbose=False,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return int(args.func(args))
    except LauncherError as exc:
        print(f'[ERROR] {exc}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
