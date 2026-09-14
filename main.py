# -*- coding: utf-8 -*-
import os
import sys
import traceback
import subprocess
import threading
import time
import configparser as ConfigParser
import tkinter as tk
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox

if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(SCRIPT_DIR, "settings.ini")
ERROR_LOG = os.path.join(SCRIPT_DIR, "error.log")
ICON_PATH = os.path.join(SCRIPT_DIR, "glitch.ico")
CREATE_NO_WINDOW = 0x08000000

TRAY_AVAILABLE = False
try:
    import ctypes
    from ctypes import wintypes

    NIM_ADD = 0x00000000
    NIM_MODIFY = 0x00000001
    NIM_DELETE = 0x00000002
    NIF_ICON = 0x00000002
    NIF_TIP = 0x00000004
    NIF_INFO = 0x00000010
    NIIF_INFO = 0x00000001

    IMAGE_ICON = 1
    LR_LOADFROMFILE = 0x00000010
    LR_DEFAULTSIZE = 0x00000040

    HICON = ctypes.c_void_p

    class NOTIFYICONDATAW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("hWnd", wintypes.HWND),
            ("uID", wintypes.UINT),
            ("uFlags", wintypes.UINT),
            ("uCallbackMessage", wintypes.UINT),
            ("hIcon", HICON),
            ("szTip", ctypes.c_wchar * 128),
            ("dwState", wintypes.DWORD),
            ("dwStateMask", wintypes.DWORD),
            ("szInfo", ctypes.c_wchar * 256),
            ("uVersion", wintypes.UINT),
            ("szInfoTitle", ctypes.c_wchar * 64),
            ("dwInfoFlags", wintypes.DWORD),
        ]

    _shell32 = ctypes.windll.shell32
    _user32 = ctypes.windll.user32
    TRAY_AVAILABLE = True
except Exception:
    TRAY_AVAILABLE = False


def log_error(msg):
    try:
        f = open(ERROR_LOG, 'ab')
        try:
            f.write(b"\n=== ")
            f.write(time.strftime("%Y-%m-%d %H:%M:%S").encode('ascii', 'replace'))
            f.write(b" ===\n")
            if isinstance(msg, str):
                msg = msg.encode('utf-8', 'replace')
            f.write(msg)
            f.write(b"\n")
        finally:
            f.close()
    except Exception:
        pass


def safe_str(s):
    if isinstance(s, str):
        return s
    if isinstance(s, bytes):
        for enc in ('cp1251', 'cp866', 'utf-8'):
            try:
                return s.decode(enc)
            except Exception:
                continue
        return s.decode('ascii', 'replace')
    try:
        return str(s)
    except Exception:
        return "?"


def load_app_icon():
    if not TRAY_AVAILABLE:
        return None
    if not os.path.isfile(ICON_PATH):
        return None
    try:
        h = _user32.LoadImageW(
            None,
            ctypes.c_wchar_p(ICON_PATH),
            IMAGE_ICON,
            0, 0,
            LR_LOADFROMFILE | LR_DEFAULTSIZE,
        )
        return h or None
    except Exception as e:
        log_error("load_app_icon: " + safe_str(e))
        return None


def set_window_icon(w):
    if not os.path.isfile(ICON_PATH):
        return
    try:
        w.iconbitmap(default=ICON_PATH)
    except Exception:
        try:
            w.iconbitmap(ICON_PATH)
        except Exception as e:
            log_error("set_window_icon: " + safe_str(e))


def show_balloon(hwnd, title, text, hicon=None):
    if not TRAY_AVAILABLE or not hwnd:
        return
    try:
        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = int(hwnd)
        nid.uID = 1
        nid.uFlags = NIF_ICON | NIF_TIP | NIF_INFO
        if hicon:
            nid.hIcon = hicon
        else:
            try:
                nid.hIcon = _user32.LoadIconW(None, ctypes.c_wchar_p(32512))
            except Exception:
                nid.hIcon = None
        nid.szTip = "Video Glitcher"
        nid.szInfo = (text or "")[:255]
        nid.szInfoTitle = (title or "")[:63]
        nid.dwInfoFlags = NIIF_INFO

        _shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))
        _shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid))

        def cleanup():
            time.sleep(8)
            try:
                _shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
            except Exception:
                pass
        t = threading.Thread(target=cleanup)
        t.daemon = True
        t.start()
    except Exception as e:
        log_error("show_balloon: " + safe_str(e))


