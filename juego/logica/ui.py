"""Dibujo de la escena, el HUD, el panel lateral, el modo ingeniero y los menús.

Los gráficos son figuras geométricas provisionales; se reemplazan por los
sprites del integrante 3 sin tocar la lógica.
"""
import math

import pygame

import config as C

COL = {k: pygame.Color(v) for k, v in C.PALETA.items()}


class Fuentes:
    def __init__(self):
        nombres = "dejavusans,arial,segoeui,helvetica"
        self.chica = pygame.font.SysFont(nombres, 13)
        self.normal = pygame.font.SysFont(nombres, 16)
        self.media = pygame.font.SysFont(nombres, 20, bold=True)
        self.grande = pygame.font.SysFont(nombres, 34, bold=True)
        self.titulo = pygame.font.SysFont(nombres, 58, bold=True)


def texto(sup, fuente, cadena, color, pos, centro=False, derecha=False):
    img = fuente.render(cadena, True, color)
    r = img.get_rect()
    if centro:
        r.center = pos
    elif derecha:
        r.topright = pos
    else:
        r.topleft = pos
    sup.blit(img, r)
    return r


def barra(sup, x, y, w, h, fraccion, color, fondo=None):
    pygame.draw.rect(sup, fondo or COL["grilla"], (x, y, w, h), border_radius=4)
    pygame.draw.rect(sup, color, (x, y, int(w * max(0.0, min(1.0, fraccion))), h), border_radius=4)


def velo(sup, alfa=170):
    capa = pygame.Surface((C.ANCHO, C.ALTO), pygame.SRCALPHA)
    capa.fill((5, 8, 18, alfa))
    sup.blit(capa, (0, 0))


# =================================================================== escena
def dibujar_nivel(sup, nivel, f, ingeniero=False):
    sup.fill(COL["fondo"])
    _campo(sup, nivel)
    _puertas_y_paquetes(sup, nivel, f)
    _gusanos(sup, nivel)
    _agentes(sup, nivel)
    _nucleo(sup, nivel)
    _oleada(sup, nivel, f)
    _hud(sup, nivel, f)
    _panel(sup, nivel, f)
    _mensajes(sup, nivel, f)
    if ingeniero:
        _ingeniero(sup, nivel, f)


