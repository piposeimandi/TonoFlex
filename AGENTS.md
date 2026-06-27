# TonoFlex — Agent Instructions

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
```

## Install desktop entry

```bash
./install-desktop.sh
```

## Code conventions

- UI: CustomTkinter (ctk) with dark theme
- Audio processing: librosa (`librosa.effects.pitch_shift` with `res_type='kaiser_best'`)
- Playback: pygame.mixer.music
- File I/O: soundfile (WAV), pydub (MP3 export)
- YouTube: yt-dlp (bestaudio, no transcoding)
- Pitch always applied relative to original audio (`self.original_audio`)
- Processing runs in a daemon thread with progress bar indicator
- Thread safety: use `self.root.after(0, callback)` for UI updates from threads
- GUI layout uses `grid()` with columnconfigure weights for responsiveness