TRANSLATIONS = {
    'ru': {
        'title': 'Video Glitcher',
        'lang_label': 'Язык:', 'theme_label': 'Тема:', 'lang_name': 'Русский',
        'input_video': 'Входное видео:',
        'output_dir': 'Папка для сохранения:',
        'output_name': 'Имя выходного файла (без расширения):',
        'btn_browse': 'Выбрать...', 'btn_process': 'Обработать видео',
        'btn_play': 'Воспроизвести', 'log_label': 'Лог ffmpeg:',
        'err': 'Ошибка', 'warn': 'Предупреждение',
        'ffmpeg_not_found': 'ffmpeg не найден',
        'ffmpeg_not_found_msg': 'Положите ffmpeg.exe рядом со скриптом.',
        'ffplay_not_found': 'ffplay не найден',
        'ffplay_not_found_msg': 'Положите ffplay.exe рядом со скриптом.',
        'file_not_found': 'Файл не найден:', 'dir_not_found': 'Папка не найдена:',
        'enter_name': 'Введите имя выходного файла.',
        'same_file': 'Выходной файл совпадает с входным.',
        'verify_failed': 'Проверка не прошла',
        'verify_failed_hint': 'Файл сохранён, но может не воспроизводиться.',
        'saved': 'Сохранено:', 'play_now': 'Воспроизвести сейчас?',
        'no_file_to_play': 'Нет файла для воспроизведения.',
        'error_ffmpeg': 'Ошибка ffmpeg', 'success': 'Успех',
        'ffmpeg_start': 'Запуск ffmpeg...',
        'done_checking': 'Готово, проверяем результат...',
        'verify_ok': 'Проверка пройдена:', 'verify_fail': 'Проверка не прошла:',
        'size_bytes': 'Размер:', 'playing': 'Воспроизведение:',
        'choose_video_title': 'Выберите видео', 'choose_dir_title': 'Куда сохранить',
        'all_files': 'Все файлы', 'video_files': 'Видео',
        'empty_file': 'Файл пустой (0 байт).', 'not_found_path': 'Файл не найден:',
        'tray_title': 'Готово', 'tray_msg': 'Видео успешно обработано',
        'first_run_title': 'Первый запуск',
        'first_run_lang': 'Язык:',
        'first_run_theme': 'Тема:',
        'theme_light_label': 'Светлая',
        'theme_dark_label': 'Тёмная',
    },
    'en': {
        'title': 'Video Glitcher',
        'lang_label': 'Language:', 'theme_label': 'Theme:', 'lang_name': 'English',
        'input_video': 'Input video:', 'output_dir': 'Output folder:',
        'output_name': 'Output file name (without extension):',
        'btn_browse': 'Browse...', 'btn_process': 'Process video',
        'btn_play': 'Play', 'log_label': 'ffmpeg log:',
        'err': 'Error', 'warn': 'Warning',
        'ffmpeg_not_found': 'ffmpeg not found',
        'ffmpeg_not_found_msg': 'Put ffmpeg.exe next to the script.',
        'ffplay_not_found': 'ffplay not found',
        'ffplay_not_found_msg': 'Put ffplay.exe next to the script.',
        'file_not_found': 'File not found:', 'dir_not_found': 'Folder not found:',
        'enter_name': 'Enter output file name.',
        'same_file': 'Output file is the same as input.',
        'verify_failed': 'Verification failed',
        'verify_failed_hint': 'File saved but may not play.',
        'saved': 'Saved:', 'play_now': 'Play now?',
        'no_file_to_play': 'No file to play.',
        'error_ffmpeg': 'ffmpeg error', 'success': 'Success',
        'ffmpeg_start': 'Starting ffmpeg...',
        'done_checking': 'Done, verifying...',
        'verify_ok': 'Verification passed:', 'verify_fail': 'Verification failed:',
        'size_bytes': 'Size:', 'playing': 'Playing:',
        'choose_video_title': 'Choose a video', 'choose_dir_title': 'Choose output folder',
        'all_files': 'All files', 'video_files': 'Video',
        'empty_file': 'File is empty (0 bytes).', 'not_found_path': 'File not found:',
        'tray_title': 'Done', 'tray_msg': 'Video processed successfully',
        'first_run_title': 'First launch',
        'first_run_lang': 'Language:',
        'first_run_theme': 'Theme:',
        'theme_light_label': 'Light',
        'theme_dark_label': 'Dark',
    },
    'zh': {
        'title': '视频处理工具',
        'lang_label': '语言:', 'theme_label': '主题:', 'lang_name': '中文',
        'input_video': '输入视频:', 'output_dir': '输出文件夹:',
        'output_name': '输出文件名（不含扩展名）:',
        'btn_browse': '浏览...', 'btn_process': '处理视频',
        'btn_play': '播放', 'log_label': 'ffmpeg 日志:',
        'err': '错误', 'warn': '警告',
        'ffmpeg_not_found': '未找到 ffmpeg',
        'ffmpeg_not_found_msg': '请将 ffmpeg.exe 放在脚本同一目录下。',
        'ffplay_not_found': '未找到 ffplay',
        'ffplay_not_found_msg': '请将 ffplay.exe 放在脚本同一目录下。',
        'file_not_found': '文件未找到:', 'dir_not_found': '文件夹未找到:',
        'enter_name': '请输入输出文件名。',
        'same_file': '输出文件与输入文件相同。',
        'verify_failed': '验证失败',
        'verify_failed_hint': '文件已保存，但可能无法播放。',
        'saved': '已保存:', 'play_now': '现在播放吗？',
        'no_file_to_play': '没有可播放的文件。',
        'error_ffmpeg': 'ffmpeg 错误', 'success': '成功',
        'ffmpeg_start': '正在启动 ffmpeg...',
        'done_checking': '完成，正在验证...',
        'verify_ok': '验证通过:', 'verify_fail': '验证失败:',
        'size_bytes': '大小:', 'playing': '正在播放:',
        'choose_video_title': '选择视频', 'choose_dir_title': '选择输出文件夹',
        'all_files': '所有文件', 'video_files': '视频',
        'empty_file': '文件为空（0 字节）。', 'not_found_path': '文件未找到:',
        'tray_title': '完成', 'tray_msg': '视频处理成功',
        'first_run_title': '首次启动',
        'first_run_lang': '语言:',
        'first_run_theme': '主题:',
        'theme_light_label': '浅色',
        'theme_dark_label': '深色',
    },

    'pt': {
        'title': 'Bugador de vídeo',
        'lang_label': 'Idioma:', 'theme_label': 'Tema:', 'lang_name': 'Português',
        'input_video': 'Vídeo de input:', 'output_dir': 'Pasta de output',
        'output_name': 'Arquivo de output (não coloque extensão):',
        'btn_browse': 'Procurar...', 'btn_process': 'Processar vídeo',
        'btn_play': 'Reproduzir', 'log_label': 'ffmpeg log:',
        'err': 'Erro', 'warn': 'Aviso',
        'ffmpeg_not_found': 'ffmpeg não encontrado',
        'ffmpeg_not_found_msg': 'Coloque ffmpeg.exe no próximo script.',
        'ffplay_not_found': 'ffplay não encontrado',
        'ffplay_not_found_msg': 'Coloque ffplay.exe no próximo script..',
        'file_not_found': 'Arquivo não encontrado:', 'dir_not_found': 'Pasta não encontrada:',
        'enter_name': 'Coloque arquivo de output',
        'same_file': 'Arquivo de output é o mesmo de input.',
        'verify_failed': 'Verificação falha',
        'verify_failed_hint': 'Arquivo criado mas não reproduzido.',
        'saved': 'Salvo:', 'play_now': 'Reproduzir agora?',
        'no_file_to_play': 'Sem arquivo pra reproduzir',
        'error_ffmpeg': 'Erro do ffmpeg', 'success': 'Sucesso',
        'ffmpeg_start': 'Iniciando ffmpeg...',
        'done_checking': 'Pronto, verificando...',
        'verify_ok': 'Verificação passou:', 'verify_fail': 'Verification falhou:',
        'size_bytes': 'Tamanho:', 'playing': 'Reproduzindo:',
        'choose_video_title': 'Escolha um nome pro vídeo', 'choose_dir_title': 'Escolha um nome pra pasta',
        'all_files': 'Todos os arquivos', 'video_files': 'Vídeo',
        'empty_file': 'Arquivo vazio (0 bytes).', 'not_found_path': 'Arquivo não encontrado:',
        'tray_title': 'Pronto', 'tray_msg': 'Vídeo processado com sucesso',
        'first_run_title': 'Primeira vez rodando',
        'first_run_lang': 'Idioma:',
        'first_run_theme': 'Tema:',
        'theme_light_label': 'Claro',
        'theme_dark_label': 'Escuro',
    },
}

