"""
Generadores de números pseudoaleatorios del juego.

Se reutilizan los generadores del Taller 1 tal como están en los módulos
(carpeta ../modulos), envueltos en clases con estado para poder
pedir un número a la vez:

    CongruencialMultiplicativo   x_{i+1} = a x_i mod m          (Park-Miller, modelo 1)
    CongruencialLineal           x_{i+1} = (a x_i + c) mod m    (Hull-Dobell, modelo 2)

Interfaz que el juego espera de cualquier generador:
    gen.random() -> float en [0, 1)
    gen.nombre   -> str   (se muestra en el modo ingeniero y va al informe)
"""
import math
import time

from fuentes import modelo1, modelo2


class CongruencialMultiplicativo:
    """Congruencial multiplicativo del Taller 1 (Park-Miller: a = 16807, m = 2^31 - 1)."""

    def __init__(self, semilla=12345, a=16807, m=2 ** 31 - 1):
        self.a, self.m = a, m
        self.x = int(semilla) % m or 1          # la semilla no puede ser 0
        self.nombre = f"Congruencial multiplicativo (a={a}, m=2^31-1)"

    def random(self):
        xs, rs = modelo1.congruencial_multiplicativo(self.x, self.a, self.m, 1)
        self.x = xs[0]
        return rs[0]


class CongruencialLineal:
    """Congruencial lineal mixto del Taller 1 (a = 1664525, c = 1013904223, m = 2^32)."""

    def __init__(self, semilla=12345, a=1664525, c=1013904223, m=2 ** 32):
        self.a, self.c, self.m = a, c, m
        self.x = int(semilla) % m
        self.nombre = f"Congruencial lineal (a={a}, c={c}, m=2^32)"

    def random(self):
        xs, rs = modelo2.congruencial_lineal(self.x, self.a, self.c, self.m, 1)
        self.x = xs[0]
        return rs[0]


# ------------------------------------------------------------------ utilidades
def uniforme(gen, a, b):
    """N_i = a + (b - a) R_i"""
    return a + (b - a) * gen.random()


def entero(gen, a, b):
    """Entero uniforme en [a, b]."""
    return min(b, a + int(gen.random() * (b - a + 1)))


def exponencial(gen, tasa):
    """Transformada inversa: t = -ln(1 - U) / tasa."""
    return -math.log(1.0 - gen.random()) / tasa


def bernoulli(gen, p):
    return gen.random() < p


def por_intervalos(gen, opciones, probabilidades):
    """Matriz Monte Carlo: ubica R_i en el intervalo acumulado que le corresponde."""
    r = gen.random()
    acumulado = 0.0
    for opcion, p in zip(opciones, probabilidades):
        acumulado += p
        if r < acumulado:
            return opcion
    return opciones[-1]


def crear_flujos(semilla_base=None):
    """Un flujo (generador independiente) por cada fuente de aleatoriedad.

    Como se vio en clase, los tiempos de llegada y los de servicio usan
    juegos de números distintos. Las colas usan el generador del modelo 1 y
    el resto el del modelo 2, ambos del Taller 1.
    """
    if semilla_base is None:
        semilla_base = int(time.time())
    tipos = {
        "llegadas": CongruencialMultiplicativo,
        "servicio": CongruencialMultiplicativo,
        "caminata": CongruencialLineal,
        "montecarlo": CongruencialLineal,
        "agentes": CongruencialLineal,
        "general": CongruencialLineal,
    }
    return {n: clase(semilla_base + 7919 * (i + 1)) for i, (n, clase) in enumerate(tipos.items())}
