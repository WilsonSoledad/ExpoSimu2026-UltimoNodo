"""
Modelo 3 - Simulación Monte Carlo (PROVISIONAL).

Lo reemplaza el módulo del integrante 3. Tiene dos usos en el juego:

1. Predictor: estima la probabilidad de que alguna amenaza atraviese
   todas las puertas en la próxima oleada, repitiendo N veces una
   simulación rápida con la configuración actual. Muestra p ± margen (IC 95 %).

2. Recompensas: cadena de Markov de dos estados, como el ejemplo de clase
   de salud y munición, con "un Monte Carlo distinto para cada transición".

       Estado actual   Intervalo de R_i   Estado siguiente
       energía (0)     [0, 0.8)           energía (0)
       energía (0)     [0.8, 1)           parche (1)
       parche (1)      [0, 0.6)           energía (0)
       parche (1)      [0.6, 1)           parche (1)

   Distribución estacionaria: pi_0 = 3/4, pi_1 = 1/4.

Interfaz que usa el juego:
    ModeloMonteCarlo(gen)
    .estimar_probabilidad(experimento, n) -> (p, margen)   experimento(gen) -> bool
    .estimar_media(experimento, n) -> (media, margen)      experimento(gen) -> float
    .siguiente_recompensa() -> "energia" | "parche"
    .metricas() -> list[(nombre, observado, teorico)]
"""
import math

MATRIZ = {
    "energia": [("energia", 0.8), ("parche", 0.2)],
    "parche": [("energia", 0.6), ("parche", 0.4)],
}
ESTACIONARIA = {"energia": 0.75, "parche": 0.25}


class ModeloMonteCarlo:
    nombre = "Monte Carlo"

    def __init__(self, gen):
        self.gen = gen
        self.ultima = None          # (descripción, p, margen, n)
        self.estado = "energia"
        self.conteo = {"energia": 0, "parche": 0}

    # -------------------------------------------------------- estimaciones
    def estimar_probabilidad(self, experimento, n=400):
        exitos = sum(1 for _ in range(n) if experimento(self.gen))
        p = exitos / n
        margen = 1.96 * math.sqrt(p * (1 - p) / n)
        return p, margen

    def estimar_media(self, experimento, n=400):
        valores = [experimento(self.gen) for _ in range(n)]
        media = sum(valores) / n
        var = sum((v - media) ** 2 for v in valores) / (n - 1) if n > 1 else 0.0
        return media, 1.96 * math.sqrt(var / n)

    # -------------------------------------------------------- recompensas
    def siguiente_recompensa(self):
        r = self.gen.random()
        acumulado = 0.0
        for destino, p in MATRIZ[self.estado]:
            acumulado += p
            if r < acumulado:
                break
        self.estado = destino
        self.conteo[destino] += 1
        return destino

    def metricas(self):
        total = sum(self.conteo.values())
        filas = []
        for estado in ("energia", "parche"):
            obs = self.conteo[estado] / total if total else float("nan")
            filas.append((f"π {estado}", obs, ESTACIONARIA[estado]))
        if self.ultima:
            desc, p, margen, n, teo = self.ultima
            filas.append((desc, p, teo))
            filas.append(("Margen IC 95 %", margen, float("nan")))
        return filas