THEMES = {
    'light': {
        'bg': '#f0f0f0', 'fg': '#000000',
        'entry_bg': '#ffffff', 'entry_fg': '#000000',
        'btn_bg': '#e1e1e1', 'btn_fg': '#000000', 'btn_active_bg': '#c8c8c8',
        'log_bg': '#ffffff', 'log_fg': '#000000',
        'select_bg': '#3399ff', 'select_fg': '#ffffff',
    },
    'dark': {
        'bg': '#2b2b2b', 'fg': '#e0e0e0',
        'entry_bg': '#1e1e1e', 'entry_fg': '#e0e0e0',
        'btn_bg': '#3c3c3c', 'btn_fg': '#e0e0e0', 'btn_active_bg': '#4a4a4a',
        'log_bg': '#1a1a1a', 'log_fg': '#d0d0d0',
        'select_bg': '#0078d7', 'select_fg': '#ffffff',
    },
}


def _find_exe(*names):
    for name in names:
        p = os.path.join(SCRIPT_DIR, name)
        if os.path.isfile(p):
            return p
    for name in names:
        for d in os.environ.get('PATH', '').split(os.pathsep):
            if not d:
                continue
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return p
    return None


def ffmpeg_exe():
    return _find_exe("ffmpeg.exe", "ffmpeg")


