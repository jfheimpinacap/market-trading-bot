from __future__ import annotations

import json
import os
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
BACKEND_DIR = ROOT / 'apps' / 'backend'
BACKEND_MANAGE_SCRIPT = BACKEND_DIR / 'manage.py'
BACKEND_VENV_PYTHON_WINDOWS = BACKEND_DIR / '.venv' / 'Scripts' / 'python.exe'
BACKEND_VENV_PYTHON_POSIX = BACKEND_DIR / '.venv' / 'bin' / 'python'
STATUS_KEYS = ('Docker', 'Ollama service', 'Ollama backend', 'Backend', 'Frontend')
STATUS_DEFAULT = 'OFF'
PREFERENCES_FILE = ROOT / '.tmp' / 'launcher-gui-preferences.json'
DEFAULT_SYSTEM_URL = 'http://localhost:5173/system'
OLLAMA_TIMEOUT_OPTIONS = ('30', '60', '90', '120')
DEFAULT_OLLAMA_BASE_URL = 'http://127.0.0.1:11434'
DEFAULT_OLLAMA_MODEL = 'llama3.2:3b'
DEFAULT_WINDOW_WIDTH = 940
DEFAULT_WINDOW_HEIGHT = 700
DEFAULT_MIN_WIDTH = 820
DEFAULT_MIN_HEIGHT = 620
WINDOW_MARGIN_X = 80
WINDOW_MARGIN_Y = 120
RESIZE_LAYOUT_DEBOUNCE_MS = 120
LOG_PANEL_POLL_MS = 2500
LOG_PANEL_LINES = 80
LOG_PANEL_SERVICES = ('backend', 'frontend')


