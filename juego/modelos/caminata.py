"""
Modelo 2 - Caminata aleatoria sesgada en 2D para los gusanos.

Adaptador del módulo de Carrillo (modulos/..._modelo2_caminatas.py): el juego
usa su regla de un paso (paso_caminata), es decir, el método de intervalos
acumulados con probabilidades (p_der, p_izq, p_arr, p_aba), y su generador
congruencial lineal (a = 1664525, c = 1013904223, m = 2^32), que llega
desde aleatorio.CongruencialLineal.

Lo que agrega este archivo es lo propio del juego:
  - la grilla de pantalla tiene el eje y hacia abajo, así que el desvío
    superior del módulo (+Y) es una fila menos en el juego;
  - las paredes (la izquierda y los bordes superior e inferior) las aplica
    logica/nivel.py, no este archivo;
  - lleva los conteos que muestra el modo ingeniero.

Teoría por paso en x:  E[dx] = p_der - p_izq
                       Var[dx] = p_der + p_izq - (p_der - p_izq)^2
Tras n pasos:          E[X_n] = n (p_der - p_izq),  Var[X_n] = n Var[dx]

Interfaz que usa el juego:
    ModeloCaminata(gen, p_der, p_izq, p_arr, p_aba)
    .paso() -> (dx, dy)            un paso sobre la grilla (dy en filas de pantalla)
    .registrar_cruce(pasos)        un gusano llegó al Núcleo tras 'pasos' pasos
    .metricas() -> list[(nombre, observado, teorico)]
"""
from fuentes import modelo2

# Paso del módulo (dx, dy) -> índice de dirección: der, izq, arr, aba
INDICE = {(1, 0): 0, (-1, 0): 1, (0, 1): 2, (0, -1): 3}


class ModeloCaminata:
    nombre = "Caminata aleatoria sesgada"

    def __init__(self, gen, p_der=0.25, p_izq=0.25, p_arr=0.25, p_aba=0.25):
        total = p_der + p_izq + p_arr + p_aba
        if abs(total - 1.0) > 1e-9:
            raise ValueError("Las probabilidades deben sumar 1")
        self.gen = gen
        self.p = (p_der, p_izq, p_arr, p_aba)
        self.conteo = [0, 0, 0, 0]
        self.suma_dx = 0
        self.suma_dx2 = 0
        self.cruces = []

    @property
    def pasos(self):
        return sum(self.conteo)

    def paso(self):
        dx, dy = modelo2.paso_caminata(self.gen.random(), self.p[0], self.p[1], self.p[2])
        self.conteo[INDICE[(dx, dy)]] += 1
        self.suma_dx += dx
        self.suma_dx2 += dx * dx
        return dx, -dy          # +Y del módulo (arriba) = fila anterior en pantalla

    def registrar_cruce(self, pasos):
        self.cruces.append(pasos)

    def media_dx(self):
        return self.p[0] - self.p[1]

    def var_dx(self):
        return self.p[0] + self.p[1] - self.media_dx() ** 2

    def pasos_esperados(self, distancia):
        """Pasos esperados para avanzar 'distancia' columnas (sin paredes)."""
        m = self.media_dx()
        return distancia / m if m > 0 else float("inf")

    def metricas(self, distancia=19):
        n = self.pasos
        media = self.suma_dx / n if n else float("nan")
        var = self.suma_dx2 / n - media ** 2 if n else float("nan")
        cruce = sum(self.cruces) / len(self.cruces) if self.cruces else float("nan")
        filas = [
            ("E[dx] por paso", media, self.media_dx()),
            ("Var[dx] por paso", var, self.var_dx()),
            ("Pasos hasta el Núcleo", cruce, self.pasos_esperados(distancia)),
        ]
        nombres = ["P(der)", "P(izq)", "P(arr)", "P(aba)"]
        for nom, c, p in zip(nombres, self.conteo, self.p):
            filas.append((nom, c / n if n else float("nan"), p))
        return filas