def ffplay_exe():
    return _find_exe("ffplay.exe", "ffplay")


class Config(object):
    def __init__(self, path):
        self.path = path
        self.parser = ConfigParser.RawConfigParser()
        self.parser.add_section('app')
        self._default('language', 'ru')
        self._default('theme', 'light')
        self._default('last_dir', SCRIPT_DIR)
        self._default('output_name', 'glitchy_output')
        self._default('geometry', '760x720')
        if os.path.isfile(path):
            try:
                self.parser.read(path, encoding='utf-8')
            except Exception:
                try:
                    self.parser.read(path)
                except Exception:
                    pass

    def _default(self, key, val):
        if not self.parser.has_option('app', key):
            try:
                self.parser.set('app', key, val)
            except Exception:
                pass

    def get(self, key, fallback=''):
        try:
            return self.parser.get('app', key)
        except Exception:
            return fallback

    def set(self, key, val):
        try:
            if not isinstance(val, str):
                val = safe_str(val)
            self.parser.set('app', str(key), val)
        except Exception:
            pass

    def save(self):
        try:
            f = open(self.path, 'w', encoding='utf-8')
            try:
                self.parser.write(f)
            finally:
                f.close()
        except Exception as e:
            log_error("Config.save: " + safe_str(e))


class FirstRunDialog(tk.Toplevel):
    def __init__(self, parent):
        tk.Toplevel.__init__(self, parent)
        self.result = None
        self.title("First launch / Первый запуск / 首次启动 / Primeria vez rodando")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        set_window_icon(self)

        tk.Label(self, text="Language / Язык / 语言 / Idioma:",
                 font=("Arial", 11, "bold")).pack(pady=(20, 6))
        self.lang_var = tk.StringVar(value='ru')
        lf = tk.Frame(self)
        lf.pack()
        for code, label in [('ru', 'Русский'), ('en', 'English'), ('zh', '中文'), ('pt', 'Português')]:
            tk.Radiobutton(lf, text=label, variable=self.lang_var,
                           value=code).pack(side='left', padx=10)

        tk.Label(self, text="Theme / Тема / 主题 / Tema:",
                 font=("Arial", 11, "bold")).pack(pady=(20, 6))
        self.theme_var = tk.StringVar(value='light')
        tf = tk.Frame(self)
        tf.pack()
        for code, label in [('light', 'Light / Светлая / 浅色 / Claro'),
                            ('dark', 'Dark / Тёмная / 深色 / Escuro')]:
            tk.Radiobutton(tf, text=label, variable=self.theme_var,
                           value=code).pack(side='left', padx=10)

        tk.Button(self, text="OK", width=14, command=self.on_ok).pack(pady=22)

        self.update_idletasks()
        w, h = 460, 300
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry("%dx%d+%d+%d" % (w, h, x, y))

    def on_ok(self):
        self.result = (self.lang_var.get(), self.theme_var.get())
        self.destroy()

    def on_cancel(self):
        self.result = ('ru', 'light')
        self.destroy()


