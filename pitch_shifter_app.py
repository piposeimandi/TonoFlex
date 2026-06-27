#!/usr/bin/env python3
"""
Pitch Shifter - Ajuste de tono sin cambio de velocidad
- Rango: -5 a +6 semitonos (siempre respecto al original)
- Botones de ±1 semitono
- Seek adelante/atrás durante preview
- Indicador visible de procesamiento
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import threading
import os
import tempfile
import numpy as np
import librosa
import soundfile as sf
import pygame
import yt_dlp
import shutil
import warnings

warnings.filterwarnings('ignore', category=UserWarning)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DESCARGAS_DIR = os.path.join(BASE_DIR, "descargas")
CONVERTIDOS_DIR = os.path.join(BASE_DIR, "convertidos")
TEMP_DIR = tempfile.mkdtemp(prefix='pitchshifter_')

os.makedirs(DESCARGAS_DIR, exist_ok=True)
os.makedirs(CONVERTIDOS_DIR, exist_ok=True)

SUPPORTED_EXTENSIONS = (
    '.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac',
    '.mp4', '.avi', '.mkv', '.mov', '.webm', '.wmv',
    '.opus', '.wma',
)


class PitchShifterApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("TonoFlex")
        self.root.geometry("950x700")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.original_audio = None
        self.processed_audio = None
        self.sample_rate = None
        self.duration = 0.0
        self.is_stereo = False
        self.current_pitch = 0.0
        self.volume = 0.8
        self.file_path = None
        self.file_name = "Ningún archivo cargado"

        self.normalize_enabled = False
        self.normalize_ceiling_db = -1.0

        self.last_processed_pitch = None
        self._last_normalize_state = False

        self.is_playing = False
        self.is_paused = False
        self.playback_pos = 0.0
        self.processing = False
        self._pitch_timer = None

        self.temp_wav = os.path.join(TEMP_DIR, "current_processed.wav")
        self._play_requested = False
        self._play_start_pos = 0.0

        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)

        self.set_icon()
        self.setup_ui()
        self.update_timer()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ────────────────────── Icono ──────────────────────

    def set_icon(self):
        icon_path = os.path.join(BASE_DIR, "pitch-shifter.png")
        if os.path.exists(icon_path):
            try:
                img = Image.open(icon_path)
                photo = ImageTk.PhotoImage(img)
                self.root.iconphoto(True, photo)
            except Exception:
                pass

    # ────────────────────── UI Setup ──────────────────────

    def setup_ui(self):
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(3, weight=1)

        header = ctk.CTkLabel(
            self.root, text="TonoFlex",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        header.grid(row=0, column=0, pady=(10, 0))

        subtitle = ctk.CTkLabel(
            self.root, text="Ajusta el tono sin cambiar la velocidad — siempre respecto al original",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        subtitle.grid(row=1, column=0, pady=(0, 5))

        # ── Top: File + YouTube ──
        top = ctk.CTkFrame(self.root, fg_color="transparent")
        top.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        top.grid_columnconfigure(1, weight=1)

        self.load_btn = ctk.CTkButton(
            top, text="Cargar Archivo",
            command=self.load_file, width=130
        )
        self.load_btn.grid(row=0, column=0, padx=(0, 5), pady=5)

        self.url_entry = ctk.CTkEntry(
            top, placeholder_text="URL de YouTube..."
        )
        self.url_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.url_entry.bind("<Return>", lambda e: self.download_youtube())

        self.dl_btn = ctk.CTkButton(
            top, text="Descargar",
            command=self.download_youtube, width=100
        )
        self.dl_btn.grid(row=0, column=2, padx=(5, 0), pady=5)

        # ── Info ──
        info = ctk.CTkFrame(self.root)
        info.grid(row=3, column=0, sticky="ew", padx=10, pady=5)
        info.grid_columnconfigure(0, weight=1)

        self.file_label = ctk.CTkLabel(info, text="Archivo: —", anchor="w")
        self.file_label.grid(row=0, column=0, sticky="ew", padx=10, pady=2)

        info_bottom = ctk.CTkFrame(info, fg_color="transparent")
        info_bottom.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 2))
        info_bottom.grid_columnconfigure(0, weight=1)

        self.duration_label = ctk.CTkLabel(info_bottom, text="Duración: --:--")
        self.duration_label.grid(row=0, column=0, sticky="w")

        self.info_label = ctk.CTkLabel(info_bottom, text="")
        self.info_label.grid(row=0, column=1, sticky="e")

        # ── Waveform ──
        wf_frame = ctk.CTkFrame(self.root)
        wf_frame.grid(row=4, column=0, sticky="nsew", padx=10, pady=5)
        wf_frame.grid_rowconfigure(0, weight=1)
        wf_frame.grid_columnconfigure(0, weight=1)

        self.waveform_canvas = tk.Canvas(
            wf_frame, bg='#1e1e1e', highlightthickness=0
        )
        self.waveform_canvas.grid(row=0, column=0, sticky="nsew")
        self.waveform_canvas.bind("<Button-1>", self.on_waveform_click)
        self.waveform_canvas.bind("<Configure>", lambda e: self.draw_waveform())

        # ── Playback Controls ──
        ctrl = ctk.CTkFrame(self.root)
        ctrl.grid(row=5, column=0, sticky="ew", padx=10, pady=5)
        ctrl.grid_columnconfigure(3, weight=1)

        self.play_btn = ctk.CTkButton(
            ctrl, text="\u25B6", width=50,
            command=self.play, state="disabled"
        )
        self.play_btn.grid(row=0, column=0, padx=5, pady=5)

        self.stop_btn = ctk.CTkButton(
            ctrl, text="\u23F9", width=50,
            command=self.stop, state="disabled"
        )
        self.stop_btn.grid(row=0, column=1, padx=5, pady=5)

        # Seek buttons
        self.seek_back_btn = ctk.CTkButton(
            ctrl, text="\u25C0\u200910s", width=55,
            command=lambda: self.seek_relative(-10),
            state="disabled"
        )
        self.seek_back_btn.grid(row=0, column=2, padx=5, pady=5)

        self.progress_slider = ctk.CTkSlider(
            ctrl, from_=0, to=100,
            command=self.on_seek, state="normal"
        )
        self.progress_slider.grid(
            row=0, column=3, sticky="ew", padx=5, pady=5
        )
        self.progress_slider.set(0)

        self.seek_fwd_btn = ctk.CTkButton(
            ctrl, text="10s\u2009\u25B6", width=55,
            command=lambda: self.seek_relative(10),
            state="disabled"
        )
        self.seek_fwd_btn.grid(row=0, column=4, padx=5, pady=5)

        self.time_current = ctk.CTkLabel(ctrl, text="0:00", width=45)
        self.time_current.grid(row=0, column=5, padx=(5, 0))

        self.time_total = ctk.CTkLabel(ctrl, text="0:00", width=45)
        self.time_total.grid(row=0, column=6, padx=(0, 10))

        # ── Effects ──
        fx = ctk.CTkFrame(self.root)
        fx.grid(row=6, column=0, sticky="ew", padx=10, pady=5)
        fx.grid_columnconfigure(2, weight=1)

        # Pitch row
        ctk.CTkLabel(fx, text="Tono (semitones):").grid(
            row=0, column=0, padx=(10, 5), pady=10
        )

        self.pitch_down_btn = ctk.CTkButton(
            fx, text="-1", width=40,
            command=self.pitch_down, state="disabled"
        )
        self.pitch_down_btn.grid(row=0, column=1, padx=2, pady=10)

        self.pitch_slider = ctk.CTkSlider(
            fx, from_=-5, to=6, number_of_steps=110,
            command=self.on_pitch_change
        )
        self.pitch_slider.grid(row=0, column=2, sticky="ew", padx=5, pady=10)
        self.pitch_slider.set(0)

        self.pitch_up_btn = ctk.CTkButton(
            fx, text="+1", width=40,
            command=self.pitch_up, state="disabled"
        )
        self.pitch_up_btn.grid(row=0, column=3, padx=2, pady=10)

        self.pitch_value = ctk.CTkLabel(fx, text="0.0 st", width=60)
        self.pitch_value.grid(row=0, column=4, padx=5, pady=10)

        self.reset_btn = ctk.CTkButton(
            fx, text="Reset", width=60,
            command=self.reset_pitch, state="disabled"
        )
        self.reset_btn.grid(row=0, column=5, padx=5, pady=10)

        # Volume row
        ctk.CTkLabel(fx, text="Volumen:").grid(
            row=1, column=0, padx=(10, 5), pady=10
        )

        self.vol_slider = ctk.CTkSlider(
            fx, from_=0, to=1, command=self.on_volume_change
        )
        self.vol_slider.grid(row=1, column=2, sticky="ew", padx=5, pady=10)
        self.vol_slider.set(0.8)

        self.vol_value = ctk.CTkLabel(fx, text="80%", width=60)
        self.vol_value.grid(row=1, column=4, padx=5, pady=10)

        # Normalization row
        ctk.CTkLabel(fx, text="Normalizar:").grid(
            row=2, column=0, padx=(10, 5), pady=10
        )

        self.normalize_var = ctk.BooleanVar(value=False)
        self.normalize_check = ctk.CTkCheckBox(
            fx, text="", variable=self.normalize_var,
            command=self.on_normalize_toggle,
            width=20
        )
        self.normalize_check.grid(row=2, column=1, padx=2, pady=10)

        self.ceiling_label = ctk.CTkLabel(fx, text="Techo:", state="disabled")
        self.ceiling_label.grid(row=2, column=2, padx=(15, 5), pady=10)

        self.ceiling_slider = ctk.CTkSlider(
            fx, from_=-12, to=-0.5, number_of_steps=115,
            command=self.on_ceiling_change,
            state="disabled"
        )
        self.ceiling_slider.grid(row=2, column=3, sticky="ew", padx=5, pady=10)
        self.ceiling_slider.set(-1.0)

        self.ceiling_value = ctk.CTkLabel(fx, text="-1.0 dB", width=60)
        self.ceiling_value.grid(row=2, column=4, padx=5, pady=10)

        self.ceiling_note = ctk.CTkLabel(
            fx, text="(pico máx)",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        self.ceiling_note.grid(row=2, column=5, padx=5, pady=10, sticky="w")

        # ── Bottom ──
        bottom = ctk.CTkFrame(self.root, fg_color="transparent")
        bottom.grid(row=7, column=0, sticky="ew", padx=10, pady=(5, 10))
        bottom.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(bottom, text="Listo", anchor="w",
                                          font=ctk.CTkFont(size=13))
        self.status_label.grid(row=0, column=0, sticky="ew", padx=5)

        self.export_btn = ctk.CTkButton(
            bottom, text="Exportar a convertidos/",
            command=self.export_audio, state="disabled",
            height=38
        )
        self.export_btn.grid(row=0, column=2, padx=5)

        self.procesar_btn = ctk.CTkButton(
            bottom, text="Procesar",
            command=self.procesar, state="disabled",
            height=38, width=100
        )
        self.procesar_btn.grid(row=0, column=1, padx=5)

        # Progress bar for processing indicator
        self.progress_bar = ctk.CTkProgressBar(
            bottom, mode='indeterminate', width=200,
            height=10
        )
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=5, pady=(5, 0))
        self.progress_bar.grid_remove()

        # Keyboard shortcuts
        self.root.bind("<space>", lambda e: self.toggle_play_pause())
        self.root.bind("<Left>", lambda e: self.seek_relative(-5))
        self.root.bind("<Right>", lambda e: self.seek_relative(5))
        self.root.bind("<Up>", lambda e: self.pitch_up())
        self.root.bind("<Down>", lambda e: self.pitch_down())

    # ─────────────────── Processing Indicator ───────────────────

    def show_processing(self, active):
        if active:
            self.processing = True
            self.progress_bar.grid()
            self.progress_bar.start()
            self.status_label.configure(
                text="\u2699 Procesando cambio de tono...",
                text_color="#ffa500"
            )
            self.root.config(cursor="watch")
            self.root.update_idletasks()
        else:
            self.processing = False
            self.progress_bar.stop()
            self.progress_bar.grid_remove()
            self.status_label.configure(text_color=("gray10", "gray90"))
            self.root.config(cursor="")

    # ─────────────────── Audio Processing ───────────────────

    def process_pitch_shift(self, semitones):
        if self.original_audio is None:
            return
        if self.processing:
            return

        self.show_processing(True)

        try:
            y = self.original_audio
            sr = self.sample_rate

            if self.is_stereo:
                ch0 = librosa.effects.pitch_shift(
                    y[0], sr=sr, n_steps=semitones, res_type='kaiser_best'
                )
                ch1 = librosa.effects.pitch_shift(
                    y[1], sr=sr, n_steps=semitones, res_type='kaiser_best'
                )
                y_shifted = np.vstack([ch0, ch1])
                audio_for_file = y_shifted.T
            else:
                y_shifted = librosa.effects.pitch_shift(
                    y, sr=sr, n_steps=semitones, res_type='kaiser_best'
                )
                audio_for_file = y_shifted

            if self.normalize_enabled:
                y_shifted = self.normalize_audio(y_shifted, self.normalize_ceiling_db)
                if self.is_stereo:
                    audio_for_file = y_shifted.T
                else:
                    audio_for_file = y_shifted

            self.processed_audio = y_shifted
            sf.write(self.temp_wav, audio_for_file, sr, subtype='PCM_16')
            self.last_processed_pitch = semitones
            self._last_normalize_state = self.normalize_enabled

            self.status_label.configure(
                text=f"Tono ajustado: {semitones:+.1f} st (respecto al original) — {self.file_name}"
            )
        except Exception as e:
            self.status_label.configure(text="Error en procesamiento")
            messagebox.showerror("Error", f"Error al procesar audio:\n{e}")
        finally:
            self.show_processing(False)
            if self._play_requested:
                self._play_requested = False
                self.root.after(0, lambda: self.play(from_pos=self.playback_pos))

    # ─────────────────── Normalization ───────────────────

    @staticmethod
    def normalize_audio(audio, ceiling_db):
        """Peak-normalize audio so the maximum peak reaches ceiling_db dB.
        Para estéreo: misma ganancia en ambos canales para mantener imagen."""
        ceiling_linear = 10 ** (ceiling_db / 20.0)
        if audio.ndim == 1:
            max_val = np.max(np.abs(audio))
        else:
            max_val = np.max(np.abs(audio))
        if max_val > 1e-10:
            gain = min(ceiling_linear / max_val, 10.0)
            return audio * gain
        return audio

    def on_normalize_toggle(self):
        enabled = self.normalize_var.get()
        self.normalize_enabled = enabled
        state = "normal" if enabled else "disabled"
        self.ceiling_label.configure(state=state)
        self.ceiling_slider.configure(state=state)
        self.ceiling_value.configure(state=state)
        if self.original_audio is not None:
            self.status_label.configure(
                text="Normalización cambiada — presioná Procesar para aplicar"
            )

    def on_ceiling_change(self, value):
        db = round(value, 1)
        self.normalize_ceiling_db = db
        self.ceiling_value.configure(text=f"{db:+.1f} dB")
        if self.normalize_enabled and self.original_audio is not None:
            self.status_label.configure(
                text="Techo cambiado — presioná Procesar para aplicar"
            )

    # ─────────────────── Event Handlers ───────────────────

    def on_pitch_change(self, value):
        semitones = round(value, 1)
        if semitones < -5:
            semitones = -5
        elif semitones > 6:
            semitones = 6
        self.current_pitch = semitones
        self.pitch_value.configure(text=f"{semitones:+.1f} st")
        if self.original_audio is not None:
            self.status_label.configure(
                text=f"Tono: {semitones:+.1f} st — presioná Procesar o Play"
            )

    def apply_pitch(self):
        if self.original_audio is None:
            return
        save_pos = self.playback_pos
        was_playing = self.is_playing and not self.is_paused
        if was_playing:
            self.stop_playback()

        t = threading.Thread(
            target=self.process_and_resume,
            args=(self.current_pitch, was_playing, save_pos),
            daemon=True
        )
        t.start()

    def process_and_resume(self, semitones, was_playing, save_pos):
        self.process_pitch_shift(semitones)
        if was_playing:
            self.root.after(0, lambda: self.play(from_pos=save_pos))

    def pitch_up(self):
        val = min(6.0, self.current_pitch + 1.0)
        self.pitch_slider.set(val)
        self.on_pitch_change(val)

    def pitch_down(self):
        val = max(-5.0, self.current_pitch - 1.0)
        self.pitch_slider.set(val)
        self.on_pitch_change(val)

    def procesar(self):
        """Procesa el audio con el tono actual sin reproducir."""
        if self.original_audio is None:
            return
        if self.processing:
            return
        self._play_requested = False
        t = threading.Thread(
            target=self.process_pitch_shift,
            args=(self.current_pitch,),
            daemon=True,
        )
        t.start()

    def reset_pitch(self):
        self.pitch_slider.set(0)
        self.on_pitch_change(0)

    def on_volume_change(self, value):
        self.volume = value
        self.vol_value.configure(text=f"{int(value * 100)}%")
        try:
            pygame.mixer.music.set_volume(self.volume)
        except Exception:
            pass

    def seek_relative(self, delta_seconds):
        if self.processed_audio is None or self.duration <= 0:
            return
        new_pos = max(0, min(self.duration, self.playback_pos + delta_seconds))
        self.playback_pos = new_pos
        ratio = new_pos / self.duration
        self.progress_slider.set(ratio * 100)

        m = int(new_pos // 60)
        s = int(new_pos % 60)
        self.time_current.configure(text=f"{m}:{s:02d}")

        self.play(from_pos=new_pos)

    def on_seek(self, value):
        if self.processed_audio is None or self.duration <= 0:
            return
        pos = (value / 100.0) * self.duration
        self.playback_pos = pos
        self.play(from_pos=pos)

    def on_waveform_click(self, event):
        if self.processed_audio is None or self.duration <= 0:
            return
        w = self.waveform_canvas.winfo_width()
        if w <= 1:
            return
        ratio = max(0, min(1, event.x / w))
        pos = ratio * self.duration
        self.playback_pos = pos
        self.progress_slider.set(ratio * 100)
        self.play(from_pos=pos)

    # ─────────────────── Playback ───────────────────

    def play(self, from_pos=None):
        if self.original_audio is None:
            return

        if self.processing:
            self._play_requested = True
            return

        needs = (
            self.processed_audio is None
            or self.current_pitch != self.last_processed_pitch
            or self.normalize_enabled != self._last_normalize_state
        )
        if needs:
            self.process_pitch_shift(self.current_pitch)

        if self.processed_audio is None:
            return

        pos = from_pos if from_pos is not None else self.playback_pos

        try:
            if not os.path.exists(self.temp_wav):
                if self.is_stereo:
                    af = self.processed_audio.T
                else:
                    af = self.processed_audio
                sf.write(self.temp_wav, af, self.sample_rate, subtype='PCM_16')

            pygame.mixer.music.load(self.temp_wav)
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play(start=pos)
            self._play_start_pos = pos

            self.is_playing = True
            self.is_paused = False
            self.play_btn.configure(text="\u23F8")
            self.stop_btn.configure(state="normal")
        except Exception as e:
            messagebox.showerror("Error", f"Error al reproducir:\n{e}")

    def toggle_play_pause(self):
        if self.original_audio is None:
            return
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def pause(self):
        if self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
            self.play_btn.configure(text="\u23F8")
        elif self.is_playing:
            pygame.mixer.music.pause()
            self.is_paused = True
            self.play_btn.configure(text="\u25B6")

    def stop(self):
        pygame.mixer.music.stop()
        self.is_playing = False
        self.is_paused = False
        self.playback_pos = 0.0
        self._play_start_pos = 0.0
        self.play_btn.configure(text="\u25B6")
        self.stop_btn.configure(state="disabled")
        self.progress_slider.set(0)
        self.time_current.configure(text="0:00")

    def stop_playback(self):
        pygame.mixer.music.stop()
        self.is_playing = False
        self.is_paused = False
        self._play_start_pos = 0.0

    # ─────────────────── File Loading ───────────────────

    def load_file(self, path=None):
        if path is None:
            path = filedialog.askopenfilename(
                title="Seleccionar archivo de audio/video",
                filetypes=[
                    ("Audio/Video",
                     "*" + " *".join(SUPPORTED_EXTENSIONS)),
                    ("Todos los archivos", "*.*"),
                ],
            )
        if not path:
            return

        self.file_path = path
        self.file_name = os.path.basename(path)
        self.file_label.configure(text=f"Archivo: {self.file_name}")
        self.status_label.configure(text=f"Cargando: {self.file_name}...")
        self.root.update_idletasks()

        t = threading.Thread(target=self.load_audio_thread, args=(path,),
                             daemon=True)
        t.start()

    def load_audio_thread(self, path):
        try:
            y, sr = librosa.load(path, sr=44100, mono=False)

            if y.ndim == 1:
                self.is_stereo = False
                self.original_audio = y.astype(np.float32)
            else:
                self.is_stereo = True
                self.original_audio = y.astype(np.float32)

            self.sample_rate = sr
            self.duration = self.original_audio.shape[-1] / sr
            self.processed_audio = None
            self.current_pitch = 0.0

            self.root.after(0, self.on_audio_loaded)
        except Exception as e:
            self.root.after(
                0, lambda: messagebox.showerror(
                    "Error", f"No se pudo cargar el archivo:\n{e}"
                )
            )
            self.root.after(
                0, lambda: self.status_label.configure(text="Error al cargar")
            )

    def on_audio_loaded(self):
        mins = int(self.duration // 60)
        secs = int(self.duration % 60)
        self.duration_label.configure(text=f"Duración: {mins}:{secs:02d}")
        self.time_total.configure(text=f"{mins}:{secs:02d}")

        ch = "Estéreo" if self.is_stereo else "Mono"
        self.info_label.configure(
            text=f"{self.sample_rate} Hz | {ch}"
        )

        self.play_btn.configure(state="normal", text="\u25B6")
        self.stop_btn.configure(state="disabled")
        self.seek_back_btn.configure(state="normal")
        self.seek_fwd_btn.configure(state="normal")
        self.export_btn.configure(state="normal")
        self.procesar_btn.configure(state="normal")
        self.pitch_down_btn.configure(state="normal")
        self.pitch_up_btn.configure(state="normal")
        self.reset_btn.configure(state="normal")
        self.progress_slider.set(0)
        self.time_current.configure(text="0:00")

        self.draw_waveform()

        self.status_label.configure(text=f"Listo: {self.file_name}")

    # ─────────────────── Waveform ───────────────────

    def draw_waveform(self, event=None):
        canvas = self.waveform_canvas
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w <= 5 or h <= 5:
            self.root.after(200, self.draw_waveform)
            return

        canvas.delete("all")

        if self.original_audio is None:
            return

        y = self.original_audio[0] if self.is_stereo else self.original_audio

        step = max(1, len(y) // w)
        samples = y[::step]
        max_val = np.max(np.abs(samples))
        if max_val > 0:
            samples = samples / max_val

        cy = h / 2.0
        amp = h * 0.42
        points = []
        n = len(samples)

        for i in range(0, n, 2):
            s = samples[i]
            x = (i / n) * w
            points.extend([x, cy + s * amp])

        if len(points) >= 4:
            canvas.create_line(points, fill="#3b8ed0", width=1, smooth=True)

    # ─────────────────── YouTube ───────────────────

    def download_youtube(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Aviso", "Ingresa una URL")
            return

        self.status_label.configure(text="Descargando audio...")
        self.dl_btn.configure(state="disabled", text="Descargando...")
        self.root.update_idletasks()

        t = threading.Thread(
            target=self.download_thread, args=(url,), daemon=True
        )
        t.start()

    def download_thread(self, url):
        try:
            tmpl = os.path.join(DESCARGAS_DIR, "%(title)s.%(ext)s")
            opts = {
                'format': 'bestaudio',
                'outtmpl': tmpl,
                'restrictfilenames': True,
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }

            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'audio')
                filename = ydl.prepare_filename(info)

                downloaded = None
                if os.path.exists(filename):
                    downloaded = filename
                else:
                    base = os.path.splitext(filename)[0]
                    for f in os.listdir(TEMP_DIR):
                        fpath = os.path.join(TEMP_DIR, f)
                        if os.path.isfile(fpath) and f.startswith(os.path.basename(base)):
                            downloaded = fpath
                            break

                if downloaded and os.path.exists(downloaded):
                    fp = downloaded
                    self.root.after(
                        0, lambda p=fp: self.load_file(p)
                    )
                    self.root.after(
                        0, lambda t=title: self.status_label.configure(
                            text=f"Descargado: {t}"
                        )
                    )
                else:
                    self.root.after(
                        0, lambda err=filename: self.status_label.configure(
                            text=f"No se encontró: {err}"
                        )
                    )
        except Exception as e:
            self.root.after(
                0, lambda: messagebox.showerror(
                    "Error", f"Error al descargar:\n{e}"
                )
            )
        finally:
            self.root.after(
                0, lambda: self.dl_btn.configure(
                    state="normal", text="Descargar"
                )
            )

    # ─────────────────── Export ───────────────────

    def export_audio(self):
        if self.original_audio is None:
            return

        needs = (
            self.processed_audio is None
            or self.current_pitch != self.last_processed_pitch
            or self.normalize_enabled != self._last_normalize_state
        )
        if needs:
            self.procesar()
            messagebox.showinfo("Aviso", "Primero procesá el audio con el tono deseado, luego exportá.")
            return

        if not self.file_path:
            messagebox.showwarning("Aviso", "No hay archivo original de referencia")
            return

        base = os.path.splitext(os.path.basename(self.file_path))[0]
        semitones_str = f"{self.current_pitch:+.1f}st".replace(".", "_")
        ext = os.path.splitext(self.file_path)[1].lower()
        if ext not in ('.wav', '.mp3', '.flac', '.ogg'):
            ext = '.wav'
        filename = f"{base}_{semitones_str}{ext}"
        path = os.path.join(CONVERTIDOS_DIR, filename)

        # Evitar sobrescribir
        counter = 1
        while os.path.exists(path):
            name = f"{base}_{semitones_str}_{counter}{ext}"
            path = os.path.join(CONVERTIDOS_DIR, name)
            counter += 1

        self.status_label.configure(text="Exportando...")
        t = threading.Thread(
            target=self.export_thread, args=(path,), daemon=True
        )
        t.start()

    def export_thread(self, path):
        try:
            ext = os.path.splitext(path)[1].lower()

            if self.is_stereo:
                audio_out = self.processed_audio.T
            else:
                audio_out = self.processed_audio

            if ext == '.mp3':
                from pydub import AudioSegment
                import io

                buf = io.BytesIO()
                sf.write(buf, audio_out, self.sample_rate, format='WAV')
                buf.seek(0)
                seg = AudioSegment.from_wav(buf)
                seg.export(path, format='mp3', bitrate='192k')
            else:
                sf.write(path, audio_out, self.sample_rate)

            self.root.after(
                0, lambda p=path: self.status_label.configure(
                    text=f"Exportado: {os.path.basename(p)}"
                )
            )
            self.root.after(
                0, lambda p=path: messagebox.showinfo(
                    "Éxito", f"Audio exportado:\n{p}"
                )
            )
        except Exception as e:
            self.root.after(
                0, lambda: messagebox.showerror(
                    "Error", f"Error al exportar:\n{e}"
                )
            )
            self.root.after(
                0, lambda: self.status_label.configure(text="Error al exportar")
            )

    # ─────────────────── Timer ───────────────────

    def update_timer(self):
        try:
            if self.is_playing and not self.is_paused:
                pos_ms = pygame.mixer.music.get_pos()
                if pos_ms >= 0:
                    self.playback_pos = self._play_start_pos + (pos_ms / 1000.0)

                    if self.duration > 0:
                        ratio = min(1.0, self.playback_pos / self.duration)
                        self.progress_slider.set(ratio * 100)

                    m = int(self.playback_pos // 60)
                    s = int(self.playback_pos % 60)
                    self.time_current.configure(text=f"{m}:{s:02d}")

                    if self.playback_pos >= self.duration - 0.3:
                        self.stop()
                else:
                    if self.is_playing:
                        self.stop()
        except Exception:
            pass

        self.root.after(100, self.update_timer)

    # ─────────────────── Cleanup ───────────────────

    def on_close(self):
        self.stop()
        pygame.mixer.quit()
        try:
            shutil.rmtree(TEMP_DIR, ignore_errors=True)
        except Exception:
            pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = PitchShifterApp()
    app.run()
