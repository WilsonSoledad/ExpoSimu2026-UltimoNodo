"""
Modelo 5 - Dinámica de sistemas: infección de la red con SIR.

Adaptador del módulo de Paredes (modulos/..._modelo5_sir.py): el juego usa
sus ecuaciones (sir_rhs), su integrador RK4 y su pico teórico (peak_theory).
Lo que agrega este archivo es lo propio del juego: avanzar un paso por
fotograma, los impulsos de infección por brechas y los cambios de beta y
gamma que hace el jugador. Unidades de tiempo del juego: segundos.

Niveles (stocks):  S sanos, I infectados, R parcheados
Flujos:            infección     = beta * S * I / N
                   recuperación  = gamma * I
Ecuaciones:        dS/dt = -beta S I / N
                   dI/dt =  beta S I / N - gamma I
                   dR/dt =  gamma I
Umbral:            R0 = beta / gamma;  la infección crece si R0 * S / N > 1

El jugador influye en los parámetros: segmentar la red reduce beta y
aplicar un parche multiplica gamma durante unos segundos. Las brechas
introducen infectados nuevos (impulsos sobre el nivel I).

Interfaz que usa el juego:
    ModeloSIR(N, beta, gamma, I0)
    .paso(dt)                 integración RK4 con subpasos (ecuaciones del módulo 5)
    .infectar(k)
    .aplicar_parche(duracion, factor)
    .segmentar(factor)
    .fraccion_infectada() -> float
    .metricas() -> list[(nombre, observado, teorico)]
"""
from fuentes import modelo5


class ModeloSIR:
    nombre = "Dinámica de sistemas (SIR)"

    def __init__(self, N=100, beta=0.35, gamma=0.12, I0=0, dt_integracion=0.05):
        self.N = N
        self.beta = beta
        self.gamma_base = gamma
        self.S = float(N - I0)
        self.I = float(I0)
        self.R = 0.0
        self.h = dt_integracion
        self.t = 0.0
        self.parche_restante = 0.0
        self.factor_parche = 1.0
        self.pico_I = self.I
        self.historial = [(0.0, self.S, self.I, self.R)]

    @property
    def gamma(self):
        return self.gamma_base * (self.factor_parche if self.parche_restante > 0 else 1.0)

    def R0(self):
        return self.beta / self.gamma

    def Re(self):
        return self.R0() * self.S / self.N

    def paso(self, dt):
        # RK4 con las ecuaciones del módulo 5 (mismo esquema que su integrate())
        f = lambda v: modelo5.sir_rhs(v, self.beta, self.gamma, self.N)
        restante = dt
        while restante > 1e-9:
            h = min(self.h, restante)
            v = (self.S, self.I, self.R)
            k1 = f(v)
            k2 = f([v[i] + 0.5 * h * k1[i] for i in range(3)])
            k3 = f([v[i] + 0.5 * h * k2[i] for i in range(3)])
            k4 = f([v[i] + h * k3[i] for i in range(3)])
            nuevo = [v[i] + h / 6.0 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]) for i in range(3)]
            self.S, self.I, self.R = max(float(nuevo[0]), 0.0), max(float(nuevo[1]), 0.0), float(nuevo[2])
            restante -= h
        self.t += dt
        self.parche_restante = max(0.0, self.parche_restante - dt)
        self.pico_I = max(self.pico_I, self.I)
        if not self.historial or self.t - self.historial[-1][0] >= 0.5:
            self.historial.append((self.t, self.S, self.I, self.R))

    def infectar(self, k):
        k = min(k, self.S)
        self.S -= k
        self.I += k

    def aplicar_parche(self, duracion=10.0, factor=3.0):
        self.parche_restante = duracion
        self.factor_parche = factor

    def segmentar(self, factor=0.75):
        self.beta *= factor

    def fraccion_infectada(self):
        return self.I / self.N

    def pico_teorico(self):
        """Referencia del módulo 5: pico de I con parámetros fijos e I0 = 1."""
        return modelo5.peak_theory(self.beta, self.gamma, self.N, 1)

    def metricas(self):
        return [
            ("S (sanos)", self.S, float("nan")),
            ("I (infectados)", self.I, float("nan")),
            ("R (parcheados)", self.R, float("nan")),
            ("S + I + R", self.S + self.I + self.R, self.N),
            ("R0 = β/γ", self.R0(), float("nan")),
            ("Re = R0·S/N (crece si > 1)", self.Re(), float("nan")),
            ("Pico de I (ref. sin intervención)", self.pico_I,
             self.pico_teorico() if self.pico_I >= 1 else float("nan")),
        ]