class VideoGlitcherApp(object):
    def __init__(self, root):
        self.root = root
        self.cfg = Config(CONFIG_PATH)
        self.lang = self.cfg.get('language', 'ru') or 'ru'
        self.theme = self.cfg.get('theme', 'light') or 'light'
        if self.lang not in TRANSLATIONS:
            self.lang = 'ru'
        if self.theme not in THEMES:
            self.theme = 'light'

        self.last_output = None
        self.play_proc = None
        self.hicon = load_app_icon()
        set_window_icon(root)

        self._build_ui()
        self._apply_theme()
        self._update_language()

        try:
            self.root.geometry(self.cfg.get('geometry', '760x720'))
        except Exception:
            self.root.geometry('760x720')

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        if not os.path.isfile(CONFIG_PATH):
            self.root.after(300, self._show_first_run)

    def tr(self, key):
        d = TRANSLATIONS.get(self.lang) or TRANSLATIONS['ru']
        return d.get(key) or TRANSLATIONS['ru'].get(key, key)

    def _build_ui(self):
        r = self.root
        r.minsize(580, 560)
        pad = {'padx': 10}

        bar = tk.Frame(r)
        bar.pack(fill='x', padx=10, pady=(10, 0))

        self.lbl_lang = tk.Label(bar, text='')
        self.lbl_lang.pack(side='left')
        self.lang_var = tk.StringVar(value=self.lang)
        self.lang_menu = tk.OptionMenu(bar, self.lang_var, 'ru', 'en', 'zh',
                                       command=self._on_lang_change)
        self.lang_menu.pack(side='left', padx=(4, 16))

        self.lbl_theme = tk.Label(bar, text='')
        self.lbl_theme.pack(side='left')
        self.theme_var = tk.StringVar(value=self.theme)
        self.theme_menu = tk.OptionMenu(bar, self.theme_var, 'light', 'dark',
                                        command=self._on_theme_change)
        self.theme_menu.pack(side='left', padx=4)

        self.lbl_input = tk.Label(r, text='')
        self.lbl_input.pack(anchor='w', pady=(14, 0), **pad)
        f1 = tk.Frame(r)
        f1.pack(fill='x', **pad)
        self.input_path = tk.StringVar()
        self.ent_input = tk.Entry(f1, textvariable=self.input_path)
        self.ent_input.pack(side='left', fill='x', expand=True)
        self.btn_input = tk.Button(f1, text='', command=self.select_input)
        self.btn_input.pack(side='left', padx=(6, 0))

        self.lbl_outdir = tk.Label(r, text='')
        self.lbl_outdir.pack(anchor='w', pady=(10, 0), **pad)
        f2 = tk.Frame(r)
        f2.pack(fill='x', **pad)
        self.output_dir = tk.StringVar()
        self.ent_outdir = tk.Entry(f2, textvariable=self.output_dir)
        self.ent_outdir.pack(side='left', fill='x', expand=True)
        self.btn_outdir = tk.Button(f2, text='', command=self.select_output_dir)
        self.btn_outdir.pack(side='left', padx=(6, 0))

        self.lbl_outname = tk.Label(r, text='')
        self.lbl_outname.pack(anchor='w', pady=(10, 0), **pad)
        self.output_name = tk.StringVar(value=self.cfg.get('output_name', 'glitchy_output'))
        self.ent_outname = tk.Entry(r, textvariable=self.output_name)
        self.ent_outname.pack(fill='x', **pad)

        btns = tk.Frame(r)
        btns.pack(pady=15)
        self.run_btn = tk.Button(btns, text='', command=self.run_ffmpeg, width=20)
        self.run_btn.pack(side='left', padx=4)
        self.play_btn = tk.Button(btns, text='', command=self.play_output, width=16)
        self.play_btn.pack(side='left', padx=4)
        self.play_btn.configure(state='disabled')

        self.lbl_log = tk.Label(r, text='')
        self.lbl_log.pack(anchor='w', **pad)
        self.log = tk.Text(r, height=18, wrap='word')
        self.log.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        self.log.configure(state='disabled')

        last = self.cfg.get('last_dir', SCRIPT_DIR)
        if last and os.path.isdir(last):
            self.output_dir.set(last)

    def _show_first_run(self):
        try:
            dlg = FirstRunDialog(self.root)
            self.root.wait_window(dlg)
            if dlg.result:
                lang, theme = dlg.result
                self.lang = lang
                self.theme = theme
                self.cfg.set('language', lang)
                self.cfg.set('theme', theme)
                self.cfg.save()
                self.lang_var.set(lang)
                self.theme_var.set(theme)
                self._update_language()
                self._apply_theme()
        except Exception:
            log_error("_show_first_run:\n" + traceback.format_exc())

    def _on_lang_change(self, val):
        self.lang = val
        self.cfg.set('language', val)
        self.cfg.save()
        self._update_language()

    def _update_language(self):
        self.root.title(self.tr('title'))
        self.lbl_lang.configure(text=self.tr('lang_label'))
        self.lbl_theme.configure(text=self.tr('theme_label'))
        self.lbl_input.configure(text=self.tr('input_video'))
        self.lbl_outdir.configure(text=self.tr('output_dir'))
        self.lbl_outname.configure(text=self.tr('output_name'))
        self.lbl_log.configure(text=self.tr('log_label'))
        self.btn_input.configure(text=self.tr('btn_browse'))
        self.btn_outdir.configure(text=self.tr('btn_browse'))
        self.run_btn.configure(text=self.tr('btn_process'))
        self.play_btn.configure(text=self.tr('btn_play'))
        self.lang_menu.configure(text=self.tr('lang_name'))

    def _on_theme_change(self, val):
        self.theme = val
        self.cfg.set('theme', val)
        self.cfg.save()
        self._apply_theme()

    def _apply_theme(self):
        t = THEMES[self.theme]
        try:
            self.root.configure(bg=t['bg'])
        except Exception:
            pass
        self._color_recursive(self.root, t)
        self._apply_menu_colors(t)

    def _apply_menu_colors(self, t):
        for mb in (self.lang_menu, self.theme_menu):
            try:
                mb.configure(bg=t['btn_bg'], fg=t['btn_fg'],
                             activebackground=t['btn_active_bg'],
                             activeforeground=t['btn_fg'])
                mb['menu'].configure(bg=t['entry_bg'], fg=t['entry_fg'],
                                     activebackground=t['select_bg'],
                                     activeforeground=t['select_fg'])
            except Exception:
                pass

    def _color_recursive(self, w, t):
        cls = w.winfo_class()
        try:
            if cls == 'Label':
                w.configure(bg=t['bg'], fg=t['fg'])
            elif cls == 'Frame':
                w.configure(bg=t['bg'])
            elif cls == 'Entry':
                w.configure(bg=t['entry_bg'], fg=t['entry_fg'],
                            insertbackground=t['fg'], relief='solid', bd=1,
                            highlightthickness=0)
            elif cls == 'Button':
                w.configure(bg=t['btn_bg'], fg=t['btn_fg'],
                            activebackground=t['btn_active_bg'],
                            activeforeground=t['btn_fg'])
            elif cls == 'Text':
                w.configure(bg=t['log_bg'], fg=t['log_fg'],
                            insertbackground=t['fg'],
                            selectbackground=t['select_bg'],
                            selectforeground=t['select_fg'],
                            relief='solid', bd=1)
        except Exception:
            pass
        for c in w.winfo_children():
            self._color_recursive(c, t)

    def select_input(self):
        path = filedialog.askopenfilename(
            title=self.tr('choose_video_title'),
            filetypes=[(self.tr('video_files'), "*.mp4 *.avi *.mkv *.mov *.webm"),
                       (self.tr('all_files'), "*.*")],
        )
        if not path:
            return
        path = os.path.normpath(os.path.abspath(path))
        self.input_path.set(path)
        self.output_dir.set(os.path.dirname(path))
        base = os.path.splitext(os.path.basename(path))[0]
        self.output_name.set(base + "_glitch")

    def select_output_dir(self):
        d = filedialog.askdirectory(title=self.tr('choose_dir_title'))
        if d:
            self.output_dir.set(os.path.normpath(os.path.abspath(d)))

    def log_msg(self, msg):
        msg = safe_str(msg)
        self.log.configure(state='normal')
        try:
            self.log.insert('end', msg + "\n")
            lines = int(self.log.index('end-1c').split('.')[0])
            if lines > 400:
                self.log.delete('1.0', '100.0')
            self.log.see('end')
        except Exception:
            pass
        self.log.configure(state='disabled')

    def run_ffmpeg(self):
        exe = ffmpeg_exe()
        if not exe:
            messagebox.showerror(self.tr('ffmpeg_not_found'),
                                 self.tr('ffmpeg_not_found_msg'))
            return

        inp = self.input_path.get().strip().strip('"')
        outdir = self.output_dir.get().strip().strip('"')
        name = self.output_name.get().strip()

        if not inp or not os.path.isfile(inp):
            messagebox.showerror(self.tr('err'), self.tr('file_not_found') + "\n" + inp)
            return
        if not outdir or not os.path.isdir(outdir):
            messagebox.showerror(self.tr('err'), self.tr('dir_not_found') + "\n" + outdir)
            return
        if not name:
            messagebox.showerror(self.tr('err'), self.tr('enter_name'))
            return

        if name.lower().endswith(".mp4"):
            name = name[:-4]

        inp = os.path.normpath(os.path.abspath(inp))
        outdir = os.path.normpath(os.path.abspath(outdir))
        out_path = os.path.normpath(os.path.join(outdir, name + ".mp4"))

        if inp == out_path:
            messagebox.showerror(self.tr('err'), self.tr('same_file'))
            return

        self.cfg.set('last_dir', outdir)
        self.cfg.set('output_name', name)
        self.cfg.save()

        self.log.configure(state='normal')
        self.log.delete('1.0', 'end')
        self.log.configure(state='disabled')
        self.run_btn.configure(state='disabled')
        self.play_btn.configure(state='disabled')

        t = threading.Thread(target=self._process, args=(exe, inp, out_path))
        t.daemon = True
        t.start()

    def _process(self, exe, inp, out):
        try:
            self.log_msg("ffmpeg: " + exe)
            self.log_msg("IN:  " + inp)
            self.log_msg("OUT: " + out)
            self.log_msg(self.tr('ffmpeg_start') + "\n")

            cmd = [
                exe, "-y",
                "-hide_banner", "-loglevel", "warning", "-nostats",
                "-i", inp,
                "-c:v", "mpeg4",
                "-c:a", "ac3",
                "-q:v", "31",
                "-vf", "scale=480:320,setsar=1",
                "-af", "volume=30dB",
                "-ar", "32000",
                "-b:a", "8k",
                "-r", "15",
                "-strict", "-2",
                "-bsf:v", "noise=256",
                out,
            ]
            self.log_msg("CMD: " + " ".join(
                ('"' + a + '"') if " " in a else a for a in cmd
            ) + "\n")

            flags = CREATE_NO_WINDOW if os.name == 'nt' else 0
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                stdin=subprocess.PIPE, shell=False, creationflags=flags,
            )
            so, se = proc.communicate()

            if so:
                self.log_msg("--- stdout ---")
                self.log_msg(safe_str(so))
            if se:
                self.log_msg("--- stderr ---")
                self.log_msg(safe_str(se))

            if proc.returncode != 0:
                err = safe_str(se)[-1500:] if se else "(no details)"
                self.log_msg("X ffmpeg rc=" + safe_str(proc.returncode))
                self.log_msg("--- error ---")
                self.log_msg(err)
                self.log_msg("--- end ---")
                self.root.after(0, lambda m=err: messagebox.showerror(
                    self.tr('error_ffmpeg'), m))
                return

            self.log_msg(self.tr('done_checking') + "\n")
            ok, info = self._verify_output(exe, out)
            if not ok:
                self.log_msg(self.tr('verify_fail') + " " + safe_str(info))
                self.root.after(0, lambda m=safe_str(info): messagebox.showwarning(
                    self.tr('verify_failed'),
                    m + "\n\n" + self.tr('verify_failed_hint')))
                return

            self.log_msg(self.tr('verify_ok'))
            self.log_msg(info)
            self.log_msg("\nOK")

            self.last_output = out

            try:
                hwnd = self.root.winfo_id()
                show_balloon(hwnd, self.tr('tray_title'), self.tr('tray_msg'),
                             hicon=self.hicon)
            except Exception as e:
                log_error("tray call: " + safe_str(e))

            self.root.after(0, lambda: self._on_success(out))

        except Exception:
            err = traceback.format_exc()
            log_error("_process:\n" + safe_str(err))
            self.root.after(0, lambda m=safe_str(err): messagebox.showerror(
                self.tr('err'), m[-1200:]))
        finally:
            self.root.after(0, lambda: self.run_btn.configure(state='normal'))

    def _verify_output(self, exe, path):
        if not os.path.isfile(path):
            return False, self.tr('not_found_path') + " " + path
        size = os.path.getsize(path)
        if size == 0:
            return False, self.tr('empty_file')
        self.log_msg(self.tr('size_bytes') + " " + str(size))

        flags = CREATE_NO_WINDOW if os.name == 'nt' else 0

        c1 = [exe, "-hide_banner", "-loglevel", "error",
              "-nostats", "-i", path, "-f", "null", "-"]
        p1 = subprocess.Popen(c1,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              stdin=subprocess.PIPE, shell=False, creationflags=flags)
        so1, se1 = p1.communicate()
        if p1.returncode != 0:
            err = safe_str(se1).strip() if se1 else "(no output)"
            return False, "decode rc=" + str(p1.returncode) + ":\n" + err

        c2 = [exe, "-hide_banner", "-i", path]
        p2 = subprocess.Popen(c2,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              stdin=subprocess.PIPE, shell=False, creationflags=flags)
        so2, se2 = p2.communicate()
        info = safe_str(se2)
        lines = []
        for line in info.splitlines():
            s = line.strip()
            if s.startswith("Duration") or s.startswith("Stream"):
                lines.append(s)
        return True, ("\n".join(lines) if lines else "(no metadata)")

    def _on_success(self, out):
        self.run_btn.configure(state='normal')
        self.play_btn.configure(state='normal')
        if messagebox.askyesno(self.tr('success'),
                               self.tr('saved') + "\n" + out +
                               "\n\n" + self.tr('play_now')):
            self.play_output()

    def play_output(self):
        if not self.last_output or not os.path.isfile(self.last_output):
            messagebox.showerror(self.tr('err'), self.tr('no_file_to_play'))
            return
        player = ffplay_exe()
        if not player:
            messagebox.showerror(self.tr('ffplay_not_found'),
                                 self.tr('ffplay_not_found_msg'))
            return
        if self.play_proc and self.play_proc.poll() is None:
            try:
                self.play_proc.terminate()
            except Exception:
                pass

        flags = CREATE_NO_WINDOW if os.name == 'nt' else 0
        cmd = [player,
               "-window_title", "Glitch preview",
               "-autoexit",
               self.last_output]
        try:
            self.play_proc = subprocess.Popen(cmd,
                                              shell=False, creationflags=flags)
            self.log_msg(self.tr('playing') + " " + self.last_output)
        except Exception as e:
            messagebox.showerror(self.tr('err'), safe_str(e))

    def on_close(self):
        try:
            self.cfg.set('geometry', self.root.geometry())
            self.cfg.set('language', self.lang)
            self.cfg.set('theme', self.theme)
            self.cfg.set('last_dir', self.output_dir.get() or SCRIPT_DIR)
            self.cfg.set('output_name', self.output_name.get())
            self.cfg.save()
        except Exception:
            pass
        try:
            if self.play_proc and self.play_proc.poll() is None:
                self.play_proc.terminate()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass


def main():
    try:
        root = tk.Tk()
    except Exception:
        log_error("Tk init failed:\n" + traceback.format_exc())
        try:
            sys.stderr.write(traceback.format_exc())
        except Exception:
            pass
        return 1
    try:
        app = VideoGlitcherApp(root)
    except Exception:
        err = traceback.format_exc()
        log_error("VideoGlitcherApp init:\n" + err)
        try:
            messagebox.showerror("Fatal error", err[-1500:])
        except Exception:
            pass
        try:
            root.destroy()
        except Exception:
            pass
        return 1
    try:
        root.mainloop()
    except Exception:
        log_error("mainloop:\n" + traceback.format_exc())
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
