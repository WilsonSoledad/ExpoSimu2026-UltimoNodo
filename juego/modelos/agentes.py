"""
Modelo 4 - Simulación basada en agentes: enjambre de bots.

Adaptador del módulo de Paredes (modulos/..._modelo4_agentes.py): el juego usa
su regla de actualización del rumbo (regla_rumbo), es decir, el modelo de
Vicsek extendido con separación y atracción hacia la puerta más débil, y su
polarización teórica (phi_global_theory).

    u_i = (1/n_i) sum_{j in B_r(i)} e^{i theta_j} + w e^{i alpha_i}
          + sum_{j != i, d_ij < r_sep} (1 - d_ij/r_sep) (x_i - x_j)/d_ij
    theta_i(t+1) = arg(u_i) + eta (U_i - 1/2)

Lo que agrega este archivo es lo propio del juego:
  - el plano no es periódico (L = None) y las unidades son píxeles y segundos;
  - alpha_i es la dirección desde cada bot hacia la puerta más débil
    (en el módulo es un ángulo fijo); la debilidad la calcula Puerta.debilidad();
  - el rumbo se actualiza cada 'periodo' segundos (paso discreto del modelo) y
    entre actualizaciones el bot avanza con rapidez constante;
  - un bot que llega a una puerta sale del enjambre y entra a su cola.

Interfaz que usa el juego:
    ModeloAgentes(gen)
    .generar_enjambre(n, x, y)
    .paso(dt, puertas) -> list[(bot, indice_puerta)]   bots que llegaron
         puertas: lista de (x, y, debilidad)
    .metricas() -> list[(nombre, observado, teorico)]
"""
import math

import numpy as np

from aleatorio import uniforme
from fuentes import modelo4


class Bot:
    _siguiente_id = 0

    def __init__(self, x, y, theta):
        Bot._siguiente_id += 1
        self.id = Bot._siguiente_id
        self.x, self.y = x, y
        self.theta = theta       # rumbo (rad)
        self.objetivo = None     # puerta hacia la que apunta su rumbo (decisión k_i)


class ModeloAgentes:
    nombre = "Basado en agentes"

    def __init__(self, gen, velocidad=70, radio_percepcion=150, radio_separacion=24,
                 eta=1.0, w=1.0, periodo=0.1, radio_llegada=16):
        self.gen = gen
        self.vel = velocidad            # v0 (px/s)
        self.r = radio_percepcion       # r   (px)
        self.r_sep = radio_separacion   # r_sep (px)
        self.eta = eta                  # amplitud del ruido angular (rad)
        self.w = w                      # peso de la atracción hacia la puerta débil
        self.periodo = periodo          # s entre actualizaciones del rumbo
        self.r_llegada = radio_llegada
        self.bots = []
        self.reloj = 0.0
        # Acumuladores para el modo ingeniero (promedios sobre todas las decisiones)
        self.pasos = 0
        self.suma_phi = 0.0
        self.decisiones = 0
        self.aciertos = 0               # bots cuyo rumbo apunta a la puerta más débil
        self.suma_dnn = 0.0
        self.n_dnn = 0
        self.llegadas_por_puerta = {}
        self.llegadas = 0
        self.llegadas_debil = 0         # llegadas a la puerta que era la más débil en ese instante

    def generar_enjambre(self, n, x, y):
        for _ in range(n):
            bx = x + uniforme(self.gen, -20, 20)
            by = y + uniforme(self.gen, -60, 60)
            theta = 2 * math.pi * self.gen.random() - math.pi   # igual que en el módulo
            self.bots.append(Bot(bx, by, theta))

    def _uniformes(self, n):
        return np.array([self.gen.random() for _ in range(n)])

    # ------------------------------------------------- paso discreto del modelo
    def _actualizar_rumbos(self, puertas):
        n = len(self.bots)
        pos = np.array([(b.x, b.y) for b in self.bots], dtype=float)
        theta = np.array([b.theta for b in self.bots], dtype=float)
        gx = np.array([p[0] for p in puertas], dtype=float)
        gy = np.array([p[1] for p in puertas], dtype=float)
        debil = max(range(len(puertas)), key=lambda k: puertas[k][2])
        alpha = np.arctan2(gy[debil] - pos[:, 1], gx[debil] - pos[:, 0])

        theta, dist2 = modelo4.regla_rumbo(pos, theta, alpha, self.r, self.eta, self.w,
                                           self.r_sep, self._uniformes(n), L=None,
                                           calcular_distancias=True)

        # Decisión de cada bot (como en el módulo): la puerta k que maximiza cos(theta_i - alpha_ik)
        alphas = np.arctan2(gy[None, :] - pos[:, 1:2], gx[None, :] - pos[:, 0:1])
        eleccion = np.argmax(np.cos(theta[:, None] - alphas), axis=1)
        for b, th, k in zip(self.bots, theta, eleccion):
            b.theta, b.objetivo = float(th), int(k)

        self.pasos += 1
        self.suma_phi += math.hypot(np.cos(theta).mean(), np.sin(theta).mean())
        self.decisiones += n
        self.aciertos += int((eleccion == debil).sum())
        if n > 1:
            d2 = dist2.copy()
            np.fill_diagonal(d2, np.inf)
            self.suma_dnn += float(np.sqrt(d2.min(1)).mean())
            self.n_dnn += 1

    def paso(self, dt, puertas):
        if not puertas or not self.bots:
            self.reloj = 0.0
            return []
        self.reloj += dt
        if self.reloj >= self.periodo:
            self.reloj %= self.periodo
            self._actualizar_rumbos(puertas)

        debil = max(range(len(puertas)), key=lambda k: puertas[k][2])
        llegados = []
        for b in list(self.bots):
            b.x += self.vel * dt * math.cos(b.theta)
            b.y += self.vel * dt * math.sin(b.theta)
            for k, (px, py, _) in enumerate(puertas):
                if math.hypot(px - b.x, py - b.y) < self.r_llegada:
                    self.bots.remove(b)
                    self.llegadas_por_puerta[k] = self.llegadas_por_puerta.get(k, 0) + 1
                    self.llegadas += 1
                    self.llegadas_debil += int(k == debil)
                    b.objetivo = k
                    llegados.append((b, k))
                    break
        return llegados

    # ------------------------------------------------- modo ingeniero
    def metricas(self):
        nan = float("nan")
        phi = self.suma_phi / self.pasos if self.pasos else nan
        pd = self.aciertos / self.decisiones if self.decisiones else nan
        dnn = self.suma_dnn / self.n_dnn if self.n_dnn else nan
        ll = self.llegadas_debil / self.llegadas if self.llegadas else nan
        return [
            ("Bots activos", len(self.bots), nan),
            ("Polarización φ (ref. global)", phi, modelo4.phi_global_theory(self.eta)),
            ("P_d (rumbo a la más débil)", pd, nan),
            ("Llegadas a la más débil", ll, nan),
            ("Distancia media al vecino (px)", dnn, nan),
        ]