def _campo(sup, nivel):
    for c in range(C.COLS + 1):
        x = C.CAMPO_X + c * C.CELDA
        pygame.draw.line(sup, COL["grilla"], (x, C.CAMPO_Y), (x, C.CAMPO_Y + C.FILAS * C.CELDA))
    for f in range(C.FILAS + 1):
        y = C.CAMPO_Y + f * C.CELDA
        pygame.draw.line(sup, COL["grilla"], (C.CAMPO_X, y), (C.CAMPO_X + C.COLS * C.CELDA, y))
    pts = nivel.camino.puntos
    for a, b in zip(pts, pts[1:]):
        pygame.draw.line(sup, COL["camino"], a, b, 26)
    for p in pts:
        pygame.draw.circle(sup, COL["camino"], p, 13)
    if nivel.modo_escaner:
        mx, my = pygame.mouse.get_pos()
        col, fila = int((mx - C.CAMPO_X) // C.CELDA), int((my - C.CAMPO_Y) // C.CELDA)
        if 0 <= col < C.COLS and 0 <= fila < C.FILAS:
            valida = (col, fila) not in nivel.camino.celdas
            color = COL["verde"] if valida else COL["naranja"]
            r = pygame.Rect(C.CAMPO_X + (col - 1) * C.CELDA, C.CAMPO_Y + (fila - 1) * C.CELDA,
                            3 * C.CELDA, 3 * C.CELDA)
            pygame.draw.rect(sup, color, r, 1)
    for e in nivel.escaneres:
        x = C.CAMPO_X + e.col * C.CELDA
        y = C.CAMPO_Y + e.fila * C.CELDA
        r = pygame.Rect(x + 8, y + 8, C.CELDA - 16, C.CELDA - 16)
        pygame.draw.rect(sup, COL["verde"], r, 2, border_radius=3)
        pygame.draw.circle(sup, COL["verde"], r.center, 3)
        if e.destello > 0:
            pygame.draw.rect(sup, COL["verde"], (x - C.CELDA, y - C.CELDA, 3 * C.CELDA, 3 * C.CELDA), 1)


def _rombo(sup, color, x, y, r):
    pygame.draw.polygon(sup, color, [(x, y - r), (x + r, y), (x, y + r), (x - r, y)])


def _puertas_y_paquetes(sup, nivel, f):
    for p in nivel.paquetes.values():
        if p.estado == "moviendo":
            x, y = nivel.camino.punto(p.s)
            color = COL["naranja"] if p.brecha else (COL["violeta"] if p.tipo == "bot" else COL["magenta"])
            _rombo(sup, color, x, y, 7)
    for pu in nivel.puertas:
        m = pu.modelo
        for p in nivel.paquetes.values():
            if p.estado == "puerta" and p.puerta == pu.indice:
                pos = m.posicion(p.id)
                if not pos:
                    continue
                tipo, i = pos
                if tipo == "servicio":
                    x, y = pu.x - 10 + i * 6, pu.y - 26 - i * 2
                else:
                    x, y = nivel.camino.punto(pu.s - 16 * (i + 1))
                color = COL["violeta"] if p.tipo == "bot" else COL["magenta"]
                _rombo(sup, color, x, y, 6 if tipo == "cola" else 5)
        rect = pygame.Rect(0, 0, 36, 36)
        rect.center = (pu.x, pu.y)
        lleno = m.en_sistema() / m.K
        borde = COL["naranja"] if lleno >= 1 else COL["cian"]
        pygame.draw.rect(sup, COL["fondo"], rect, border_radius=6)
        pygame.draw.rect(sup, borde, rect, 3, border_radius=6)
        barra(sup, rect.x + 4, rect.bottom - 9, rect.w - 8, 5, lleno, borde)
        texto(sup, f.chica, f"c{m.c}", COL["texto"], (pu.x, pu.y - 5), centro=True)
        texto(sup, f.chica, f"K{m.K} μ{m.mu:.2f}", COL["texto2"], (pu.x, pu.y + 24), centro=True)


def _gusanos(sup, nivel):
    for g in nivel.gusanos:
        for k, (c, fl) in enumerate(g.rastro):
            x = C.CAMPO_X + c * C.CELDA + C.CELDA / 2
            y = C.CAMPO_Y + fl * C.CELDA + C.CELDA / 2
            pygame.draw.circle(sup, COL["rojo"], (x, y), 2 + k // 2, 1)
        x = C.CAMPO_X + g.col * C.CELDA + C.CELDA / 2
        y = C.CAMPO_Y + g.fila * C.CELDA + C.CELDA / 2
        if g.generacion > 0:
            # Hidra (generación 2) o fragmento (1): más grande, con una cabeza por generación
            r = 8 + 4 * g.generacion
            pygame.draw.circle(sup, COL["rojo"], (x, y), r)
            pygame.draw.circle(sup, COL["naranja"], (x, y), r + 3, 2)
            for k in range(g.generacion + 1):
                ang = -math.pi / 2 + (k - g.generacion / 2) * 0.9
                pygame.draw.circle(sup, COL["fondo"], (x + (r - 4) * math.cos(ang), y + (r - 4) * math.sin(ang)), 2)
        else:
            pygame.draw.circle(sup, COL["rojo"], (x, y), 7)
            pygame.draw.circle(sup, COL["fondo"], (x + 2, y - 2), 2)


def _agentes(sup, nivel):
    if not nivel.agentes:
        return
    for b in nivel.agentes.bots:
        ang = b.theta           # el triángulo apunta en la dirección real del rumbo
        pts = [(b.x + 9 * math.cos(ang), b.y + 9 * math.sin(ang)),
               (b.x + 7 * math.cos(ang + 2.5), b.y + 7 * math.sin(ang + 2.5)),
               (b.x + 7 * math.cos(ang - 2.5), b.y + 7 * math.sin(ang - 2.5))]
        pygame.draw.polygon(sup, COL["violeta"], pts)


def _nucleo(sup, nivel):
    x, y = nivel.camino.puntos[-1]
    pulso = 3 * math.sin(nivel.t * 4)
    color = COL["cian"] if nivel.integridad > 30 else COL["naranja"]
    pygame.draw.circle(sup, color, (x, y), 22 + pulso, 3)
    hexagono = [(x + 14 * math.cos(math.pi / 3 * k), y + 14 * math.sin(math.pi / 3 * k)) for k in range(6)]
    pygame.draw.polygon(sup, color, hexagono)


def _oleada(sup, nivel, f):
    """Indicador de la oleada en la parte superior del campo."""
    x, y = C.PANEL_X // 2, C.HUD_ALTO + 14
    if nivel.estado != "jugando" or nivel.t >= nivel.n_oleadas * nivel.ciclo:
        return
    if nivel.en_oleada:
        resta = C.OLEADA_DURACION - nivel.t_fase
        texto(sup, f.normal, f"Oleada {nivel.oleada} de {nivel.n_oleadas} · {resta:.0f} s",
              COL["magenta"], (x, y), centro=True)
    else:
        resta = C.OLEADA_PAUSA - nivel.t_fase
        texto(sup, f.media, f"Preparación · oleada {nivel.oleada} de {nivel.n_oleadas} en {resta:.0f} s",
              COL["amarillo"], (x, y + 4), centro=True)


# =================================================================== HUD
def _hud(sup, nivel, f):
    pygame.draw.rect(sup, COL["panel"], (0, 0, C.ANCHO, C.HUD_ALTO))
    pygame.draw.line(sup, COL["cian"], (0, C.HUD_ALTO - 1), (C.ANCHO, C.HUD_ALTO - 1))
    texto(sup, f.media, f"Nivel {nivel.indice + 1}: {nivel.cfg['nombre']}", COL["cian"], (14, 8))
    texto(sup, f.chica, nivel.cfg["descripcion"], COL["texto2"], (14, 36))

    x = 470
    texto(sup, f.chica, "Integridad", COL["texto2"], (x, 8))
    barra(sup, x, 26, 150, 12, nivel.integridad / 100,
          COL["cian"] if nivel.integridad > 30 else COL["naranja"])
    texto(sup, f.chica, f"{nivel.integridad:.0f} %", COL["texto"], (x + 156, 24))

    x = 680
    texto(sup, f.chica, "Respaldo", COL["texto2"], (x, 8))
    barra(sup, x, 26, 150, 12, nivel.respaldo / 100, COL["verde"])
    texto(sup, f.chica, f"{nivel.respaldo:.0f} %", COL["texto"], (x + 156, 24))

    x = 890
    texto(sup, f.chica, "Energía", COL["texto2"], (x, 8))
    texto(sup, f.media, f"{nivel.energia:.0f}", COL["amarillo"], (x, 24))
    texto(sup, f.chica, f"Parches: {nivel.parches}", COL["texto2"], (x + 70, 28))


def _panel(sup, nivel, f):
    x0 = C.PANEL_X
    pygame.draw.rect(sup, COL["panel"], (x0, C.HUD_ALTO, C.PANEL_ANCHO, C.ALTO - C.HUD_ALTO))
    pygame.draw.line(sup, COL["grilla"], (x0, C.HUD_ALTO), (x0, C.ALTO))
    x, y = x0 + 16, C.HUD_ALTO + 12

    texto(sup, f.media, "Red interna", COL["texto"], (x, y))
    y += 28
    if nivel.sir:
        s = nivel.sir
        orden = [COL["verde"]] * int(round(s.S)) + [COL["rojo"]] * int(round(s.I)) + [COL["cian"]] * int(round(s.R))
        orden = (orden + [COL["verde"]] * 100)[:100]
        for k, color in enumerate(orden):
            cx = x + 6 + (k % 20) * 13
            cy = y + 6 + (k // 20) * 13
            pygame.draw.circle(sup, color, (cx, cy), 4)
        y += 70
        texto(sup, f.chica, f"S {s.S:5.1f}   I {s.I:5.1f}   R {s.R:5.1f}", COL["texto"], (x, y))
        y += 18
        umbral = nivel.cfg["umbral_infeccion"]
        barra(sup, x, y, 250, 8, s.fraccion_infectada() / umbral, COL["rojo"])
        y += 12
        texto(sup, f.chica, f"Infección {s.fraccion_infectada() * 100:.0f} % (límite {umbral * 100:.0f} %)",
              COL["texto2"], (x, y))
        if s.parche_restante > 0:
            texto(sup, f.chica, f"Parche activo {s.parche_restante:.0f} s", COL["verde"], (x + 175, y - 30))
        y += 26
    else:
        texto(sup, f.chica, "Sin infección en este nivel.", COL["texto2"], (x, y))
        y += 30

    texto(sup, f.media, "Predictor", COL["texto"], (x, y))
    y += 26
    if nivel.prediccion:
        p, margen, n, _ = nivel.prediccion
        color = COL["naranja"] if p > 0.5 else COL["verde"]
        texto(sup, f.normal, f"P(brecha) = {p:.2f} ± {margen:.2f}", color, (x, y))
        texto(sup, f.chica, f"{n} simulaciones de una oleada ({C.OLEADA_DURACION:.0f} s)",
              COL["texto2"], (x, y + 20))
    elif nivel.mc:
        texto(sup, f.chica, "Pulsa P para simular la próxima oleada.", COL["texto2"], (x, y))
    else:
        texto(sup, f.chica, "Se desbloquea en el nivel 2.", COL["texto2"], (x, y))
    y += 50

    texto(sup, f.media, "Controles", COL["texto"], (x, y))
    y += 26
    ayuda = [
        ("Clic izq. en puerta", f"+1 servidor ({C.COSTOS['servidor']})"),
        ("Clic der. en puerta", f"+2 capacidad ({C.COSTOS['capacidad']})"),
        ("Shift + clic puerta", f"μ + {C.MU_PASO:.2f} ({C.COSTOS['servicio']})"),
        ("E + clic", f"Escáner ({C.COSTOS['escaner']})" + ("  [ACTIVO]" if nivel.modo_escaner else "")),
        ("P", f"Predictor ({C.COSTOS['predictor']})"),
        ("H", f"Parche ({C.COSTOS['parche']} o gratis)"),
        ("S", f"Segmentar red ({C.COSTOS['segmentar']})"),
        ("F1", "Modo ingeniero"),
        ("V", "Velocidad x1 / x2"),
        ("ESC", "Pausa"),
    ]
    for tecla, desc in ayuda:
        texto(sup, f.chica, tecla, COL["cian"], (x, y))
        texto(sup, f.chica, desc, COL["texto"], (x + 120, y))
        y += 18

    y = C.ALTO - 44
    texto(sup, f.chica, f"Eliminadas: {nivel.eliminados}   Brechas: {nivel.brechas}", COL["texto2"], (x, y))
    texto(sup, f.chica, f"Tiempo: {nivel.t:5.1f} s", COL["texto2"], (x, y + 18))


def _mensajes(sup, nivel, f):
    y = C.ALTO - 30
    for cadena, color, _ in reversed(nivel.mensajes):
        texto(sup, f.normal, cadena, color, (C.PANEL_X // 2, y), centro=True)
        y -= 22


def _fmt(v):
    if isinstance(v, float) and math.isnan(v):
        return "—"
    if isinstance(v, int):
        return str(v)
    return f"{v:.3f}"


def _ingeniero(sup, nivel, f):
    capa = pygame.Surface((C.PANEL_X - 40, C.ALTO - C.HUD_ALTO - 40), pygame.SRCALPHA)
    capa.fill((5, 8, 18, 225))
    sup.blit(capa, (20, C.HUD_ALTO + 20))
    x, y = 36, C.HUD_ALTO + 30
    texto(sup, f.media, "MODO INGENIERO · observado vs. teórico", COL["amarillo"], (x, y))
    texto(sup, f.chica, f"Generador: {nivel.flujos['llegadas'].nombre}", COL["texto2"], (x, y + 24))
    y += 48
    columna = 0
    for titulo, filas in nivel.metricas_ingeniero():
        alto = 20 + 16 * len(filas) + 8
        if y + alto > C.ALTO - 30:
            columna += 1
            x, y = 36 + columna * 380, C.HUD_ALTO + 78
        texto(sup, f.normal, titulo, COL["cian"], (x, y))
        y += 20
        for nombre, obs, teo in filas:
            texto(sup, f.chica, nombre, COL["texto"], (x, y))
            texto(sup, f.chica, _fmt(obs), COL["verde"], (x + 230, y), derecha=True)
            texto(sup, f.chica, _fmt(teo), COL["texto2"], (x + 300, y), derecha=True)
            if isinstance(obs, (int, float)) and isinstance(teo, float) and teo and not math.isnan(teo) \
                    and not (isinstance(obs, float) and math.isnan(obs)):
                dif = abs(obs - teo) / abs(teo) * 100
                texto(sup, f.chica, f"{dif:.1f}%", COL["amarillo"], (x + 355, y), derecha=True)
            y += 16
        y += 8
    texto(sup, f.chica, "verde: observado · gris: teórico · amarillo: diferencia %",
          COL["texto2"], (36, C.ALTO - 40))


# =================================================================== pantallas
def pantalla_menu(sup, f, opciones, seleccion, t):
    sup.fill(COL["fondo"])
    for k in range(40):
        x = (k * 97 + t * 30 * (1 + k % 3)) % C.ANCHO
        y = (k * 53) % C.ALTO
        _rombo(sup, COL["grilla"], x, y, 4)
    texto(sup, f.titulo, "ÚLTIMO NODO", COL["cian"], (C.ANCHO // 2, 170), centro=True)
    texto(sup, f.normal, "Resiste hasta que el respaldo del Núcleo llegue al 100 %",
          COL["texto2"], (C.ANCHO // 2, 225), centro=True)
    for i, op in enumerate(opciones):
        color = COL["amarillo"] if i == seleccion else COL["texto"]
        marca = "▶  " if i == seleccion else ""
        texto(sup, f.grande, marca + op, color, (C.ANCHO // 2, 320 + i * 56), centro=True)
    texto(sup, f.chica, "Flechas + Enter · ExpoSimu 2026 · Simulación por computador · UPTC",
          COL["texto2"], (C.ANCHO // 2, C.ALTO - 30), centro=True)


def pantalla_controles(sup, f):
    sup.fill(COL["fondo"])
    texto(sup, f.grande, "Controles", COL["cian"], (C.ANCHO // 2, 70), centro=True)
    filas = [
        ("Clic izquierdo en una puerta", "Agregar un servidor (c + 1)"),
        ("Clic derecho en una puerta", "Ampliar capacidad (K + 2)"),
        ("Shift + clic izquierdo en una puerta", f"Mejorar servicio (μ + {C.MU_PASO:.2f})"),
        ("E, luego clic en una celda", "Instalar escáner contra gusanos"),
        ("P", "Predictor Monte Carlo"),
        ("H", "Aplicar parche a la red (γ × 3)"),
        ("S", "Segmentar la red (β × 0,75)"),
        ("F1", "Modo ingeniero (observado vs. teórico)"),
        ("V", "Velocidad normal / doble"),
        ("ESC", "Pausa"),
    ]
    y = 140
    for tecla, desc in filas:
        texto(sup, f.normal, tecla, COL["amarillo"], (220, y))
        texto(sup, f.normal, desc, COL["texto"], (560, y))
        y += 36
    texto(sup, f.normal, "Enter o ESC para volver", COL["texto2"], (C.ANCHO // 2, C.ALTO - 50), centro=True)


def pantalla_pausa(sup, f):
    velo(sup)
    texto(sup, f.grande, "PAUSA", COL["cian"], (C.ANCHO // 2, 230), centro=True)
    for i, linea in enumerate(["ESC  continuar", "R  reiniciar nivel", "M  menú principal"]):
        texto(sup, f.normal, linea, COL["texto"], (C.ANCHO // 2, 300 + i * 32), centro=True)


def pantalla_resultado(sup, f, titulo, color, lineas, pie):
    velo(sup, 200)
    texto(sup, f.titulo, titulo, color, (C.ANCHO // 2, 210), centro=True)
    for i, linea in enumerate(lineas):
        texto(sup, f.normal, linea, COL["texto"], (C.ANCHO // 2, 290 + i * 28), centro=True)
    texto(sup, f.normal, pie, COL["amarillo"], (C.ANCHO // 2, 290 + len(lineas) * 28 + 40), centro=True)
