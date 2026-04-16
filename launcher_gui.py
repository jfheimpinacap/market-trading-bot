from __future__ import annotations

import json
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
import tkinter.messagebox as messagebox

import customtkinter as ctk


ROOT = Path(__file__).resolve().parent
START_SCRIPT = ROOT / 'start.py'
STATUS_KEYS = ('Docker', 'Ollama service', 'Ollama backend', 'Backend', 'Frontend')
STATUS_DEFAULT = 'OFF'
PREFERENCES_FILE = ROOT / '.tmp' / 'launcher-gui-preferences.json'
DEFAULT_SYSTEM_URL = 'http://localhost:5173/system'


class LauncherGUI(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.preferences = self._load_preferences()
        self.title('Market Trading Bot — Launcher local')
        self.geometry(str(self.preferences.get('window_geometry', '720x540')))
        self.minsize(680, 500)
        self.protocol('WM_DELETE_WINDOW', self._on_close)

        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('blue')

        self.status_labels: dict[str, ctk.CTkLabel] = {}
        self.action_buttons: list[ctk.CTkButton] = []
        self.feedback_var = ctk.StringVar(value='Listo para iniciar.')
        self.last_status_check_var = ctk.StringVar(value='Última revisión: pendiente')
        self.main_url_var = ctk.StringVar(value='URL principal: no disponible')
        self.auto_open_browser_var = ctk.BooleanVar(value=bool(self.preferences.get('auto_open_browser', True)))
        self.use_ollama_var = ctk.BooleanVar(value=bool(self.preferences.get('use_ollama', True)))
        self.dashboard_button: ctk.CTkButton | None = None

        self._build_ui()
        self.after(600, self._save_preferences)
        self.refresh_status()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, corner_radius=14)
        header.grid(row=0, column=0, padx=20, pady=(20, 12), sticky='ew')
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text='Launcher local de Market Trading Bot',
            font=ctk.CTkFont(size=22, weight='bold'),
        ).grid(row=0, column=0, padx=16, pady=(16, 4), sticky='w')
        ctk.CTkLabel(
            header,
            text='Fachada visual para ejecutar start.py (full / lite / status / logs / stop).',
            font=ctk.CTkFont(size=13),
            text_color='gray80',
        ).grid(row=1, column=0, padx=16, pady=(0, 16), sticky='w')

        body = ctk.CTkFrame(self, corner_radius=14)
        body.grid(row=1, column=0, padx=20, pady=0, sticky='nsew')
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        actions = ctk.CTkFrame(body, corner_radius=12)
        actions.grid(row=0, column=0, padx=(14, 8), pady=14, sticky='nsew')
        actions.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            actions,
            text='Arranque rápido',
            font=ctk.CTkFont(size=17, weight='bold'),
        ).pack(anchor='w', padx=14, pady=(12, 2))

        self._add_action_button(actions, 'Iniciar sistema completo (full)', lambda: self.run_action('full'))
        self._add_action_button(actions, 'Iniciar modo liviano (lite)', lambda: self.run_action('lite'))
        self._add_action_button(actions, 'Iniciar último modo usado', self.run_last_mode)
        self._add_action_button(actions, 'Actualizar estado ahora', self.refresh_status)
        self._add_action_button(actions, 'Abrir logs', self.open_logs)
        self._add_action_button(actions, 'Detener servicios', lambda: self.run_action('stop'))
        self.dashboard_button = self._add_action_button(
            actions,
            'Abrir Dashboard',
            self.open_dashboard,
            state='disabled',
        )

        ctk.CTkCheckBox(
            actions,
            text='Abrir navegador automáticamente al iniciar',
            variable=self.auto_open_browser_var,
            command=self._save_preferences,
            font=ctk.CTkFont(size=13),
        ).pack(anchor='w', padx=16, pady=(8, 4))
        ctk.CTkCheckBox(
            actions,
            text='Usar Ollama (shadow + señal auxiliar)',
            variable=self.use_ollama_var,
            command=self._save_preferences,
            font=ctk.CTkFont(size=13),
        ).pack(anchor='w', padx=16, pady=(4, 4))

        ctk.CTkLabel(
            actions,
            textvariable=self.main_url_var,
            font=ctk.CTkFont(size=12),
            text_color='gray80',
            wraplength=390,
            justify='left',
        ).pack(anchor='w', padx=16, pady=(4, 10))

        self._add_action_button(actions, 'Salir', self.destroy, fg_color='#3c3c3c', hover_color='#4a4a4a')

        status_box = ctk.CTkFrame(body, corner_radius=12)
        status_box.grid(row=0, column=1, padx=(8, 14), pady=14, sticky='nsew')
        status_box.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            status_box,
            text='Estado rápido',
            font=ctk.CTkFont(size=18, weight='bold'),
        ).grid(row=0, column=0, columnspan=2, padx=14, pady=(14, 10), sticky='w')

        for i, name in enumerate(STATUS_KEYS, start=1):
            ctk.CTkLabel(status_box, text=f'{name}:', font=ctk.CTkFont(size=14, weight='bold')).grid(
                row=i,
                column=0,
                padx=(14, 8),
                pady=8,
                sticky='w',
            )
            value = ctk.CTkLabel(status_box, text=STATUS_DEFAULT, font=ctk.CTkFont(size=14), text_color='#f5a524')
            value.grid(row=i, column=1, padx=(0, 14), pady=8, sticky='w')
            self.status_labels[name] = value

        ctk.CTkLabel(
            status_box,
            textvariable=self.last_status_check_var,
            font=ctk.CTkFont(size=12),
            text_color='gray80',
            wraplength=250,
            justify='left',
        ).grid(row=len(STATUS_KEYS) + 1, column=0, columnspan=2, padx=14, pady=(8, 14), sticky='w')

        footer = ctk.CTkFrame(self, corner_radius=14)
        footer.grid(row=2, column=0, padx=20, pady=(12, 20), sticky='ew')
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            footer,
            textvariable=self.feedback_var,
            wraplength=660,
            justify='left',
            anchor='w',
            font=ctk.CTkFont(size=13),
        ).grid(row=0, column=0, padx=14, pady=12, sticky='ew')

    def _add_action_button(self, parent: ctk.CTkFrame, text: str, command, **kwargs: object) -> ctk.CTkButton:
        button = ctk.CTkButton(
            parent,
            text=text,
            command=command,
            height=46,
            corner_radius=10,
            font=ctk.CTkFont(size=15, weight='bold'),
            **kwargs,
        )
        button.pack(fill='x', padx=12, pady=8)
        self.action_buttons.append(button)
        return button

    def _run_start_command(self, *args: str) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(START_SCRIPT), *args]
        return subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def run_action(self, action: str) -> None:
        feedback_text = {
            'full': 'Iniciando sistema completo... puede tardar unos minutos.',
            'lite': 'Iniciando modo lite... preparando backend y frontend.',
            'stop': 'Deteniendo servicios del launcher...',
        }.get(action, f'Ejecutando {action}...')

        if action == 'full':
            self._set_transitional_status(
                {
                    'Docker': 'STARTING',
                    'Ollama service': 'STARTING' if self.use_ollama_var.get() else 'OFF',
                    'Ollama backend': 'ENABLED' if self.use_ollama_var.get() else 'DISABLED',
                    'Backend': 'STARTING',
                    'Frontend': 'STARTING',
                }
            )
        elif action == 'lite':
            self._set_transitional_status(
                {
                    'Ollama service': 'STARTING' if self.use_ollama_var.get() else 'OFF',
                    'Ollama backend': 'ENABLED' if self.use_ollama_var.get() else 'DISABLED',
                    'Backend': 'STARTING',
                    'Frontend': 'STARTING',
                }
            )

        command_args = [action]
        if action in {'full', 'lite'} and not self.auto_open_browser_var.get():
            command_args.append('--no-browser')
        if action in {'full', 'lite'}:
            command_args.extend(['--ollama', 'enabled' if self.use_ollama_var.get() else 'disabled'])
        if action in {'full', 'lite'}:
            self.preferences['last_mode'] = action
        self._save_preferences()
        self._run_background(action, feedback_text, *command_args)

    def refresh_status(self) -> None:
        self._run_background('status', 'Revisando estado de servicios...', 'status')

    def open_logs(self) -> None:
        self._set_busy(True)
        self.feedback_var.set('Abriendo logs del launcher...')

        def worker() -> None:
            result = self._run_start_command('logs')
            self.after(0, lambda: self._on_logs_ready(result))

        threading.Thread(target=worker, daemon=True).start()

    def _on_logs_ready(self, result: subprocess.CompletedProcess[str]) -> None:
        self._set_busy(False)
        if result.returncode != 0:
            error_output = (result.stderr or result.stdout or 'Error desconocido').strip()
            self.feedback_var.set('No fue posible abrir logs.')
            messagebox.showerror('Error en logs', error_output)
            return

        logs_window = ctk.CTkToplevel(self)
        logs_window.title('Logs del launcher (start.py logs)')
        logs_window.geometry('900x560')
        logs_window.grid_columnconfigure(0, weight=1)
        logs_window.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            logs_window,
            text='Salida de `start.py logs`',
            font=ctk.CTkFont(size=16, weight='bold'),
        ).grid(row=0, column=0, padx=16, pady=(14, 8), sticky='w')

        textbox = ctk.CTkTextbox(logs_window, corner_radius=10)
        textbox.grid(row=1, column=0, padx=16, pady=(0, 16), sticky='nsew')
        output = (result.stdout or '').strip() or 'No hay logs disponibles todavía.'
        textbox.insert('1.0', output)
        textbox.configure(state='disabled')
        self.feedback_var.set('Logs cargados correctamente.')

    def _run_background(self, action: str, feedback: str, *command_args: str) -> None:
        self._set_busy(True)
        self.feedback_var.set(feedback)

        def worker() -> None:
            run_args = command_args or (action,)
            result = self._run_start_command(*run_args)
            self.after(0, lambda: self._on_action_done(action, result))

        threading.Thread(target=worker, daemon=True).start()

    def _on_action_done(self, action: str, result: subprocess.CompletedProcess[str]) -> None:
        self._set_busy(False)

        if result.returncode != 0:
            error_output = (result.stderr or result.stdout or 'Error desconocido').strip()
            self.feedback_var.set(f'Error al ejecutar `{action}`.')
            messagebox.showerror('Error del launcher', error_output)
            self.refresh_status()
            return

        if action == 'status':
            self._update_status_from_output(result.stdout)
            self.feedback_var.set('Estado actualizado correctamente.')
            return

        success_messages = {
            'full': 'Sistema completo iniciado. Revisa el estado y abre Dashboard cuando esté en OK.',
            'lite': 'Modo lite iniciado. Revisa el estado y abre Dashboard cuando esté en OK.',
            'stop': 'Servicios detenidos por el launcher.',
        }
        status_url = self._extract_primary_url(result.stdout or '')
        if status_url:
            self.main_url_var.set(f'URL principal: {status_url}')
        self.feedback_var.set(success_messages.get(action, f'Comando `{action}` completado.'))
        self.refresh_status()

    def _set_busy(self, busy: bool) -> None:
        state = 'disabled' if busy else 'normal'
        for button in self.action_buttons:
            button.configure(state=state)

    def _set_transitional_status(self, partial_status: dict[str, str]) -> None:
        for service, value in partial_status.items():
            if service in self.status_labels:
                self._paint_status(self.status_labels[service], value)

    def _update_status_from_output(self, output: str) -> None:
        parsed = {name: STATUS_DEFAULT for name in STATUS_KEYS}
        primary_url = self._extract_primary_url(output) or DEFAULT_SYSTEM_URL

        for raw_line in output.splitlines():
            line = raw_line.strip()
            for key in STATUS_KEYS:
                prefix = f'{key}:'
                if line.startswith(prefix):
                    token = line[len(prefix):].strip().split(' ', 1)[0].upper()
                    parsed[key] = self._normalize_status(token)

        for key, value in parsed.items():
            self._paint_status(self.status_labels[key], value)
        can_open_dashboard = parsed.get('Frontend') == 'OK'
        self.main_url_var.set(f'URL principal: {primary_url if can_open_dashboard else "no disponible (frontend OFF)"}')
        if self.dashboard_button is not None:
            self.dashboard_button.configure(state='normal' if can_open_dashboard else 'disabled')
        self.last_status_check_var.set(f'Última revisión: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

    @staticmethod
    def _normalize_status(status: str) -> str:
        if status in {'OK', 'STARTING', 'FAILED', 'OFF', 'ENABLED', 'DISABLED'}:
            return status
        return 'OFF'

    @staticmethod
    def _paint_status(label: ctk.CTkLabel, status: str) -> None:
        colors = {
            'OK': '#27ae60',
            'STARTING': '#f5a524',
            'FAILED': '#d7263d',
            'OFF': '#e74c3c',
            'ENABLED': '#27ae60',
            'DISABLED': '#e74c3c',
        }
        label.configure(text=status, text_color=colors.get(status, '#e74c3c'))

    def _extract_primary_url(self, output: str) -> str | None:
        for raw_line in output.splitlines():
            line = raw_line.strip()
            if line.startswith('Primary URL:'):
                value = line.split(':', 1)[1].strip()
                return value or None
            if line.startswith('System page:'):
                value = line.split(':', 1)[1].strip()
                return value or None
        return None

    def open_dashboard(self) -> None:
        status_text = self.main_url_var.get()
        if ':' not in status_text:
            messagebox.showinfo('Dashboard no disponible', 'No hay una URL principal disponible todavía.')
            return
        url = status_text.split(':', 1)[1].strip()
        if not url.startswith('http'):
            messagebox.showinfo('Dashboard no disponible', 'La URL principal aún no está disponible.')
            return
        if webbrowser.open(url, new=2):
            self.feedback_var.set(f'Se abrió el dashboard en tu navegador: {url}')
        else:
            self.feedback_var.set('No se pudo abrir el navegador automáticamente.')

    def run_last_mode(self) -> None:
        last_mode = str(self.preferences.get('last_mode', 'full')).lower().strip()
        mode = last_mode if last_mode in {'full', 'lite'} else 'full'
        self.run_action(mode)

    def _load_preferences(self) -> dict[str, object]:
        if not PREFERENCES_FILE.exists():
            return {'last_mode': 'full', 'auto_open_browser': True, 'use_ollama': True}
        try:
            loaded = json.loads(PREFERENCES_FILE.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            return {'last_mode': 'full', 'auto_open_browser': True, 'use_ollama': True}
        if not isinstance(loaded, dict):
            return {'last_mode': 'full', 'auto_open_browser': True, 'use_ollama': True}
        loaded.setdefault('last_mode', 'full')
        loaded.setdefault('auto_open_browser', True)
        loaded.setdefault('use_ollama', True)
        return loaded

    def _save_preferences(self) -> None:
        self.preferences['window_geometry'] = self.geometry()
        self.preferences['auto_open_browser'] = bool(self.auto_open_browser_var.get())
        self.preferences['use_ollama'] = bool(self.use_ollama_var.get())
        PREFERENCES_FILE.parent.mkdir(parents=True, exist_ok=True)
        PREFERENCES_FILE.write_text(json.dumps(self.preferences, indent=2), encoding='utf-8')

    def _on_close(self) -> None:
        self._save_preferences()
        self.destroy()


if __name__ == '__main__':
    if not START_SCRIPT.exists():
        raise SystemExit('No se encontró start.py en la raíz del proyecto.')

    app = LauncherGUI()
    app.mainloop()
