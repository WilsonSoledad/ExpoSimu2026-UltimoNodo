"""Entidades del juego: camino, paquetes, gusanos, escáneres y puertas."""
import math

from config import CELDA, CAMPO_X, CAMPO_Y, VEL_PAQUETE


def centro_celda(col, fila):
    return (CAMPO_X + col * CELDA + CELDA / 2, CAMPO_Y + fila * CELDA + CELDA / 2)


def celda_de(x, y):
    return int((x - CAMPO_X) // CELDA), int((y - CAMPO_Y) // CELDA)


class Camino:
    """Polilínea definida por celdas; permite ubicar un punto por distancia recorrida."""

    def __init__(self, celdas):
        self.vertices = celdas
        self.puntos = [centro_celda(c, f) for c, f in celdas]
        self.acumulado = [0.0]
        for (x0, y0), (x1, y1) in zip(self.puntos, self.puntos[1:]):
            self.acumulado.append(self.acumulado[-1] + math.hypot(x1 - x0, y1 - y0))
        self.largo = self.acumulado[-1]
        self.celdas = set()
        for (c0, f0), (c1, f1) in zip(celdas, celdas[1:]):
            for c in range(min(c0, c1), max(c0, c1) + 1):
                for f in range(min(f0, f1), max(f0, f1) + 1):
                    self.celdas.add((c, f))

    def punto(self, s):
        s = max(0.0, min(s, self.largo))
        for i in range(len(self.puntos) - 1):
            if s <= self.acumulado[i + 1]:
                tramo = self.acumulado[i + 1] - self.acumulado[i]
                u = (s - self.acumulado[i]) / tramo if tramo else 0.0
                (x0, y0), (x1, y1) = self.puntos[i], self.puntos[i + 1]
                return x0 + u * (x1 - x0), y0 + u * (y1 - y0)
        return self.puntos[-1]


class Paquete:
    """Amenaza que recorre el camino y hace fila en las puertas (colas)."""
    _siguiente_id = 0

    def __init__(self, s=0.0, sig_puerta=0, tipo="paquete"):
        Paquete._siguiente_id += 1
        self.id = Paquete._siguiente_id
        self.s = s
        self.sig_puerta = sig_puerta
        self.tipo = tipo            # "paquete" o "bot" (bot que entró al camino)
        self.estado = "moviendo"    # moviendo | puerta
        self.puerta = None
        self.brecha = False

    def avanzar(self, dt):
        self.s += VEL_PAQUETE * dt


class Gusano:
    """Se mueve por la grilla con la caminata aleatoria."""

    def __init__(self, col, fila):
        self.col, self.fila = col, fila
        self.pasos = 0
        self.rastro = []


class Escaner:
    def __init__(self, col, fila):
        self.col, self.fila = col, fila
        self.reloj = 0.0
        self.destello = 0.0


class Puerta:
    """Firewall ubicado sobre el camino; su lógica es el modelo de colas."""

    def __init__(self, indice, camino, fraccion, modelo):
        self.indice = indice
        self.s = fraccion * camino.largo
        self.x, self.y = camino.punto(self.s)
        self.modelo = modelo

    def debilidad(self):
        """Qué tan vulnerable es (lo usan los bots): ocupada y con pocos servidores."""
        m = self.modelo
        return m.en_sistema() / m.K - 0.25 * m.c

    def contiene(self, x, y):
        return math.hypot(x - self.x, y - self.y) < 24
