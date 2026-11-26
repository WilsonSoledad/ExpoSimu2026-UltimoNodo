"""
Procesa las tiras de sprites base (4 cuadros cada una) para Último Nodo.

Modificaciones aplicadas a cada sprite:
  1. Separación de la tira en sus 4 cuadros de animación, alineados por la base.
  2. Limpieza: cada píxel se clasifica en contorno, cuerpo o acento (las imágenes
     base tienen ~20 000-30 000 colores por ruido de compresión); la transparencia
     se binariza para obtener bordes nítidos.
  3. Reducción a la resolución del juego por mayoría de clase en cada bloque
     (pixel art sin suavizado), al tamaño que ocupa cada entidad en la grilla de 40 px.
  4. Recoloreado a la paleta del juego (config.py): cuerpo con el color del rol,
     contorno con ese color oscurecido y acento con un color de alerta.

Uso (desde la raíz del repositorio):
    python docs/arte/procesar_sprites.py docs/arte/base juego/assets/sprites docs/arte
"""
import colorsys
import sys
from pathlib import Path

import numpy as np
from PIL import Image

PALETA = {
    "magenta": "#FF2E88", "rojo": "#FF3B3B", "violeta": "#9D4EDD",
    "amarillo": "#FFD23F", "naranja": "#FF8C42", "fondo": "#0B1020", "texto": "#E6F1FF",
}

# fuente, nombre en el juego, alto en px, color del cuerpo, color del acento
SPRITES = [
    ("arana.png", "paquete", 22, "magenta", "amarillo"),
    ("serpiente.png", "gusano", 30, "rojo", "amarillo"),
    ("robot.png", "bot", 26, "violeta", "amarillo"),
    ("dragon.png", "hidra", 38, "rojo", "naranja"),
    ("dragon.png", "fragmento", 28, "rojo", "naranja"),   # fragmentos de la Hidra (generación 1)
]

TRANSP, CONTORNO, CUERPO, ACENTO = 0, 1, 2, 3


def hex_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=float)


def clasificar(rgba):
    """Clase de cada píxel: transparente, contorno, cuerpo o acento."""
    alfa = rgba[..., 3] > 128
    rgb = rgba[..., :3].reshape(-1, 3) / 255.0
    hsv = np.array([colorsys.rgb_to_hsv(*p) for p in rgb]).reshape(rgba.shape[0], rgba.shape[1], 3)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    clase = np.full(alfa.shape, CUERPO, dtype=np.uint8)
    clase[v < 0.30] = CONTORNO
    calido = (h > 0.04) & (h < 0.20) & (s > 0.35) & (v >= 0.30)
    clase[calido] = ACENTO
    clase[~alfa] = TRANSP
    return clase


def cuadros(clase):
    """Columnas ocupadas -> segmentos (un segmento por cuadro de animación)."""
    ocupadas = (clase != TRANSP).any(0)
    segs, dentro = [], False
    for x, v in enumerate(ocupadas):
        if v and not dentro:
            ini, dentro = x, True
        elif not v and dentro:
            segs.append((ini, x))
            dentro = False
    if dentro:
        segs.append((ini, len(ocupadas)))
    filas = (clase != TRANSP).any(1).nonzero()[0]
    y0, y1 = filas.min(), filas.max() + 1
    ancho = max(e - s for s, e in segs)
    salida = []
    for s, e in segs:
        lienzo = np.zeros((y1 - y0, ancho), dtype=np.uint8)
        dx = (ancho - (e - s)) // 2
        lienzo[:, dx:dx + (e - s)] = clase[y0:y1, s:e]
        salida.append(lienzo)
    return salida


def reducir(clase, alto):
    """Reduce por mayoría de clase en cada bloque (sin suavizar colores)."""
    h, w = clase.shape
    ancho = max(1, round(w * alto / h))
    capas = []
    for c in (TRANSP, CONTORNO, CUERPO, ACENTO):
        m = Image.fromarray(((clase == c) * 255).astype(np.uint8))
        capas.append(np.array(m.resize((ancho, alto), Image.BOX), dtype=float))
    capas = np.stack(capas)
    opaco = capas[1:].sum(0) > capas[0]          # opaco si la mayoría del bloque es opaca
    clase_red = capas[1:].argmax(0) + 1
    clase_red[~opaco] = TRANSP
    return clase_red.astype(np.uint8)


def colorear(clase, cuerpo, acento):
    c = hex_rgb(PALETA[cuerpo])
    tabla = {
        CONTORNO: c * 0.35,
        CUERPO: c,
        ACENTO: hex_rgb(PALETA[acento]),
    }
    out = np.zeros(clase.shape + (4,), dtype=np.uint8)
    for k, col in tabla.items():
        out[clase == k, :3] = col.astype(np.uint8)
        out[clase == k, 3] = 255
    return Image.fromarray(out, "RGBA")


def main(fuentes, salida, figuras):
    fuentes, salida, figuras = Path(fuentes), Path(salida), Path(figuras)
    salida.mkdir(parents=True, exist_ok=True)
    figuras.mkdir(parents=True, exist_ok=True)
    resumen = []
    for archivo, nombre, alto, cuerpo, acento in SPRITES:
        base = np.array(Image.open(fuentes / archivo).convert("RGBA"))
        n_colores = len(np.unique(base[..., :3][base[..., 3] > 0].reshape(-1, 3), axis=0))
        clase = clasificar(base)
        for i, cuadro in enumerate(cuadros(clase)):
            img = colorear(reducir(cuadro, alto), cuerpo, acento)
            img.save(salida / f"{nombre}_{i}.png")
        resumen.append((nombre, archivo, n_colores, img.size))
    for r in resumen:
        print(f"{r[0]:8s} <- {r[1]:14s} colores base: {r[2]:6d} -> 3 colores; cuadro final {r[3][0]}x{r[3][1]} px")


if __name__ == "__main__":
    main(*sys.argv[1:4])
