# Copiex sounds

Aquí vive la alarma que suena cuando una copia termina. Para cambiarla, descarga
el sonido que quieras y déjalo en esta carpeta; no hay que tocar el código.

Reglas para elegir el fichero:

- Manda `copy-finished.*` (el que viene incluido). Sustitúyelo por el tuyo con el
  mismo nombre, o bórralo.
- Si no existe ese nombre, se usa el primer fichero de audio por orden
  alfabético de la carpeta. Lo más claro: deja **un único** fichero aquí.
- Si la carpeta está vacía (o no hay reproductor que entienda el formato), se
  usa el sonido «Complete» del sistema; nunca se queda muda.

Extensiones reconocidas: `.oga`, `.ogg`, `.wav`, `.flac`, `.mp3`, `.opus`,
`.m4a`, `.aac`. Se intenta reproducir con `canberra-gtk-play`, luego `paplay` y,
si el formato no es de los suyos, con `gst-launch-1.0`. OGG y WAV son los más
seguros; MP3 y M4A dependen de GStreamer.

No hace falta reiniciar Copiex: el fichero se busca cada vez que suena la
alarma. Para probar sin esperar a una copia:

```bash
python3 -c "import sys; sys.path.insert(0, '.'); from copiex.sound import reproducir; print(reproducir())"
```

`copy-finished.wav` es un tono corto generado para este proyecto (dos notas
ascendentes, medio segundo), sin derechos de terceros: puedes borrarlo sin más.
