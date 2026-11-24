"""
Modelo 2 - Caminata aleatoria sesgada en 2D para los gusanos (PROVISIONAL).

Lo reemplaza el módulo del integrante 1. Interfaz que usa el juego:

    ModeloCaminata(gen, p_der, p_izq, p_arr, p_aba)
    .paso() -> (dx, dy)            un paso sobre la grilla
    .registrar_cruce(pasos)        un gusano llegó al Núcleo tras 'pasos' pasos
    .metricas() -> list[(nombre, observado, teorico)]

Caso de clase: caminata simple simétrica en Z^2, cada dirección con 1/4.
Aquí se sesga hacia el Núcleo (derecha): p_der > p_izq.
Teoría por paso en x:  E[dx] = p_der - p_izq
                       Var[dx] = p_der + p_izq - (p_der - p_izq)^2
Tras n pasos:          E[X_n] = n (p_der - p_izq),  Var[X_n] = n Var[dx]
"""
from aleatorio import por_intervalos

DIRECCIONES = [(1, 0), (-1, 0), (0, -1), (0, 1)]   # der, izq, arr, aba


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
        i = por_intervalos(self.gen, [0, 1, 2, 3], self.p)
        self.conteo[i] += 1
        dx, dy = DIRECCIONES[i]
        self.suma_dx += dx
        self.suma_dx2 += dx * dx
        return dx, dy

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
