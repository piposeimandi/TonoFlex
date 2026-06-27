# TonoFlex

Aplicación de escritorio para ajustar el tono de audio y video **sin cambiar la velocidad**.

## Características

- Carga archivos de audio/video (MP3, WAV, FLAC, MP4, AVI, etc.)
- Descarga audio desde YouTube (mejor calidad original, sin transcodificar)
- Ajuste de tono de **-5 a +6 semitonos** con botones de ±1
- La duración del audio **no se modifica** (pitch shifting puro)
- Normalización opcional de pico con techo configurable
- Reproducción con seek (barra de progreso, waveform, botones ◀10s/▶10s)
- Exportación automática a `convertidos/` con el nombre original + semitonos
- Atajos de teclado: Espacio (play/pause), ← → (seek), ↑ ↓ (tono)

## Requisitos

- Python 3.11+
- ffmpeg (para carga de formatos varios y YouTube)

## Instalación

### Desde el .deb

```bash
sudo dpkg -i tonoflex_1.0.0_all.deb
sudo apt install -f
```

### Manual

```bash
python3 -m venv /tmp/audio_app_venv
/tmp/audio_app_venv/bin/pip install customtkinter pydub pygame pyrubberband numpy resampy librosa soundfile yt-dlp Pillow
./run.sh
```

## Estructura

```
TonoFlex/
├── pitch_shifter_app.py   # Aplicación principal
├── run.sh                 # Lanzador
├── build-deb.sh           # Genera .deb
├── install-desktop.sh     # Instala acceso en el menú
├── descargas/             # Audios de YouTube (se crea automáticamente)
├── convertidos/           # Audios exportados (se crea automáticamente)
└── pitch-shifter.png      # Icono
```

## Uso

1. Cargar un archivo o pegar una URL de YouTube
2. Ajustar el tono con el slider o los botones -1/+1
3. Presionar **Procesar** para aplicar el cambio
4. Presionar **Play** para pre-escuchar
5. Presionar **Exportar** para guardar en `convertidos/`
