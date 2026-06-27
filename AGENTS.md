# TonoFlex — Agent Instructions

## Repo
https://github.com/piposeimandi/TonoFlex

## Build & Run

```bash
./run.sh                          # Run from project directory
/tmp/audio_app_venv/bin/python pitch_shifter_app.py  # Run with venv
```

## Recreate virtual environment

```bash
python3 -m venv /tmp/audio_app_venv
/tmp/audio_app_venv/bin/pip install customtkinter pydub pygame pyrubberband numpy resampy librosa soundfile yt-dlp Pillow
```

## Build .deb package

```bash
./build-deb.sh
# Genera tonoflex_1.0.0_all.deb
```

## Install desktop entry

```bash
./install-desktop.sh
# Aparece "TonoFlex" en el menú de aplicaciones
```

## Create GitHub release

```bash
gh release create v1.0.0 tonoflex_1.0.0_all.deb --title "TonoFlex v1.0.0" --notes "Notas del release"
```

## Push to git

```bash
git add -A && git commit -m "mensaje"
git push origin main
git push origin dev
```

## Code conventions

- UI: CustomTkinter (ctk) with dark theme
- Audio processing: librosa (`librosa.effects.pitch_shift` with `res_type='kaiser_best'`)
- Playback: pygame.mixer.music with `_play_start_pos` tracking for accurate seek
- File I/O: soundfile (WAV), pydub (MP3 export)
- YouTube: yt-dlp (bestaudio, no transcoding, saves to `descargas/`)
- Export: auto-save to `convertidos/` with filename `{original}_{semitones}st.wav`
- Pitch always applied relative to original audio (`self.original_audio`)
- Processing runs in a daemon thread with progress bar + wait cursor
- Only processes on explicit "Procesar" button, Play, or Export
- Thread safety: use `self.root.after(0, callback)` for UI updates from threads
- GUI layout uses `grid()` with columnconfigure weights for responsiveness
- Pitch range: -5 to +6 semitones, buttons for ±1
- Seek: progress slider, waveform click, ◀10s/▶10s buttons, keyboard ← →
- Normalization: optional peak normalization with configurable ceiling