class LauncherGUI(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.preferences = self._load_preferences()
        self.title('Market Trading Bot — Launcher local')
        self._configure_window_geometry()
        self.protocol('WM_DELETE_WINDOW', self._on_close)

        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('blue')

        self.status_labels: dict[str, ctk.CTkLabel] = {}
        self.action_buttons: list[ctk.CTkButton] = []
        self.feedback_var = ctk.StringVar(value='Listo para iniciar.')
        self.last_status_check_var = ctk.StringVar(value='Última revisión: pendiente')
        self.main_url_var = ctk.StringVar(value='URL principal: no disponible')
        self.auto_open_browser_var = ctk.BooleanVar(value=bool(self.preferences.get('auto_open_browser', True)))
        self.debug_visible_processes_var = ctk.BooleanVar(value=bool(self.preferences.get('debug_visible_processes', False)))
        self.use_ollama_var = ctk.BooleanVar(value=bool(self.preferences.get('use_ollama', True)))
        self.aux_signal_var = ctk.BooleanVar(value=bool(self.preferences.get('aux_signal_enabled', False)))
        self.ollama_base_url_var = ctk.StringVar(value=str(self.preferences.get('ollama_base_url', DEFAULT_OLLAMA_BASE_URL)))
        self.ollama_model_var = ctk.StringVar(value=str(self.preferences.get('ollama_model', DEFAULT_OLLAMA_MODEL)))
        timeout_value = str(self.preferences.get('ollama_timeout_seconds', '90')).strip()
        if timeout_value not in OLLAMA_TIMEOUT_OPTIONS:
            timeout_value = '90'
        self.ollama_timeout_var = ctk.StringVar(value=timeout_value)
        self.dashboard_button: ctk.CTkButton | None = None
        self.main_url_label: ctk.CTkLabel | None = None
        self.footer_feedback_label: ctk.CTkLabel | None = None
        self._resize_layout_job: str | None = None
        self.logs_panel_frame: ctk.CTkFrame | None = None
        self.logs_tabview: ctk.CTkTabview | None = None
        self.logs_textboxes: dict[str, ctk.CTkTextbox] = {}
        self.logs_panel_visible = False
        self.logs_autoscroll_var = ctk.BooleanVar(value=True)
        self._logs_poll_job: str | None = None
        self._logs_refresh_inflight = False
        self._logs_cache: dict[str, str] = {service: '' for service in LOG_PANEL_SERVICES}
        self._action_button_groups: list[tuple[ctk.CTkFrame, list[ctk.CTkButton], int]] = []

        self._build_ui()
        self.bind('<Configure>', self._on_window_configure)
        self.after(250, self._apply_responsive_layout)
        self.after(600, self._save_preferences)
        self.refresh_status()

    @staticmethod
    def _clamp(value: int, minimum: int, maximum: int) -> int:
        if minimum > maximum:
            return minimum
        return max(minimum, min(value, maximum))

    @staticmethod
    def _parse_geometry(geometry: str) -> tuple[int, int, int | None, int | None] | None:
        value = (geometry or '').strip()
        if not value:
            return None
        if 'x' not in value:
            return None
        size_part, _, position_part = value.partition('+')
        width_str, _, height_str = size_part.partition('x')
        if not width_str.isdigit() or not height_str.isdigit():
            return None
        width = int(width_str)
        height = int(height_str)
        if width <= 0 or height <= 0:
            return None
        x_value: int | None = None
        y_value: int | None = None
        if position_part:
            x_str, _, y_str = position_part.partition('+')
            if x_str.isdigit() and y_str.isdigit():
                x_value = int(x_str)
                y_value = int(y_str)
        return width, height, x_value, y_value

    def _configure_window_geometry(self) -> None:
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        usable_w = max(640, screen_w - WINDOW_MARGIN_X)
        usable_h = max(560, screen_h - WINDOW_MARGIN_Y)

        min_w = min(DEFAULT_MIN_WIDTH, usable_w)
        min_h = min(DEFAULT_MIN_HEIGHT, usable_h)
        self.minsize(min_w, min_h)

        saved_geometry = str(self.preferences.get('window_geometry', '')).strip()
        parsed_geometry = self._parse_geometry(saved_geometry)

        if parsed_geometry is None:
            width = self._clamp(DEFAULT_WINDOW_WIDTH, min_w, usable_w)
            height = self._clamp(DEFAULT_WINDOW_HEIGHT, min_h, usable_h)
            x = max(0, (screen_w - width) // 2)
            y = max(0, (screen_h - height) // 2)
            self.geometry(f'{width}x{height}+{x}+{y}')
            return

        raw_w, raw_h, raw_x, raw_y = parsed_geometry
        width = self._clamp(raw_w, min_w, usable_w)
        height = self._clamp(raw_h, min_h, usable_h)
        max_x = max(0, screen_w - width)
        max_y = max(0, screen_h - height)

        if raw_x is None or raw_y is None:
            x = max(0, (screen_w - width) // 2)
            y = max(0, (screen_h - height) // 2)
        else:
            x = self._clamp(raw_x, 0, max_x)
            y = self._clamp(raw_y, 0, max_y)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

        header = ctk.CTkFrame(self, corner_radius=14)
        header.grid(row=0, column=0, padx=20, pady=(20, 12), sticky='ew')
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text='Launcher local de Market Trading Bot',
            font=ctk.CTkFont(size=20, weight='bold'),
        ).grid(row=0, column=0, padx=16, pady=(16, 4), sticky='w')
        ctk.CTkLabel(
            header,
            text='Control local compacto para start.py (full/lite/status/logs/stop).',
            font=ctk.CTkFont(size=12),
            text_color='gray80',
        ).grid(row=1, column=0, padx=16, pady=(0, 16), sticky='w')

        body = ctk.CTkFrame(self, corner_radius=14)
        body.grid(row=1, column=0, padx=20, pady=0, sticky='nsew')
        body.grid_columnconfigure(0, weight=7)
        body.grid_columnconfigure(1, weight=4)
        body.grid_rowconfigure(0, weight=1)

        actions = ctk.CTkScrollableFrame(body, corner_radius=12)
        actions.grid(row=0, column=0, padx=(14, 8), pady=14, sticky='nsew')
        actions.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(actions, text='Arranque del sistema', font=ctk.CTkFont(size=15, weight='bold')).grid(
            row=0, column=0, padx=12, pady=(10, 2), sticky='w'
        )
        startup_group = ctk.CTkFrame(actions, corner_radius=10)
        startup_group.grid(row=1, column=0, padx=10, pady=(0, 8), sticky='ew')
        startup_buttons = [
            self._add_action_button(startup_group, 'Iniciar completo', lambda: self.run_action('full'), primary=True),
            self._add_action_button(startup_group, 'Iniciar lite', lambda: self.run_action('lite'), primary=True),
            self._add_action_button(startup_group, 'Repetir último inicio', self.run_last_mode, primary=True),
        ]
        self._register_action_button_group(startup_group, startup_buttons, max_columns=3)

        ctk.CTkLabel(actions, text='Servicios individuales', font=ctk.CTkFont(size=15, weight='bold')).grid(
            row=2, column=0, padx=12, pady=(4, 2), sticky='w'
        )
        services_group = ctk.CTkFrame(actions, corner_radius=10)
        services_group.grid(row=3, column=0, padx=10, pady=(0, 8), sticky='ew')
        services_buttons = [
            self._add_action_button(services_group, 'Solo backend', lambda: self.run_action('backend')),
            self._add_action_button(services_group, 'Solo frontend', lambda: self.run_action('frontend')),
            self._add_action_button(services_group, 'Revisar estado', self.refresh_status),
            self._add_action_button(services_group, 'Detener servicios', lambda: self.run_action('stop')),
        ]
        self._register_action_button_group(services_group, services_buttons, max_columns=2)

        ctk.CTkLabel(actions, text='Logs y monitoreo', font=ctk.CTkFont(size=15, weight='bold')).grid(
            row=4, column=0, padx=12, pady=(4, 2), sticky='w'
        )
        monitor_group = ctk.CTkFrame(actions, corner_radius=10)
        monitor_group.grid(row=5, column=0, padx=10, pady=(0, 8), sticky='ew')
        self.dashboard_button = self._add_action_button(
            monitor_group, 'Abrir dashboard', self.open_dashboard, state='disabled'
        )
        monitor_buttons = [
            self.dashboard_button,
            self._add_action_button(monitor_group, 'Panel interno logs', self.toggle_logs_panel),
            self._add_action_button(monitor_group, 'Logs backend', lambda: self.show_logs_panel('backend')),
            self._add_action_button(monitor_group, 'Logs frontend', lambda: self.show_logs_panel('frontend')),
            self._add_action_button(monitor_group, 'Logs Ollama', lambda: self.open_logs('ollama')),
        ]
        self._register_action_button_group(monitor_group, monitor_buttons, max_columns=3)

        ctk.CTkLabel(actions, text='Preferencias y debug', font=ctk.CTkFont(size=15, weight='bold')).grid(
            row=6, column=0, padx=12, pady=(4, 2), sticky='w'
        )
        preferences_group = ctk.CTkFrame(actions, corner_radius=10)
        preferences_group.grid(row=7, column=0, padx=10, pady=(0, 10), sticky='ew')
        preferences_group.grid_columnconfigure(0, weight=1)
        preferences_group.grid_columnconfigure(1, weight=1)

        ctk.CTkCheckBox(
            preferences_group,
            text='Abrir navegador al iniciar',
            variable=self.auto_open_browser_var,
            command=self._save_preferences,
            font=ctk.CTkFont(size=12),
        ).grid(row=0, column=0, padx=12, pady=(8, 2), sticky='w')
        ctk.CTkCheckBox(
            preferences_group,
            text='Modo debug (consolas visibles)',
            variable=self.debug_visible_processes_var,
            command=self._save_preferences,
            font=ctk.CTkFont(size=12),
        ).grid(row=0, column=1, padx=12, pady=(8, 2), sticky='w')
        ctk.CTkCheckBox(
            preferences_group,
            text='Usar Ollama (shadow)',
            variable=self.use_ollama_var,
            command=self._save_preferences,
            font=ctk.CTkFont(size=12),
        ).grid(row=1, column=0, padx=12, pady=(2, 2), sticky='w')
        ctk.CTkCheckBox(
            preferences_group,
            text='Señal auxiliar LLM',
            variable=self.aux_signal_var,
            command=self._save_preferences,
            font=ctk.CTkFont(size=12),
        ).grid(row=1, column=1, padx=12, pady=(2, 2), sticky='w')

        timeout_row = ctk.CTkFrame(preferences_group, fg_color='transparent')
        timeout_row.grid(row=2, column=0, padx=12, pady=(2, 4), sticky='ew')
        ctk.CTkLabel(
            timeout_row,
            text='Timeout Ollama (s):',
            font=ctk.CTkFont(size=12),
        ).pack(side='left')
        timeout_selector = ctk.CTkOptionMenu(
            timeout_row,
            values=list(OLLAMA_TIMEOUT_OPTIONS),
            variable=self.ollama_timeout_var,
            width=90,
            height=30,
            command=lambda _: self._save_preferences(),
        )
        timeout_selector.pack(side='left', padx=(8, 0))

        model_row = ctk.CTkFrame(preferences_group, fg_color='transparent')
        model_row.grid(row=2, column=1, padx=12, pady=(2, 4), sticky='ew')
        ctk.CTkLabel(
            model_row,
            text='Modelo Ollama:',
            font=ctk.CTkFont(size=12),
        ).pack(side='left')
        model_entry = ctk.CTkEntry(model_row, textvariable=self.ollama_model_var, height=30)
        model_entry.pack(side='left', padx=(8, 0), fill='x', expand=True)
        model_entry.bind('<FocusOut>', lambda _: self._save_preferences())

        base_url_row = ctk.CTkFrame(preferences_group, fg_color='transparent')
        base_url_row.grid(row=3, column=0, columnspan=2, padx=12, pady=(2, 4), sticky='ew')
        ctk.CTkLabel(
            base_url_row,
            text='Base URL Ollama:',
            font=ctk.CTkFont(size=12),
        ).pack(side='left')
        base_url_entry = ctk.CTkEntry(base_url_row, textvariable=self.ollama_base_url_var, height=30)
        base_url_entry.pack(side='left', padx=(8, 0), fill='x', expand=True)
        base_url_entry.bind('<FocusOut>', lambda _: self._save_preferences())

        preferences_buttons_group = ctk.CTkFrame(preferences_group, fg_color='transparent')
        preferences_buttons_group.grid(row=4, column=0, columnspan=2, padx=6, pady=(2, 6), sticky='ew')
        pref_buttons = [
            self._add_action_button(preferences_buttons_group, 'Smoke test Ollama', self.run_llm_shadow_smoke_test),
            self._add_action_button(
                preferences_buttons_group, 'Salir launcher', self.destroy, fg_color='#3c3c3c', hover_color='#4a4a4a'
            ),
        ]
        self._register_action_button_group(preferences_buttons_group, pref_buttons, max_columns=2)

        self.main_url_label = ctk.CTkLabel(
            preferences_group,
            textvariable=self.main_url_var,
            font=ctk.CTkFont(size=11),
            text_color='gray80',
            wraplength=460,
            justify='left',
        )
        self.main_url_label.grid(row=5, column=0, columnspan=2, padx=12, pady=(0, 8), sticky='w')

        status_box = ctk.CTkFrame(body, corner_radius=12)
        status_box.grid(row=0, column=1, padx=(8, 14), pady=14, sticky='nsew')
        status_box.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            status_box,
            text='Estado rápido',
            font=ctk.CTkFont(size=16, weight='bold'),
        ).grid(row=0, column=0, columnspan=2, padx=14, pady=(14, 10), sticky='w')

        for i, name in enumerate(STATUS_KEYS, start=1):
            ctk.CTkLabel(status_box, text=f'{name}:', font=ctk.CTkFont(size=13, weight='bold')).grid(
                row=i,
                column=0,
                padx=(14, 8),
                pady=6,
                sticky='w',
            )
            value = ctk.CTkLabel(status_box, text=STATUS_DEFAULT, font=ctk.CTkFont(size=13), text_color='#f5a524')
            value.grid(row=i, column=1, padx=(0, 14), pady=6, sticky='w')
            self.status_labels[name] = value

        ctk.CTkLabel(
            status_box,
            textvariable=self.last_status_check_var,
            font=ctk.CTkFont(size=11),
            text_color='gray80',
            wraplength=250,
            justify='left',
        ).grid(row=len(STATUS_KEYS) + 1, column=0, columnspan=2, padx=14, pady=(8, 14), sticky='w')

        self.logs_panel_frame = self._build_logs_panel()
        self.logs_panel_frame.grid(row=2, column=0, padx=20, pady=(0, 12), sticky='nsew')
        self.logs_panel_frame.grid_remove()

        footer = ctk.CTkFrame(self, corner_radius=14)
        footer.grid(row=3, column=0, padx=20, pady=(0, 20), sticky='ew')
        footer.grid_columnconfigure(0, weight=1)
        self.footer_feedback_label = ctk.CTkLabel(
            footer,
            textvariable=self.feedback_var,
            wraplength=660,
            justify='left',
            anchor='w',
            font=ctk.CTkFont(size=13),
        )
        self.footer_feedback_label.grid(row=0, column=0, padx=14, pady=12, sticky='ew')

    def _on_window_configure(self, event) -> None:
        if event.widget is not self:
            return
        if self._resize_layout_job is not None:
            self.after_cancel(self._resize_layout_job)
        self._resize_layout_job = self.after(RESIZE_LAYOUT_DEBOUNCE_MS, self._apply_responsive_layout)

    def _apply_responsive_layout(self) -> None:
        self._resize_layout_job = None
        width = max(self.winfo_width(), DEFAULT_MIN_WIDTH)
        # Nota técnica: este ajuste desacoplado de layout mantiene la lógica de UI concentrada
        # y facilita una futura migración gradual a otro toolkit (por ejemplo PySide6) sin
        # mezclar lógica de procesos/startup con el framework gráfico.
        if self.main_url_label is not None:
            self.main_url_label.configure(wraplength=max(320, width - 560))
        if self.footer_feedback_label is not None:
            self.footer_feedback_label.configure(wraplength=max(500, width - 300))
        columns = 3 if width >= 1220 else 2
        for frame, buttons, max_columns in self._action_button_groups:
            target_columns = max(1, min(columns, max_columns))
            self._layout_action_button_group(frame, buttons, target_columns)

    @staticmethod
    def _layout_action_button_group(
        frame: ctk.CTkFrame,
        buttons: list[ctk.CTkButton],
        columns: int,
    ) -> None:
        for idx in range(columns):
            frame.grid_columnconfigure(idx, weight=1)
        for index, button in enumerate(buttons):
            row = index // columns
            column = index % columns
            button.grid(row=row, column=column, padx=6, pady=5, sticky='ew')

    def _register_action_button_group(
        self,
        frame: ctk.CTkFrame,
        buttons: list[ctk.CTkButton],
        max_columns: int,
    ) -> None:
        self._action_button_groups.append((frame, buttons, max_columns))

    def _build_logs_panel(self) -> ctk.CTkFrame:
        panel = ctk.CTkFrame(self, corner_radius=14)
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(panel, fg_color='transparent')
        header.grid(row=0, column=0, padx=12, pady=(10, 6), sticky='ew')
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header,
            text='Logs en launcher (últimas líneas)',
            font=ctk.CTkFont(size=15, weight='bold'),
        ).grid(row=0, column=0, padx=(4, 10), sticky='w')
        ctk.CTkCheckBox(
            header,
            text='Auto-scroll',
            variable=self.logs_autoscroll_var,
            font=ctk.CTkFont(size=12),
        ).grid(row=0, column=1, sticky='e')
        ctk.CTkButton(header, text='Actualizar', width=90, height=30, command=self.refresh_logs_panel_once).grid(
            row=0, column=2, padx=(8, 0), sticky='e'
        )
        ctk.CTkButton(header, text='Limpiar', width=80, height=30, command=self.clear_current_log_tab).grid(
            row=0, column=3, padx=(8, 0), sticky='e'
        )
        ctk.CTkButton(header, text='Copiar', width=80, height=30, command=self.copy_current_log_tab).grid(
            row=0, column=4, padx=(8, 0), sticky='e'
        )
        ctk.CTkButton(header, text='Ocultar', width=80, height=30, command=self.hide_logs_panel).grid(
            row=0, column=5, padx=(8, 2), sticky='e'
        )

        self.logs_tabview = ctk.CTkTabview(panel, corner_radius=10)
        self.logs_tabview.grid(row=1, column=0, padx=12, pady=(0, 12), sticky='nsew')
        for service in LOG_PANEL_SERVICES:
            tab = self.logs_tabview.add(service.capitalize())
            tab.grid_rowconfigure(0, weight=1)
            tab.grid_columnconfigure(0, weight=1)
            textbox = ctk.CTkTextbox(tab, corner_radius=8)
            textbox.grid(row=0, column=0, sticky='nsew')
            textbox.insert('1.0', f'Sin datos todavía para {service}.')
            self.logs_textboxes[service] = textbox
        return panel

    def toggle_logs_panel(self) -> None:
        if self.logs_panel_visible:
            self.hide_logs_panel()
            return
        self.show_logs_panel()

    def show_logs_panel(self, preferred_service: str | None = None) -> None:
        if self.logs_panel_frame is None:
            return
        self.logs_panel_frame.grid()
        self.logs_panel_visible = True
        if preferred_service in LOG_PANEL_SERVICES and self.logs_tabview is not None:
            self.logs_tabview.set(preferred_service.capitalize())
        self.refresh_logs_panel_once()
        self._schedule_logs_poll()

    def hide_logs_panel(self) -> None:
        if self.logs_panel_frame is not None:
            self.logs_panel_frame.grid_remove()
        self.logs_panel_visible = False
        if self._logs_poll_job is not None:
            self.after_cancel(self._logs_poll_job)
            self._logs_poll_job = None

    def _schedule_logs_poll(self) -> None:
        if not self.logs_panel_visible:
            return
        if self._logs_poll_job is not None:
            self.after_cancel(self._logs_poll_job)
        self._logs_poll_job = self.after(LOG_PANEL_POLL_MS, self._poll_logs_panel)

    def _poll_logs_panel(self) -> None:
        self._logs_poll_job = None
        self.refresh_logs_panel_once()
        self._schedule_logs_poll()

    def refresh_logs_panel_once(self) -> None:
        if not self.logs_panel_visible or self._logs_refresh_inflight:
            return
        self._logs_refresh_inflight = True

        def worker() -> None:
            outputs: dict[str, str] = {}
            errors: list[str] = []
            for service in LOG_PANEL_SERVICES:
                result = self._run_start_command('logs', '--service', service, '--lines', str(LOG_PANEL_LINES))
                if result.returncode == 0:
                    outputs[service] = (result.stdout or '').strip() or f'No hay logs para {service}.'
                else:
                    errors.append(service)
                    outputs[service] = (result.stderr or result.stdout or f'Error leyendo logs de {service}.').strip()
            self.after(0, lambda: self._on_logs_panel_polled(outputs, errors))

        threading.Thread(target=worker, daemon=True).start()

    def _on_logs_panel_polled(self, outputs: dict[str, str], errors: list[str]) -> None:
        self._logs_refresh_inflight = False
        for service, content in outputs.items():
            if self._logs_cache.get(service) == content:
                continue
            self._logs_cache[service] = content
            textbox = self.logs_textboxes.get(service)
            if textbox is None:
                continue
            textbox.delete('1.0', 'end')
            textbox.insert('1.0', content)
            if self.logs_autoscroll_var.get():
                textbox.see('end')
        if errors:
            self.feedback_var.set(f'Logs parciales: no se pudieron leer {", ".join(errors)}.')

    def _current_logs_service(self) -> str:
        if self.logs_tabview is None:
            return 'backend'
        current = self.logs_tabview.get().strip().lower()
        return current if current in LOG_PANEL_SERVICES else 'backend'

    def clear_current_log_tab(self) -> None:
        service = self._current_logs_service()
        self._logs_cache[service] = ''
        textbox = self.logs_textboxes.get(service)
        if textbox is None:
            return
        textbox.delete('1.0', 'end')
        textbox.insert('1.0', f'Logs limpiados para {service}.')

    def copy_current_log_tab(self) -> None:
        service = self._current_logs_service()
        textbox = self.logs_textboxes.get(service)
        if textbox is None:
            return
        try:
            content = textbox.get('sel.first', 'sel.last').strip()
        except Exception:
            content = textbox.get('1.0', 'end').strip()
        if not content:
            self.feedback_var.set(f'No hay contenido para copiar ({service}).')
            return
        self.clipboard_clear()
        self.clipboard_append(content)
        self.feedback_var.set(f'Logs copiados al portapapeles ({service}).')

    def _add_action_button(
        self,
        parent: ctk.CTkFrame,
        text: str,
        command,
        primary: bool = False,
        **kwargs: object,
    ) -> ctk.CTkButton:
        button_font = ctk.CTkFont(size=13, weight='bold' if primary else 'normal')
        button = ctk.CTkButton(
            parent,
            text=text,
            command=command,
            height=34,
            corner_radius=8,
            font=button_font,
            **kwargs,
        )
        self.action_buttons.append(button)
        return button

    @staticmethod
    def _windows_hidden_subprocess_kwargs() -> dict[str, object]:
        if os.name != 'nt':
            return {}
        kwargs: dict[str, object] = {'creationflags': subprocess.CREATE_NO_WINDOW}
        startupinfo_factory = getattr(subprocess, 'STARTUPINFO', None)
        startf_use_showwindow = getattr(subprocess, 'STARTF_USESHOWWINDOW', 0)
        if startupinfo_factory is not None:
            startupinfo = startupinfo_factory()
            startupinfo.dwFlags |= startf_use_showwindow
            startupinfo.wShowWindow = 0
            kwargs['startupinfo'] = startupinfo
        return kwargs

    def _run_start_command(self, *args: str) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(START_SCRIPT), *args]
        run_kwargs: dict[str, object] = {
            'cwd': ROOT,
            'text': True,
            'capture_output': True,
            'check': False,
        }
        run_kwargs.update(self._windows_hidden_subprocess_kwargs())
        return subprocess.run(command, **run_kwargs)

    def _run_backend_manage_command(
        self,
        *args: str,
        env_overrides: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        backend_python = self._resolve_backend_python()
        command = [str(backend_python), str(BACKEND_MANAGE_SCRIPT), *args]
        env = os.environ.copy()
        if env_overrides:
            env.update(env_overrides)
        run_kwargs: dict[str, object] = {
            'cwd': BACKEND_DIR,
            'text': True,
            'capture_output': True,
            'check': False,
            'env': env,
        }
        run_kwargs.update(self._windows_hidden_subprocess_kwargs())
        return subprocess.run(command, **run_kwargs)

    @staticmethod
    def _backend_python_path() -> Path:
        if os.name == 'nt':
            return BACKEND_VENV_PYTHON_WINDOWS
        return BACKEND_VENV_PYTHON_POSIX

    def _resolve_backend_python(self) -> Path:
        backend_python = self._backend_python_path()
        if backend_python.exists():
            return backend_python
        raise RuntimeError(
            'No se encontró el Python del backend en '
            f'{backend_python}. Prepara el entorno con `python start.py setup` '
            'o creando `apps/backend/.venv` antes de usar comandos Django desde el launcher.'
        )

    def run_action(self, action: str) -> None:
        feedback_text = {
            'full': 'Iniciando sistema completo... puede tardar unos minutos.',
            'lite': 'Iniciando modo lite... preparando backend y frontend.',
            'backend': 'Iniciando solo backend...',
            'frontend': 'Iniciando solo frontend...',
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

        command_args = self._build_start_args(action)
        if action in {'full', 'lite'}:
            self.preferences['last_mode'] = action
        self._save_preferences()
        self._run_background(action, feedback_text, *command_args)

    def _build_start_args(self, action: str) -> list[str]:
        global_args: list[str] = []
        command_args: list[str] = [action]
        if action in {'full', 'lite', 'frontend'} and not self.auto_open_browser_var.get():
            command_args.append('--no-browser')
        if action in {'full', 'lite', 'backend'}:
            command_args.extend(['--ollama', 'enabled' if self.use_ollama_var.get() else 'disabled'])
        if action in {'full', 'lite', 'backend', 'frontend'}:
            if self.debug_visible_processes_var.get():
                command_args.append('--separate-windows')
                if action in {'full', 'lite', 'backend'}:
                    command_args.append('--verbose')
            else:
                # Importante: --gui-silent es una bandera global en start.py.
                # Debe ir antes del subcomando para ser compatible con argparse.
                global_args.append('--gui-silent')
        if action in {'full', 'lite', 'backend'}:
            command_args.extend(
                [
                    '--ollama-aux-signal',
                    'enabled' if self.aux_signal_var.get() else 'disabled',
                    '--ollama-env-timeout',
                    str(self.ollama_timeout_var.get()),
                    '--ollama-timeout',
                    str(self.ollama_timeout_var.get()),
                ]
            )
        return [*global_args, *command_args]

    def refresh_status(self) -> None:
        self._run_background('status', 'Revisando estado de servicios...', 'status')

    def open_logs(self, service: str = 'all') -> None:
        self._set_busy(True)
        self.feedback_var.set(f'Abriendo logs del launcher ({service})...')

        def worker() -> None:
            result = self._run_start_command('logs', '--service', service)
            self.after(0, lambda: self._on_logs_ready(result, service))

        threading.Thread(target=worker, daemon=True).start()

    def _on_logs_ready(self, result: subprocess.CompletedProcess[str], service: str) -> None:
        self._set_busy(False)
        if result.returncode != 0:
            error_output = (result.stderr or result.stdout or 'Error desconocido').strip()
            self.feedback_var.set('No fue posible abrir logs.')
            messagebox.showerror('Error en logs', error_output)
            return

        logs_window = ctk.CTkToplevel(self)
        logs_window.title(f'Logs del launcher ({service})')
        logs_window.geometry('900x560')
        logs_window.grid_columnconfigure(0, weight=1)
        logs_window.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            logs_window,
            text=f'Salida de `start.py logs --service {service}`',
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
            'backend': 'Backend iniciado por el launcher.',
            'frontend': 'Frontend iniciado por el launcher.',
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

    def run_llm_shadow_smoke_test(self) -> None:
        try:
            self._resolve_backend_python()
        except RuntimeError as exc:
            self.feedback_var.set('Falta preparar entorno backend (.venv).')
            messagebox.showerror('Backend .venv faltante', str(exc))
            return

        model = self.ollama_model_var.get().strip() or DEFAULT_OLLAMA_MODEL
        timeout = self.ollama_timeout_var.get().strip() or '90'
        base_url = self.ollama_base_url_var.get().strip() or DEFAULT_OLLAMA_BASE_URL
        aux_signal_enabled = bool(self.aux_signal_var.get())

        command_args = [
            'run_llm_shadow_smoke',
            '--settings=config.settings.lite',
            '--model',
            model,
            '--timeout',
            timeout,
            '--json',
        ]
        command_args.append('--aux-signal' if aux_signal_enabled else '--no-aux-signal')
        env_overrides = {
            'OLLAMA_ENABLED': 'true',
            'LLM_ENABLED': 'true',
            'OLLAMA_AUX_SIGNAL_ENABLED': 'true' if aux_signal_enabled else 'false',
            'OLLAMA_BASE_URL': base_url,
            'OLLAMA_MODEL': model,
            'OLLAMA_TIMEOUT_SECONDS': timeout,
        }
        self._save_preferences()
        self._set_busy(True)
        self.feedback_var.set('Ejecutando smoke test corto de Ollama...')

        def worker() -> None:
            result = self._run_backend_manage_command(*command_args, env_overrides=env_overrides)
            self.after(0, lambda: self._on_smoke_test_done(result, model, timeout, base_url, aux_signal_enabled))

        threading.Thread(target=worker, daemon=True).start()

    def _on_smoke_test_done(
        self,
        result: subprocess.CompletedProcess[str],
        model: str,
        timeout: str,
        base_url: str,
        aux_signal_enabled: bool,
    ) -> None:
        self._set_busy(False)
        if result.returncode != 0:
            error_output = (result.stderr or result.stdout or 'Error desconocido').strip()
            concise_error = self._build_smoke_error_message(error_output)
            self.feedback_var.set('Smoke test de Ollama falló.')
            messagebox.showerror('Smoke test Ollama', concise_error)
            return

        raw_output = (result.stdout or '').strip()
        try:
            payload = json.loads(raw_output)
        except json.JSONDecodeError:
            self.feedback_var.set('Smoke test completó con salida no parseable.')
            messagebox.showerror(
                'Smoke test Ollama',
                'No se pudo parsear JSON de salida del smoke test. Revisa logs backend/Ollama.',
            )
            return

        self.feedback_var.set('Smoke test corto de Ollama completado.')
        self._show_smoke_result_window(payload, raw_output, model, timeout, base_url, aux_signal_enabled)

    @staticmethod
    def _build_smoke_error_message(raw_error: str) -> str:
        lowered = raw_error.lower()
        if "no module named 'celery'" in lowered or 'no module named "celery"' in lowered:
            return (
                'El comando se ejecutó sin dependencias del backend. '
                'Verifica `apps/backend/.venv` y vuelve a correr `python start.py setup`.'
            )
        if 'run migrations first' in lowered or 'could not access mission-control tables' in lowered:
            return 'Faltan migraciones en backend. Ejecuta: python apps/backend/manage.py migrate'
        if 'timed out' in lowered or 'timeout' in lowered:
            return 'El smoke test excedió el timeout de Ollama. Prueba con mayor timeout o revisa el servicio.'
        if 'connection refused' in lowered or 'failed to establish a new connection' in lowered:
            return 'No se pudo conectar a Ollama. Verifica que esté corriendo y la Base URL configurada.'
        if 'commanderror' in lowered:
            return f'Error del comando de smoke test: {raw_error.splitlines()[-1]}'
        compact = raw_error.splitlines()[-1] if raw_error.splitlines() else raw_error
        return compact or 'Error desconocido en smoke test de Ollama.'

    def _show_smoke_result_window(
        self,
        payload: dict[str, object],
        raw_json: str,
        model: str,
        timeout: str,
        base_url: str,
        aux_signal_enabled: bool,
    ) -> None:
        window = ctk.CTkToplevel(self)
        window.title('Resultado smoke test Ollama')
        window.geometry('940x660')
        window.grid_columnconfigure(0, weight=1)
        window.grid_rowconfigure(1, weight=1)
        window.grid_rowconfigure(3, weight=1)

        header = (
            f'Modelo: {model} | Timeout: {timeout}s | Aux signal: {"ON" if aux_signal_enabled else "OFF"}\n'
            f'Base URL: {base_url}'
        )
        ctk.CTkLabel(
            window,
            text=header,
            font=ctk.CTkFont(size=13),
            justify='left',
            anchor='w',
        ).grid(row=0, column=0, padx=16, pady=(16, 6), sticky='ew')

        summary_box = ctk.CTkTextbox(window, corner_radius=10, height=240)
        summary_box.grid(row=1, column=0, padx=16, pady=(0, 10), sticky='nsew')
        summary_lines = [
            f"ollama_responded: {payload.get('ollama_responded')}",
            f"llm_shadow_reasoning_status: {payload.get('llm_shadow_reasoning_status')}",
            f"summary: {payload.get('summary')}",
            f"key_risks: {json.dumps(payload.get('key_risks', []), ensure_ascii=False)}",
            f"key_supporting_points: {json.dumps(payload.get('key_supporting_points', []), ensure_ascii=False)}",
            f"artifact_id: {payload.get('artifact_id')}",
            f"llm_aux_signal_summary: {json.dumps(payload.get('llm_aux_signal_summary', {}), ensure_ascii=False, indent=2)}",
            f"boundaries: {json.dumps(payload.get('boundaries', {}), ensure_ascii=False)}",
        ]
        summary_box.insert('1.0', '\n\n'.join(summary_lines))
        summary_box.configure(state='disabled')

        ctk.CTkLabel(
            window,
            text='JSON completo',
            font=ctk.CTkFont(size=14, weight='bold'),
        ).grid(row=2, column=0, padx=16, pady=(0, 6), sticky='w')

        json_box = ctk.CTkTextbox(window, corner_radius=10)
        json_box.grid(row=3, column=0, padx=16, pady=(0, 16), sticky='nsew')
        pretty_json = json.dumps(payload, indent=2, ensure_ascii=False)
        json_box.insert('1.0', pretty_json if pretty_json.strip() else raw_json)
        json_box.configure(state='disabled')

    def _load_preferences(self) -> dict[str, object]:
        if not PREFERENCES_FILE.exists():
            return {
                'last_mode': 'full',
                'auto_open_browser': True,
                'use_ollama': True,
                'aux_signal_enabled': False,
                'ollama_timeout_seconds': '90',
                'ollama_base_url': DEFAULT_OLLAMA_BASE_URL,
                'ollama_model': DEFAULT_OLLAMA_MODEL,
                'debug_visible_processes': False,
            }
        try:
            loaded = json.loads(PREFERENCES_FILE.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            return {
                'last_mode': 'full',
                'auto_open_browser': True,
                'use_ollama': True,
                'aux_signal_enabled': False,
                'ollama_timeout_seconds': '90',
                'ollama_base_url': DEFAULT_OLLAMA_BASE_URL,
                'ollama_model': DEFAULT_OLLAMA_MODEL,
                'debug_visible_processes': False,
            }
        if not isinstance(loaded, dict):
            return {
                'last_mode': 'full',
                'auto_open_browser': True,
                'use_ollama': True,
                'aux_signal_enabled': False,
                'ollama_timeout_seconds': '90',
                'ollama_base_url': DEFAULT_OLLAMA_BASE_URL,
                'ollama_model': DEFAULT_OLLAMA_MODEL,
                'debug_visible_processes': False,
            }
        loaded.setdefault('last_mode', 'full')
        loaded.setdefault('auto_open_browser', True)
        loaded.setdefault('use_ollama', True)
        loaded.setdefault('aux_signal_enabled', False)
        loaded.setdefault('ollama_timeout_seconds', '90')
        loaded.setdefault('ollama_base_url', DEFAULT_OLLAMA_BASE_URL)
        loaded.setdefault('ollama_model', DEFAULT_OLLAMA_MODEL)
        loaded.setdefault('debug_visible_processes', False)
        return loaded

    def _save_preferences(self) -> None:
        self.preferences['window_geometry'] = self.geometry()
        self.preferences['auto_open_browser'] = bool(self.auto_open_browser_var.get())
        self.preferences['debug_visible_processes'] = bool(self.debug_visible_processes_var.get())
        self.preferences['use_ollama'] = bool(self.use_ollama_var.get())
        self.preferences['aux_signal_enabled'] = bool(self.aux_signal_var.get())
        self.preferences['ollama_timeout_seconds'] = str(self.ollama_timeout_var.get())
        self.preferences['ollama_base_url'] = self.ollama_base_url_var.get().strip() or DEFAULT_OLLAMA_BASE_URL
        self.preferences['ollama_model'] = self.ollama_model_var.get().strip() or DEFAULT_OLLAMA_MODEL
        PREFERENCES_FILE.parent.mkdir(parents=True, exist_ok=True)
        PREFERENCES_FILE.write_text(json.dumps(self.preferences, indent=2), encoding='utf-8')

    def _on_close(self) -> None:
        if self._logs_poll_job is not None:
            self.after_cancel(self._logs_poll_job)
            self._logs_poll_job = None
        self._save_preferences()
        self.destroy()


def maybe_relaunch_with_pythonw() -> None:
    if os.name != 'nt':
        return
    if os.environ.get('MTB_LAUNCHER_RELAUNCHED') == '1':
        return
    current_python = Path(sys.executable or '')
    if current_python.name.lower() == 'pythonw.exe':
        return
    pythonw_path = current_python.with_name('pythonw.exe')
    if not pythonw_path.exists():
        return
    env = os.environ.copy()
    env['MTB_LAUNCHER_RELAUNCHED'] = '1'
    creationflags = getattr(subprocess, 'DETACHED_PROCESS', 0) | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
    subprocess.Popen(
        [str(pythonw_path), str(Path(__file__).resolve())],
        cwd=str(ROOT),
        env=env,
        close_fds=True,
        creationflags=creationflags,
    )
    raise SystemExit(0)


if __name__ == '__main__':
    maybe_relaunch_with_pythonw()

    if not START_SCRIPT.exists():
        raise SystemExit('No se encontró start.py en la raíz del proyecto.')

    app = LauncherGUI()
    app.mainloop()
