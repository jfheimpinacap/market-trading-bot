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


def info(message: str) -> None:
    print(f'[INFO] {message}')


def ok(message: str) -> None:
    print(f'[OK] {message}')


def warn(message: str) -> None:
    print(f'[WARN] {message}')


def fail(message: str) -> None:
    raise LauncherError(message)


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


def backend_command_env(paths: ProjectPaths) -> dict[str, str]:
    _ = paths
    return subprocess_env(
        {
            'DJANGO_SETTINGS_MODULE': os.environ.get('DJANGO_SETTINGS_MODULE', 'config.settings.local'),
        }
    )


def frontend_command_env() -> dict[str, str]:
    return subprocess_env()


def run_backend_manage(
    paths: ProjectPaths,
    args: Sequence[str],
    *,
    capture_output: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    venv_python = get_backend_venv_python(paths)
    if not venv_python.exists():
        fail('Backend virtual environment is missing. Run python start.py setup first.')
    return run_command(
        [str(venv_python), str(paths.backend_manage), *args],
        cwd=paths.backend,
        env=backend_command_env(paths),
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


def start_infrastructure(paths: ProjectPaths, compose_command: Sequence[str]) -> None:
    root_env = parse_env_file(paths.root_env)
    postgres_port = int(root_env.get('POSTGRES_PORT', DEFAULT_PORTS['postgres']))
    redis_port = int(root_env.get('REDIS_PORT', DEFAULT_PORTS['redis']))

    info('Starting PostgreSQL and Redis with Docker Compose...')
    run_command([*compose_command, 'up', '-d', 'postgres', 'redis'], cwd=paths.root)
    wait_for_port('127.0.0.1', postgres_port, timeout=45, label='PostgreSQL')
    wait_for_port('127.0.0.1', redis_port, timeout=30, label='Redis')


def stop_infrastructure(paths: ProjectPaths, compose_command: Sequence[str] | None) -> None:
    if compose_command is None:
        warn('Docker Compose is not available; skipping infrastructure shutdown.')
        return

    info('Stopping Docker Compose services...')
    run_command([*compose_command, 'down'], cwd=paths.root)
    ok('Docker Compose services stopped.')


def prepare_backend(paths: ProjectPaths, *, skip_install: bool) -> Path:
    info('Preparing backend...')
    venv_python = ensure_backend_dependencies(paths, skip_install=skip_install)
    info('Running backend migrations...')
    run_backend_manage(paths, ['migrate'])
    ok('Backend migrations completed.')
    return venv_python


def prepare_frontend(paths: ProjectPaths, *, skip_install: bool) -> None:
    info('Preparing frontend...')
    ensure_frontend_deps(paths, skip_install=skip_install)


def prepare_dev_environment(
    paths: ProjectPaths,
    *,
    skip_backend: bool,
    skip_frontend: bool,
    skip_install: bool,
    no_seed: bool,
) -> None:
    if not skip_backend:
        prepare_backend(paths, skip_install=skip_install)
        maybe_seed(paths, no_seed=no_seed)
    else:
        warn('Skipping backend preparation.')

    if not skip_frontend:
        prepare_frontend(paths, skip_install=skip_install)
    else:
        warn('Skipping frontend preparation.')


def should_seed_demo(paths: ProjectPaths) -> bool:
    result = run_backend_manage(
        paths,
        ['shell', '-c', 'from apps.markets.models import Market; print("yes" if Market.objects.exists() else "no")'],
        capture_output=True,
    )
    status = result.stdout.strip().splitlines()[-1].strip().lower() if result.stdout.strip() else 'no'
    return status != 'yes'


def run_seed(paths: ProjectPaths) -> None:
    info('Running demo seed...')
    run_backend_manage(paths, ['seed_markets_demo'])
    ok('Demo market seed completed.')


def maybe_seed(paths: ProjectPaths, *, no_seed: bool) -> None:
    if no_seed:
        warn('Skipping demo seed because --no-seed was used.')
        return

    if should_seed_demo(paths):
        info('No market data detected, running demo seed automatically...')
        run_seed(paths)
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


def write_state_file(processes: list[dict[str, Any]]) -> None:
    PATHS.state_dir.mkdir(parents=True, exist_ok=True)
    PATHS.state_file.write_text(json.dumps({'processes': processes}, indent=2), encoding='utf-8')


def remove_state_file() -> None:
    if PATHS.state_file.exists():
        PATHS.state_file.unlink()


def spawn_process(label: str, command: Sequence[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.Popen[str]:
    info(f"Starting {label}: {' '.join(str(part) for part in command)}")
    return subprocess.Popen(
        [str(part) for part in command],
        cwd=cwd,
        env=subprocess_env(env),
        **process_kwargs(),
    )


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
    if not PATHS.state_file.exists():
        warn('No launcher-managed process state file was found.')
        return

    state = json.loads(PATHS.state_file.read_text(encoding='utf-8'))
    for process in state.get('processes', []):
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
    remove_state_file()


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


def backend_run_command(paths: ProjectPaths) -> list[str]:
    return [str(get_backend_venv_python(paths)), str(paths.backend_manage), 'runserver', '0.0.0.0:8000']


def frontend_run_command() -> list[str]:
    return [npm_exec(), 'run', 'dev', '--', '--host', '0.0.0.0', '--port', str(DEFAULT_PORTS['frontend'])]


def build_dev_process_specs(
    paths: ProjectPaths,
    *,
    include_backend: bool,
    include_frontend: bool,
    with_sim_loop: bool,
) -> list[dict[str, Any]]:
    process_specs: list[dict[str, Any]] = []
    if include_backend:
        process_specs.append(
            {
                'label': 'backend',
                'title': 'market-trading-bot backend',
                'command': backend_run_command(paths),
                'cwd': paths.backend,
                'env': backend_command_env(paths),
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
                'env': backend_command_env(paths),
            }
        )
    return process_specs


def start_dev_servers(process_specs: Sequence[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[tuple[str, subprocess.Popen[str]]]]:
    if os.name == 'nt':
        launched = open_new_console_windows(process_specs)
        write_state_file(launched)
        return launched, []

    processes: list[dict[str, Any]] = []
    live_processes: list[tuple[str, subprocess.Popen[str]]] = []
    for spec in process_specs:
        process = spawn_process(spec['label'], spec['command'], spec['cwd'], env=spec.get('env'))
        live_processes.append((spec['label'], process))
        processes.append(
            {
                'label': spec['label'],
                'pid': process.pid,
                'command': ' '.join(str(part) for part in spec['command']),
                'cwd': str(spec['cwd']),
                'mode': 'background-process',
            }
        )
    write_state_file(processes)
    return processes, live_processes


def command_up(args: argparse.Namespace) -> int:
    paths = build_paths()
    ensure_project_structure(paths)
    prereqs = verify_prerequisites(require_node=not args.skip_frontend, require_docker=True)
    ensure_env_files()
    start_infrastructure(paths, prereqs['docker_compose'])

    try:
        prepare_dev_environment(
            paths,
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
            include_backend=include_backend,
            include_frontend=include_frontend,
            with_sim_loop=args.with_sim_loop and include_backend,
        )

        started_processes: list[dict[str, Any]] = []
        live_processes: list[tuple[str, subprocess.Popen[str]]] = []
        if process_specs:
            started_processes, live_processes = start_dev_servers(process_specs)
        else:
            warn('Both backend and frontend startup were skipped; nothing was started.')

        print_urls()
        if os.name == 'nt' and started_processes:
            ok('Windows mode: backend/frontend were launched in separate console windows.')
            info('Use `python start.py down` from the repo root to stop launcher-managed processes and Docker services.')
            return 0

        if started_processes:
            info('Launcher is running. Press Ctrl+C to stop backend/frontend child processes.')
            while True:
                for label, process in live_processes:
                    code = process.poll()
                    if code is not None:
                        fail(f'{label} exited unexpectedly with code {code}.')
                time.sleep(1)
        return 0
    except KeyboardInterrupt:
        warn('Received Ctrl+C. Stopping launcher-managed processes...')
    finally:
        if os.name != 'nt':
            stop_managed_processes()
    return 0


def command_setup(args: argparse.Namespace) -> int:
    paths = build_paths()
    ensure_project_structure(paths)
    prereqs = verify_prerequisites(require_node=not args.skip_frontend, require_docker=not args.skip_infra)
    ensure_env_files()
    if not args.skip_infra:
        start_infrastructure(paths, prereqs['docker_compose'])
    prepare_dev_environment(
        paths,
        skip_backend=args.skip_backend,
        skip_frontend=args.skip_frontend,
        skip_install=args.skip_install,
        no_seed=args.no_seed,
    )
    print_urls()
    ok('Setup completed. Use python start.py up when you want to start the servers.')
    return 0


def command_status(_: argparse.Namespace) -> int:
    paths = build_paths()
    ensure_project_structure(paths)
    python = resolve_python_interpreter()
    node_tooling = inspect_node_tooling()
    compose_command, compose_mode = detect_docker_compose()
    root_env_values = parse_env_file(paths.root_env)
    backend_venv_python = get_backend_venv_python(paths)
    docker_found = shutil.which('docker') is not None

    print('=== market-trading-bot local status ===')
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
    print(f"  Docker Compose mode:   {compose_mode}")
    print(f"  Docker Compose command:{' ' + ' '.join(compose_command) if compose_command else ' not found'}")
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
    print(f"  postgres:              {root_env_values.get('POSTGRES_PORT', str(DEFAULT_PORTS['postgres']))}")
    print(f"  redis:                 {root_env_values.get('REDIS_PORT', str(DEFAULT_PORTS['redis']))}")
    print_urls(root_env_values)
    print('')
    print('Recommended commands:')
    print('  python start.py status')
    print('  python start.py setup')
    print('  python start.py up')
    print('  python start.py seed')
    print('  python start.py simulate-tick')
    print('  python start.py simulate-loop')
    print('  python start.py down')
    print('')
    if PATHS.state_file.exists():
        print(f'Launcher state file:     present at {PATHS.state_file}')
    else:
        print('Launcher state file:     not present')
    return 0


def command_down(_: argparse.Namespace) -> int:
    paths = build_paths()
    compose_command, _ = detect_docker_compose()
    stop_managed_processes()
    stop_infrastructure(paths, compose_command)
    return 0


def command_seed(args: argparse.Namespace) -> int:
    paths = build_paths()
    ensure_project_structure(paths)
    prereqs = verify_prerequisites(require_node=False, require_docker=not args.skip_infra)
    ensure_env_files()
    if not args.skip_infra:
        start_infrastructure(paths, prereqs['docker_compose'])
    prepare_backend(paths, skip_install=args.skip_install)
    run_seed(paths)
    return 0


def command_simulate_tick(args: argparse.Namespace) -> int:
    paths = build_paths()
    ensure_project_structure(paths)
    prereqs = verify_prerequisites(require_node=False, require_docker=not args.skip_infra)
    ensure_env_files()
    if not args.skip_infra:
        start_infrastructure(paths, prereqs['docker_compose'])
    prepare_backend(paths, skip_install=args.skip_install)
    run_backend_manage(paths, ['simulate_markets_tick'])
    ok('Simulation tick completed.')
    return 0


def command_simulate_loop(args: argparse.Namespace) -> int:
    paths = build_paths()
    ensure_project_structure(paths)
    prereqs = verify_prerequisites(require_node=False, require_docker=not args.skip_infra)
    ensure_env_files()
    if not args.skip_infra:
        start_infrastructure(paths, prereqs['docker_compose'])
    prepare_backend(paths, skip_install=args.skip_install)
    run_backend_manage(paths, ['simulate_markets_loop'])
    ok('Simulation loop finished.')
    return 0


def command_backend(args: argparse.Namespace) -> int:
    paths = build_paths()
    ensure_project_structure(paths)
    prereqs = verify_prerequisites(require_node=False, require_docker=not args.skip_infra)
    ensure_env_files()
    if not args.skip_infra:
        start_infrastructure(paths, prereqs['docker_compose'])
    prepare_backend(paths, skip_install=args.skip_install)
    if args.no_seed:
        warn('Skipping automatic seed for backend-only startup because --no-seed was used.')
    else:
        maybe_seed(paths, no_seed=False)
    if os.name == 'nt':
        launched = open_new_console_windows(
            [
                {
                    'label': 'backend',
                    'title': 'market-trading-bot backend',
                    'command': backend_run_command(paths),
                    'cwd': paths.backend,
                    'env': backend_command_env(paths),
                }
            ]
        )
        write_state_file(launched)
        print_urls()
        ok('Windows mode: backend launched in a separate console window.')
        return 0

    process = spawn_process('backend', backend_run_command(paths), paths.backend, env=backend_command_env(paths))
    write_state_file([
        {
            'label': 'backend',
            'pid': process.pid,
            'command': ' '.join(backend_run_command(paths)),
            'cwd': str(paths.backend),
            'mode': 'background-process',
        }
    ])
    info('Backend is running. Press Ctrl+C to stop it.')
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        warn('Received Ctrl+C. Stopping backend...')
    finally:
        stop_managed_processes()
    return 0


def command_frontend(args: argparse.Namespace) -> int:
    paths = build_paths()
    ensure_project_structure(paths)
    verify_prerequisites(require_node=True, require_docker=False)
    ensure_env_files()
    prepare_frontend(paths, skip_install=args.skip_install)
    if os.name == 'nt':
        launched = open_new_console_windows(
            [
                {
                    'label': 'frontend',
                    'title': 'market-trading-bot frontend',
                    'command': frontend_run_command(),
                    'cwd': paths.frontend,
                    'env': frontend_command_env(),
                }
            ]
        )
        write_state_file(launched)
        print_urls()
        ok('Windows mode: frontend launched in a separate console window.')
        return 0

    process = spawn_process('frontend', frontend_run_command(), paths.frontend, env=frontend_command_env())
    write_state_file([
        {
            'label': 'frontend',
            'pid': process.pid,
            'command': ' '.join(frontend_run_command()),
            'cwd': str(paths.frontend),
            'mode': 'background-process',
        }
    ])
    info('Frontend is running. Press Ctrl+C to stop it.')
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        warn('Received Ctrl+C. Stopping frontend...')
    finally:
        stop_managed_processes()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Local-first launcher for the market-trading-bot monorepo.')
    subparsers = parser.add_subparsers(dest='command')

    common_setup = argparse.ArgumentParser(add_help=False)
    common_setup.add_argument('--skip-install', action='store_true', help='Skip pip/npm install steps.')
    common_setup.add_argument('--skip-backend', action='store_true', help='Skip backend preparation/startup.')
    common_setup.add_argument('--skip-frontend', action='store_true', help='Skip frontend preparation/startup.')
    common_setup.add_argument('--no-seed', action='store_true', help='Do not auto-run the demo seed.')

    backend_only = argparse.ArgumentParser(add_help=False)
    backend_only.add_argument('--skip-install', action='store_true', help='Skip pip install before running the command.')
    backend_only.add_argument('--skip-infra', action='store_true', help='Skip Docker Compose startup before running the command.')
    backend_only.add_argument('--no-seed', action='store_true', help='Do not auto-run the demo seed before backend startup.')

    frontend_only = argparse.ArgumentParser(add_help=False)
    frontend_only.add_argument('--skip-install', action='store_true', help='Skip npm install before running the command.')

    up_parser = subparsers.add_parser('up', parents=[common_setup], help='Prepare the project and start backend + frontend.')
    up_parser.add_argument('--with-sim-loop', action='store_true', help='Start simulate_markets_loop alongside the backend.')
    up_parser.set_defaults(func=command_up)

    setup_parser = subparsers.add_parser('setup', parents=[common_setup], help='Prepare local dependencies without starting the servers.')
    setup_parser.add_argument('--skip-infra', action='store_true', help='Skip Docker Compose startup for postgres/redis.')
    setup_parser.set_defaults(func=command_setup)

    status_parser = subparsers.add_parser('status', help='Show a local environment summary for this repo.')
    status_parser.set_defaults(func=command_status)

    down_parser = subparsers.add_parser('down', help='Stop launcher-managed processes and Docker Compose services.')
    down_parser.set_defaults(func=command_down)

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
