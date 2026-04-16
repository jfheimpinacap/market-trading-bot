from __future__ import annotations

import subprocess
import sys
import threading
from pathlib import Path
import tkinter.messagebox as messagebox

import customtkinter as ctk


ROOT = Path(__file__).resolve().parent
START_SCRIPT = ROOT / 'start.py'
STATUS_KEYS = ('Docker', 'Ollama', 'Backend', 'Frontend')
STATUS_DEFAULT = 'OFF'


class LauncherGUI(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title('Market Trading Bot — Launcher local')
        self.geometry('720x540')
        self.minsize(680, 500)

        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('blue')

        self.status_labels: dict[str, ctk.CTkLabel] = {}
        self.action_buttons: list[ctk.CTkButton] = []
        self.feedback_var = ctk.StringVar(value='Listo para iniciar.')

        self._build_ui()
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
            text='Interfaz visual para ejecutar start.py (full / lite / status / logs / stop).',
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

        self._add_action_button(actions, 'Iniciar sistema completo', lambda: self.run_action('full'))
        self._add_action_button(actions, 'Inicio lite', lambda: self.run_action('lite'))
        self._add_action_button(actions, 'Revisar estado de servicios', self.refresh_status)
        self._add_action_button(actions, 'Abrir logs', self.open_logs)
        self._add_action_button(actions, 'Detener servicios', lambda: self.run_action('stop'))
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

    def _add_action_button(self, parent: ctk.CTkFrame, text: str, command, **kwargs: object) -> None:
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
            self._set_transitional_status({'Docker': 'STARTING', 'Ollama': 'STARTING', 'Backend': 'STARTING', 'Frontend': 'STARTING'})
        elif action == 'lite':
            self._set_transitional_status({'Backend': 'STARTING', 'Frontend': 'STARTING'})

        self._run_background(action, feedback_text)

    def refresh_status(self) -> None:
        self._run_background('status', 'Revisando estado de servicios...')

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

    def _run_background(self, action: str, feedback: str) -> None:
        self._set_busy(True)
        self.feedback_var.set(feedback)

        def worker() -> None:
            result = self._run_start_command(action)
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
            'full': 'Sistema completo iniciado. Verifica el estado para confirmar servicios.',
            'lite': 'Modo lite iniciado. Verifica el estado para confirmar servicios.',
            'stop': 'Servicios detenidos por el launcher.',
        }
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
        for raw_line in output.splitlines():
            line = raw_line.strip()
            for key in STATUS_KEYS:
                prefix = f'{key}:'
                if line.startswith(prefix):
                    token = line[len(prefix) :].strip().split(' ', 1)[0].upper()
                    parsed[key] = self._normalize_status(token)

        for key, value in parsed.items():
            self._paint_status(self.status_labels[key], value)

    @staticmethod
    def _normalize_status(status: str) -> str:
        if status in {'OK', 'STARTING'}:
            return status
        return 'OFF'

    @staticmethod
    def _paint_status(label: ctk.CTkLabel, status: str) -> None:
        colors = {
            'OK': '#27ae60',
            'STARTING': '#f5a524',
            'OFF': '#e74c3c',
        }
        label.configure(text=status, text_color=colors.get(status, '#e74c3c'))


if __name__ == '__main__':
    if not START_SCRIPT.exists():
        raise SystemExit('No se encontró start.py en la raíz del proyecto.')

    app = LauncherGUI()
    app.mainloop()
