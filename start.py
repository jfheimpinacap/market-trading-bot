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
    print(f"[INFO] {message}")


def ok(message: str) -> None:
    print(f"[OK] {message}")


def warn(message: str) -> None:
    print(f"[WARN] {message}")


def fail(message: str) -> None:
    raise LauncherError(message)


def run_command(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    capture_output: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(command),
            cwd=cwd,
            env=env,
            check=check,
            text=True,
            capture_output=capture_output,
        )
    except FileNotFoundError as exc:
        fail(f"Command not found: {command[0]}")
    except subprocess.CalledProcessError as exc:
        if capture_output:
            output = '\n'.join(part for part in [exc.stdout, exc.stderr] if part).strip()
            detail = f"\n{output}" if output else ''
            fail(f"Command failed ({' '.join(command)}).{detail}")
        fail(f"Command failed ({' '.join(command)}).")


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
            'Repository structure is incomplete. Missing: ' + ', '.join(missing)
        )


def find_executable(name: str) -> str | None:
    return shutil.which(name)


def is_valid_python_interpreter(command: str) -> bool:
    try:
        result = subprocess.run(
            [command, '--version'],
            check=False,
            text=True,
            capture_output=True,
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


def command_version(command: Sequence[str]) -> str:
    result = run_command(command, capture_output=True, check=False)
    output = '\n'.join(part for part in [result.stdout, result.stderr] if part).strip()
    return output.splitlines()[0] if output else 'available'


def detect_docker_compose() -> list[str] | None:
    docker = find_executable('docker')
    if docker:
        result = subprocess.run(
            [docker, 'compose', 'version'],
            check=False,
            text=True,
            capture_output=True,
        )
        if result.returncode == 0:
            return [docker, 'compose']

    docker_compose = find_executable('docker-compose')
    if docker_compose:
        return [docker_compose]
    return None


def verify_prerequisites(*, require_node: bool, require_docker: bool) -> dict[str, Any]:
    python = resolve_python_interpreter()
    if python is None:
        fail('Python is required but no valid interpreter was found. Try running this launcher with py, python, or python3.')

    node_path = find_executable('node')
    npm_path = find_executable('npm')
    if require_node and (not node_path or not npm_path):
        fail('Node.js and npm are required for the frontend but were not found in PATH.')

    compose_command = detect_docker_compose()
    if require_docker and compose_command is None:
        fail('Docker Compose is required to start PostgreSQL and Redis, but neither docker compose nor docker-compose was found.')

    return {
        'python': python.command,
        'python_source': python.source,
        'node': node_path,
        'npm': npm_path,
        'docker_compose': compose_command,
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

    interpreter = resolve_python_interpreter()
    if interpreter is None:
        fail('Python is required to create the backend virtual environment. Try running this launcher with py, python, or python3.')

    info('Creating backend virtual environment...')
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


def ensure_frontend_dependencies(paths: ProjectPaths, *, skip_install: bool) -> None:
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

    if node_modules.exists() and installed_hash == package_hash:
        ok('Frontend dependencies already installed.')
        return

    info('Installing frontend dependencies with npm install...')
    run_command(['npm', 'install'], cwd=paths.frontend)
    node_modules.mkdir(parents=True, exist_ok=True)
    stamp.write_text(package_hash, encoding='utf-8')
    ok('Frontend dependencies installed.')


def backend_command_env(paths: ProjectPaths) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
    env.setdefault('PYTHONUNBUFFERED', '1')
    return env


def run_backend_manage(paths: ProjectPaths, args: Sequence[str], *, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    venv_python = get_backend_venv_python(paths)
    if not venv_python.exists():
        fail('Backend virtual environment is missing. Run python start.py setup first.')
    return run_command(
        [str(venv_python), str(paths.backend_manage), *args],
        cwd=paths.backend,
        env=backend_command_env(paths),
        capture_output=capture_output,
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
    ensure_frontend_dependencies(paths, skip_install=skip_install)


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


def process_kwargs() -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if os.name == 'nt':
        kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
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
    info(f"Starting {label}: {' '.join(command)}")
    return subprocess.Popen(list(command), cwd=cwd, env=env, text=True, **process_kwargs())


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
                os.kill(pid, signal.SIGTERM)
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


def command_up(args: argparse.Namespace) -> int:
    paths = build_paths()
    ensure_project_structure(paths)
    prereqs = verify_prerequisites(
        require_node=not args.skip_frontend,
        require_docker=True,
    )
    ensure_env_files()
    start_infrastructure(paths, prereqs['docker_compose'])

    backend_process: subprocess.Popen[str] | None = None
    frontend_process: subprocess.Popen[str] | None = None
    sim_process: subprocess.Popen[str] | None = None
    processes: list[dict[str, Any]] = []

    try:
        if not args.skip_backend:
            prepare_backend(paths, skip_install=args.skip_install)
            maybe_seed(paths, no_seed=args.no_seed)
            backend_process = spawn_process(
                'backend',
                [str(get_backend_venv_python(paths)), str(paths.backend_manage), 'runserver', '0.0.0.0:8000'],
                cwd=paths.backend,
                env=backend_command_env(paths),
            )
            processes.append({'label': 'backend', 'pid': backend_process.pid, 'command': 'runserver'})
        else:
            warn('Skipping backend preparation and startup.')

        if not args.skip_frontend:
            prepare_frontend(paths, skip_install=args.skip_install)
            frontend_process = spawn_process(
                'frontend',
                ['npm', 'run', 'dev', '--', '--host', '0.0.0.0', '--port', str(DEFAULT_PORTS['frontend'])],
                cwd=paths.frontend,
            )
            processes.append({'label': 'frontend', 'pid': frontend_process.pid, 'command': 'npm run dev'})
        else:
            warn('Skipping frontend preparation and startup.')

        if args.with_sim_loop:
            if args.skip_backend:
                warn('Simulation loop was requested, but backend startup is skipped, so the loop was not started.')
            else:
                sim_process = spawn_process(
                    'simulation loop',
                    [str(get_backend_venv_python(paths)), str(paths.backend_manage), 'simulate_markets_loop'],
                    cwd=paths.backend,
                    env=backend_command_env(paths),
                )
                processes.append({'label': 'simulation loop', 'pid': sim_process.pid, 'command': 'simulate_markets_loop'})

        if processes:
            write_state_file(processes)

        print_urls()
        info('Launcher is running. Press Ctrl+C to stop backend/frontend child processes.')

        while True:
            for label, process in [('backend', backend_process), ('frontend', frontend_process), ('simulation loop', sim_process)]:
                if process is not None:
                    code = process.poll()
                    if code is not None:
                        fail(f'{label} exited unexpectedly with code {code}.')
            time.sleep(1)
    except KeyboardInterrupt:
        warn('Received Ctrl+C. Stopping launcher-managed processes...')
    finally:
        stop_managed_processes()
    return 0


def command_setup(args: argparse.Namespace) -> int:
    paths = build_paths()
    ensure_project_structure(paths)
    prereqs = verify_prerequisites(
        require_node=not args.skip_frontend,
        require_docker=not args.skip_infra,
    )
    ensure_env_files()
    if not args.skip_infra:
        start_infrastructure(paths, prereqs['docker_compose'])
    if not args.skip_backend:
        prepare_backend(paths, skip_install=args.skip_install)
        maybe_seed(paths, no_seed=args.no_seed)
    else:
        warn('Skipping backend setup.')
    if not args.skip_frontend:
        prepare_frontend(paths, skip_install=args.skip_install)
    else:
        warn('Skipping frontend setup.')
    print_urls()
    ok('Setup completed. Use python start.py up when you want to start the servers.')
    return 0


def command_status(_: argparse.Namespace) -> int:
    paths = build_paths()
    ensure_project_structure(paths)
    compose_command = detect_docker_compose()
    python = resolve_python_interpreter()
    node_path = find_executable('node')
    npm_path = find_executable('npm')
    root_env_values = parse_env_file(paths.root_env)

    backend_status = 'OK' if paths.backend.exists() else 'MISSING'
    frontend_status = 'OK' if paths.frontend.exists() else 'MISSING'
    python_version = command_version([python.command, '--version']) if python else 'MISSING'
    node_version = command_version([node_path, '--version']) if node_path else 'MISSING'
    npm_version = command_version([npm_path, '--version']) if npm_path else 'MISSING'

    print('=== market-trading-bot local status ===')
    print(f'Repo root:      {paths.root}')
    print(f'Backend dir:    {backend_status} -> {paths.backend}')
    print(f'Frontend dir:   {frontend_status} -> {paths.frontend}')
    print(f'Docker compose: {" ".join(compose_command) if compose_command else "MISSING"}')
    print(f'Python:         {python_version}')
    print(f'Current interpreter: {python.command if python else "MISSING"}')
    print(f'Python source:  {python.source if python else "not detected"}')
    print(f'Node:           {node_version}')
    print(f'npm:            {npm_version}')
    print('')
    print('Environment files:')
    print(f'  root .env:         {"present" if paths.root_env.exists() else "missing"}')
    print(f'  backend .env:      {"present" if paths.backend_env.exists() else "missing"}')
    print(f'  frontend .env:     {"present" if paths.frontend_env.exists() else "missing"}')
    print('')
    print('Dependency state:')
    print(f'  backend .venv:     {"present" if (paths.backend / ".venv").exists() else "missing"}')
    print(f'  frontend node_modules: {"present" if (paths.frontend / "node_modules").exists() else "missing"}')
    print('')
    print('Expected local ports:')
    print(f"  backend:   {DEFAULT_PORTS['backend']}")
    print(f"  frontend:  {DEFAULT_PORTS['frontend']}")
    print(f"  postgres:  {root_env_values.get('POSTGRES_PORT', str(DEFAULT_PORTS['postgres']))}")
    print(f"  redis:     {root_env_values.get('REDIS_PORT', str(DEFAULT_PORTS['redis']))}")
    print('')
    print('Recommended commands:')
    print('  python start.py setup')
    print('  python start.py up')
    print('  python start.py seed')
    print('  python start.py simulate-tick')
    print('  python start.py simulate-loop')
    print('  python start.py down')
    print('')
    print_urls(root_env_values)
    if PATHS.state_file.exists():
        print(f'Launcher state file: present at {PATHS.state_file}')
    else:
        print('Launcher state file: not present')
    return 0


def command_down(_: argparse.Namespace) -> int:
    paths = build_paths()
    compose_command = detect_docker_compose()
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Local-first launcher for the market-trading-bot monorepo.',
    )
    subparsers = parser.add_subparsers(dest='command')

    common_setup = argparse.ArgumentParser(add_help=False)
    common_setup.add_argument('--skip-install', action='store_true', help='Skip pip/npm install steps.')
    common_setup.add_argument('--skip-backend', action='store_true', help='Skip backend preparation.')
    common_setup.add_argument('--skip-frontend', action='store_true', help='Skip frontend preparation.')
    common_setup.add_argument('--no-seed', action='store_true', help='Do not auto-run the demo seed.')

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

    backend_only = argparse.ArgumentParser(add_help=False)
    backend_only.add_argument('--skip-install', action='store_true', help='Skip pip install before running the command.')
    backend_only.add_argument('--skip-infra', action='store_true', help='Skip Docker Compose startup before running the command.')

    seed_parser = subparsers.add_parser('seed', parents=[backend_only], help='Run seed_markets_demo.')
    seed_parser.set_defaults(func=command_seed)

    tick_parser = subparsers.add_parser('simulate-tick', parents=[backend_only], help='Run simulate_markets_tick.')
    tick_parser.set_defaults(func=command_simulate_tick)

    loop_parser = subparsers.add_parser('simulate-loop', parents=[backend_only], help='Run simulate_markets_loop.')
    loop_parser.set_defaults(func=command_simulate_loop)

    parser.set_defaults(command='up', func=command_up, skip_install=False, skip_backend=False, skip_frontend=False, no_seed=False, with_sim_loop=False)
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
