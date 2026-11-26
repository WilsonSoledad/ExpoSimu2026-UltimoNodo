"""
Sprites y audio del juego (carpeta juego/assets).

    assets/sprites/<nombre>_<cuadro>.png   cuadros de animación (paquete, gusano, ...)
    assets/audio/musica/<archivo>.ogg      música por pantalla y nivel (config.MUSICA)
    assets/audio/efectos/<evento>.ogg      un efecto por evento del juego

Si un archivo falta o el equipo no tiene salida de audio, el juego sigue
funcionando: un sprite ausente se dibuja con su figura geométrica y un
sonido ausente simplemente no suena. Los créditos están en
assets/audio/CREDITOS.md.

Interfaz:
    iniciar()                      después de pygame.display.set_mode()
    sprite(nombre, t, fase=0)      cuadro de la animación o None
    sonar(evento)
    musica(archivo)                cambia la pista (no la reinicia si es la misma)
"""
from pathlib import Path

import pygame

import config as C

ASSETS = Path(__file__).resolve().parent / "assets"

_sprites = {}
_sonidos = {}
_audio = False
_pista = None


def iniciar():
    global _audio
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        _audio = True
    except pygame.error:
        _audio = False             # sin dispositivo de audio: el juego sigue en silencio
    _cargar_sprites()
    if _audio:
        _cargar_efectos()


def _cargar_sprites():
    carpeta = ASSETS / "sprites"
    for archivo in sorted(carpeta.glob("*_*.png")):
        nombre, _, cuadro = archivo.stem.rpartition("_")
        if not cuadro.isdigit():
            continue
        _sprites.setdefault(nombre, []).append((int(cuadro), pygame.image.load(str(archivo)).convert_alpha()))
    for nombre in _sprites:
        _sprites[nombre] = [img for _, img in sorted(_sprites[nombre], key=lambda par: par[0])]


def _cargar_efectos():
    for archivo in (ASSETS / "audio" / "efectos").glob("*.ogg"):
        try:
            sonido = pygame.mixer.Sound(str(archivo))
            sonido.set_volume(C.VOLUMEN_EFECTOS)
            _sonidos[archivo.stem] = sonido
        except pygame.error:
            pass


def sprite(nombre, t, fase=0):
    """Cuadro de la animación 'nombre' en el instante t (s), o None si no hay sprite."""
    cuadros = _sprites.get(nombre)
    if not cuadros:
        return None
    return cuadros[(int(t * C.CUADROS_POR_SEGUNDO) + fase) % len(cuadros)]


def sonar(evento):
    sonido = _sonidos.get(evento)
    if sonido:
        sonido.play()


def musica(archivo):
    global _pista
    if not _audio or archivo == _pista:
        return
    _pista = archivo
    ruta = ASSETS / "audio" / "musica" / archivo
    try:
        pygame.mixer.music.load(str(ruta))
        pygame.mixer.music.set_volume(C.VOLUMEN_MUSICA)
        pygame.mixer.music.play(-1)
    except pygame.error:
        pass
