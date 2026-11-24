"""
Módulo 3: Simulación de Monte Carlo (Predictor de Brechas y Recompensas Markov)
Proyecto: Último Nodo — ExpoSimu 2026 (UPTC)
Autores: Paredes, Carrillo, Soledad, Suárez (Integrante 3)

Descripción:
    Implementa el Modelo 3 de simulación estocástica desacoplado de Pygame:
    1. Generador Congruencial Aditivo reutilizado del Taller 1:
       X_n = (X_{n-1} + X_{n-k}) mod m,   R_n = X_n / m
    2. Predictor Monte Carlo: estima la probabilidad de brecha p_hat en una
       oleada con N réplicas independientes e intervalo de confianza al 95 %:
       IC_95% = p_hat ± 1.96 * sqrt(p_hat * (1 - p_hat) / N)
    3. Sistema de recompensas mediante Cadena de Markov de dos estados
       ("energia" y "parche") con distribución estacionaria pi = (0.75, 0.25).
    4. Interfaz compatible con juego/modelos/montecarlo.py y validación
       experimental de 3 configuraciones con exportación de gráfica PNG.
"""

from datetime import datetime
import getpass
import math
import os
from pathlib import Path

# ==============================================================================
# 1. GENERADOR PSEUDOALEATORIO: CONGRUENCIAL ADITIVO (TALLER 1)
# ==============================================================================

SEMILLAS_ADITIVO_DEFECTO = (123456789, 362436069, 521288629, 88675123, 5783321)
MODULO_ADITIVO = 2**31 - 1  # 2147483647 (primo de Mersenne)


def congruencial_aditivo(semillas, m, cantidad):
    """
    Genera `cantidad` números pseudoaleatorios mediante el método
    Congruencial Aditivo:
        X_n = (X_{n-1} + X_{n-k}) mod m
        R_n = X_n / m

    Parámetros:
        semillas (Sequence[int]): Vector inicial de k >= 2 semillas enteras.
        m (int): Módulo entero positivo.
        cantidad (int): Cantidad de números a generar.

    Retorna:
        tuple[list[int], list[float]]: (lista_Xi, lista_Ri)
    """
    estado = [int(s) % m for s in semillas]
    k = len(estado)
    if k < 2:
        raise ValueError("El generador congruencial aditivo requiere al menos k >= 2 semillas.")
    if all(x == 0 for x in estado):
        estado[0] = 1

    xi_lista = []
    ri_lista = []

    for _ in range(cantidad):
        nuevo_x = (estado[-1] + estado[-k]) % m
        estado.append(nuevo_x)
        estado.pop(0)
        xi_lista.append(nuevo_x)
        ri_lista.append(nuevo_x / m)

    return xi_lista, ri_lista


class CongruencialAditivo:
    """
    Envoltorio con estado del Generador Congruencial Aditivo que cumple
    la interfaz esperada por el juego (gen.random() -> float en [0, 1) y gen.nombre).
    """

    def __init__(self, semilla=2049, semillas=None, m=MODULO_ADITIVO):
        self.m = m
        if semillas is not None:
            self.estado = [int(s) % m for s in semillas]
        else:
            base = int(semilla) % m or 1
            self.estado = [
                (base + i * 7919) % m or 1
                for i in range(len(SEMILLAS_ADITIVO_DEFECTO))
            ]
        self.k = len(self.estado)
        self.nombre = f"Congruencial aditivo (k={self.k}, m=2^31-1)"

    def random(self):
        """Retorna el siguiente número pseudoaleatorio R_i en [0, 1)."""
        nuevo_x = (self.estado[-1] + self.estado[-self.k]) % self.m
        self.estado.append(nuevo_x)
        self.estado.pop(0)
        return nuevo_x / self.m

    def exponencial(self, tasa):
        """Genera Exp(tasa) por transformada inversa: -ln(1 - R_i) / tasa."""
        if tasa <= 0:
            return float("inf")
        r = self.random()
        while r >= 0.9999999999:
            r = self.random()
        return -math.log(1.0 - r) / tasa


# ==============================================================================
# 2. MODELO 3: PREDICTOR MONTE CARLO Y RECOMPENSAS MARKOV
# ==============================================================================

MATRIZ_MARKOV = {
    "energia": [("energia", 0.80), ("parche", 0.20)],
    "parche": [("energia", 0.60), ("parche", 0.40)],
}

DISTRIBUCION_ESTACIONARIA = {
    "energia": 0.75,  # pi_0 = 0.6 / (0.2 + 0.6) = 3/4
    "parche": 0.25,   # pi_1 = 0.2 / (0.2 + 0.6) = 1/4
}


def probabilidad_estacionaria_markov(p01=0.20, p10=0.60):
    """
    Calcula analíticamente la distribución estacionaria pi = (pi_0, pi_1)
    de una Cadena de Markov ergódica de 2 estados:
        pi_0 = p_10 / (p_01 + p_10)
        pi_1 = p_01 / (p_01 + p_10)
    """
    denom = p01 + p10
    return p10 / denom, p01 / denom


class ModeloMonteCarlo:
    """
    Modelo 3: Simulación de Monte Carlo para predicción de riesgo de brecha
    antes de cada oleada y asignación secuencial de recompensas Markovianas.
    """

    nombre = "Monte Carlo"

    def __init__(self, gen=None, semilla=2049):
        self.gen = gen if gen is not None else CongruencialAditivo(semilla=semilla)
        self.ultima = None  # (descripcion, p, margen, n, teorico)
        self.estado = "energia"
        self.conteo = {"energia": 0, "parche": 0}

    # --------------------------------------------------------- Estimaciones MC
    def estimar_probabilidad(self, experimento, n=400):
        """
        Estima la probabilidad p = P(evento) mediante n réplicas Monte Carlo
        independientes y calcula su margen de error al 95 % de confianza:
            p_hat = (1/n) * sum(I_i)
            margen = 1.96 * sqrt(p_hat * (1 - p_hat) / n)
        """
        exitos = sum(1 for _ in range(n) if experimento(self.gen))
        p_hat = exitos / n
        margen = 1.96 * math.sqrt(p_hat * (1.0 - p_hat) / n)
        return p_hat, margen

    def estimar_media(self, experimento, n=400):
        """
        Estima la esperanza E[X] mediante n réplicas Monte Carlo y calcula
        el margen de error al 95 % de confianza usando la varianza muestral.
        """
        valores = [experimento(self.gen) for _ in range(n)]
        media = sum(valores) / n
        var = sum((v - media) ** 2 for v in valores) / (n - 1) if n > 1 else 0.0
        margen = 1.96 * math.sqrt(var / n)
        return media, margen

    # ---------------------------------------------------- Simulación de oleada
    @staticmethod
    def simular_oleada_brecha(gen, lam, mu, c, k, duracion):
        """
        Replica estocásticamente una oleada de duración `duracion` (s) sobre un
        sistema de colas M/M/c/K (c servidores paralelos, capacidad total K).
        Retorna True si ocurre al menos una brecha (rechazo por buffer lleno).
        """
        t = 0.0
        en_sistema = 0
        t_llegada = -math.log(1.0 - min(gen.random(), 0.9999999999)) / lam
        salidas = []

        while t < duracion:
            t_salida = min(salidas) if salidas else float("inf")
            if t_llegada <= t_salida:
                t = t_llegada
                if t > duracion:
                    break
                if en_sistema >= k:
                    return True  # Ocurre brecha
                en_sistema += 1
                if len(salidas) < c:
                    st = -math.log(1.0 - min(gen.random(), 0.9999999999)) / mu
                    salidas.append(t + st)
                t_llegada = t - math.log(1.0 - min(gen.random(), 0.9999999999)) / lam
            else:
                t = t_salida
                if t > duracion:
                    break
                salidas.remove(t_salida)
                en_sistema -= 1
                if en_sistema >= c:
                    st = -math.log(1.0 - min(gen.random(), 0.9999999999)) / mu
                    salidas.append(t + st)

        return False

    def predecir_oleada(self, lam, mu, c, k, duracion=20.0, n=400):
        """
        Ejecuta `n` réplicas de Monte Carlo para predecir el riesgo de brecha
        de la próxima oleada bajo los parámetros (lam, mu, c, k, duracion).
        """
        p_hat, margen = self.estimar_probabilidad(
            lambda g: self.simular_oleada_brecha(g, lam, mu, c, k, duracion),
            n=n,
        )
        ee = margen / 1.96
        ic_inf = max(0.0, p_hat - margen)
        ic_sup = min(1.0, p_hat + margen)
        return {
            "n": n,
            "p_hat": p_hat,
            "error_estandar": ee,
            "margen_95": margen,
            "ic_95": (ic_inf, ic_sup),
        }

    # ---------------------------------------------------- Recompensas Markov
    def siguiente_recompensa(self):
        """
        Avanza un paso en la Cadena de Markov de dos estados ("energia", "parche")
        usando el generador congruencial aditivo y actualiza los conteos observados.
        """
        r = self.gen.random()
        acumulado = 0.0
        destino = self.estado
        for est, prob in MATRIZ_MARKOV[self.estado]:
            acumulado += prob
            if r < acumulado:
                destino = est
                break
        self.estado = destino
        self.conteo[destino] += 1
        return destino

    def reiniciar_markov(self, estado_inicial="energia"):
        self.estado = estado_inicial
        self.conteo = {"energia": 0, "parche": 0}

    def metricas(self):
        """Métricas para el Modo Ingeniero (F1) del juego."""
        total = sum(self.conteo.values())
        filas = []
        for estado in ("energia", "parche"):
            obs = self.conteo[estado] / total if total else float("nan")
            filas.append((f"π {estado}", obs, DISTRIBUCION_ESTACIONARIA[estado]))
        if self.ultima:
            desc, p, margen, n, teo = self.ultima
            filas.append((desc, p, teo))
            filas.append(("Margen IC 95 %", margen, float("nan")))
        return filas


# ==============================================================================
# 3. VALIDACIÓN EXPERIMENTAL STANDALONE (3 CONFIGURACIONES + GRÁFICO PNG)
# ==============================================================================

def ejecutar_validacion():
    fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    usuario = getpass.getuser()

    print("=" * 84)
    print("VALIDACIÓN EXPERIMENTAL — MODELO 3: SIMULACIÓN DE MONTE CARLO (ÚLTIMO NODO)")
    print(f"Fecha y hora del sistema : {fecha_hora}")
    print(f"Usuario del sistema      : {usuario}")
    print("Generador PRNG           : Congruencial Aditivo (k=5, m=2^31 - 1)")
    print("=" * 84)

    # Tres configuraciones experimentales (correspondientes a los 3 niveles del juego)
    configuraciones = [
        {
            "id": 1,
            "nombre": "Config. 1 (Nivel 1 - Tráfico bajo)",
            "lam": 0.65,
            "mu": 0.60,
            "c": 2,
            "k": 5,
            "duracion": 20.0,
            "N_mc": 1000,
            "M_markov": 20000,
            "semilla": 1049,
        },
        {
            "id": 2,
            "nombre": "Config. 2 (Nivel 2 - Tráfico medio)",
            "lam": 0.80,
            "mu": 0.55,
            "c": 2,
            "k": 4,
            "duracion": 20.0,
            "N_mc": 2500,
            "M_markov": 20000,
            "semilla": 2049,
        },
        {
            "id": 3,
            "nombre": "Config. 3 (Nivel 3 - Tráfico crítico)",
            "lam": 0.85,
            "mu": 0.50,
            "c": 2,
            "k": 4,
            "duracion": 20.0,
            "N_mc": 5000,
            "M_markov": 20000,
            "semilla": 3049,
        },
    ]

    pi0_teo, pi1_teo = probabilidad_estacionaria_markov(p01=0.20, p10=0.60)
    resultados_tabla = []

    for cfg in configuraciones:
        # 1) Referencia de alta precisión (N_ref = 100,000 réplicas) como valor esperado
        mc_ref = ModeloMonteCarlo(semilla=cfg["semilla"] + 99991)
        res_ref = mc_ref.predecir_oleada(
            cfg["lam"], cfg["mu"], cfg["c"], cfg["k"], cfg["duracion"], n=100000
        )
        p_teo = res_ref["p_hat"]
        ee_teo = math.sqrt(p_teo * (1.0 - p_teo) / cfg["N_mc"])

        # 2) Corrida experimental con N_mc réplicas y M_markov transiciones
        mc = ModeloMonteCarlo(semilla=cfg["semilla"])
        res = mc.predecir_oleada(
            cfg["lam"], cfg["mu"], cfg["c"], cfg["k"], cfg["duracion"], n=cfg["N_mc"]
        )
        for _ in range(cfg["M_markov"]):
            mc.siguiente_recompensa()

        pi0_obs = mc.conteo["energia"] / cfg["M_markov"]
        pi1_obs = mc.conteo["parche"] / cfg["M_markov"]

        err_p = abs(res["p_hat"] - p_teo) / p_teo * 100.0 if p_teo > 0 else 0.0
        err_pi0 = abs(pi0_obs - pi0_teo) / pi0_teo * 100.0
        err_pi1 = abs(pi1_obs - pi1_teo) / pi1_teo * 100.0

        resultados_tabla.append({
            "cfg": cfg,
            "p_teo": p_teo,
            "ee_teo": ee_teo,
            "p_obs": res["p_hat"],
            "ee_obs": res["error_estandar"],
            "ic_95": res["ic_95"],
            "pi0_obs": pi0_obs,
            "pi1_obs": pi1_obs,
            "err_p": err_p,
            "err_pi0": err_pi0,
            "err_pi1": err_pi1,
        })

        print(f"\n[{cfg['nombre']}]")
        print(
            f"  Parámetros : lam={cfg['lam']}, mu={cfg['mu']}, c={cfg['c']}, "
            f"K={cfg['k']}, T={cfg['duracion']}s, N={cfg['N_mc']}, M={cfg['M_markov']}"
        )
        print(
            f"  Teórico    : p_brecha={p_teo:.4f}, EE_teo={ee_teo:.5f}, "
            f"pi_energia={pi0_teo:.4f}, pi_parche={pi1_teo:.4f}"
        )
        print(
            f"  Obtenido   : p_brecha={res['p_hat']:.4f} (IC 95%: [{res['ic_95'][0]:.4f}, {res['ic_95'][1]:.4f}]), "
            f"EE_obs={res['error_estandar']:.5f}, pi_energia={pi0_obs:.4f}, pi_parche={pi1_obs:.4f}"
        )
        print(
            f"  Diferencia : Err(p_brecha)={err_p:.2f} %, Err(pi_energia)={err_pi0:.2f} %, "
            f"Err(pi_parche)={err_pi1:.2f} %"
        )

    # 3) Estudio de convergencia del error estándar ~ 1 / sqrt(N)
    print("\n" + "-" * 84)
    print("ESTUDIO DE CONVERGENCIA DEL PREDICTOR MONTE CARLO (Config. 2)")
    print(f"{'N réplicas':<12} | {'p_hat':<10} | {'IC 95 %':<22} | {'EE obs':<12} | {'EE teo':<12}")
    print("-" * 84)
    ns_conv = [100, 400, 1600, 6400, 25600]
    p_conv, ee_obs_list, ee_teo_list = [], [], []
    p_ref_c2 = resultados_tabla[1]["p_teo"]

    for n_val in ns_conv:
        mc_c = ModeloMonteCarlo(semilla=2049)
        r_c = mc_c.predecir_oleada(0.80, 0.55, 2, 4, 20.0, n=n_val)
        ee_t = math.sqrt(p_ref_c2 * (1.0 - p_ref_c2) / n_val)
        p_conv.append(r_c["p_hat"])
        ee_obs_list.append(r_c["error_estandar"])
        ee_teo_list.append(ee_t)
        ic_txt = f"[{r_c['ic_95'][0]:.4f}, {r_c['ic_95'][1]:.4f}]"
        print(
            f"{n_val:<12} | {r_c['p_hat']:<10.4f} | {ic_txt:<22} | "
            f"{r_c['error_estandar']:<12.5f} | {ee_t:<12.5f}"
        )

    # 4) Generación de gráfico de validación
    try:
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
        fig.suptitle(
            "Validación Modelo 3: Simulación de Monte Carlo y Cadena de Markov",
            fontsize=12,
            fontweight="bold",
        )

        # Panel (a): Convergencia del error estándar ~ 1/sqrt(N)
        ax1 = axes[0]
        ax1.loglog(ns_conv, ee_teo_list, "o--", color="#0077B6", label="Error estándar teórico $\\sqrt{p(1-p)/N}$")
        ax1.loglog(ns_conv, ee_obs_list, "s-", color="#D62828", label="Error estándar simulado")
        ax1.set_title("(a) Convergencia del error estándar ($\\propto 1/\\sqrt{N}$)")
        ax1.set_xlabel("Número de réplicas (N)")
        ax1.set_ylabel("Error estándar (EE)")
        ax1.grid(True, which="both", linestyle=":", alpha=0.6)
        ax1.legend(fontsize=8.5)

        # Panel (b): Convergencia de la Cadena de Markov hacia pi = (0.75, 0.25)
        ax2 = axes[1]
        mc_mk = ModeloMonteCarlo(semilla=2049)
        pasos = list(range(1, 3001))
        traj_energia = []
        traj_parche = []
        for step in pasos:
            mc_mk.siguiente_recompensa()
            traj_energia.append(mc_mk.conteo["energia"] / step)
            traj_parche.append(mc_mk.conteo["parche"] / step)

        ax2.plot(pasos, traj_energia, color="#0096C7", linewidth=1.3, label="$\\hat{\\pi}_{\\mathrm{energia}}$ observado")
        ax2.axhline(0.75, color="#023E8A", linestyle="--", linewidth=1.2, label="$\\pi_{\\mathrm{energia}} = 0.75$ (teórico)")
        ax2.plot(pasos, traj_parche, color="#E63946", linewidth=1.3, label="$\\hat{\\pi}_{\\mathrm{parche}}$ observado")
        ax2.axhline(0.25, color="#9B2226", linestyle="--", linewidth=1.2, label="$\\pi_{\\mathrm{parche}} = 0.25$ (teórico)")
        ax2.set_title("(b) Convergencia estacionaria Cadena de Markov")
        ax2.set_xlabel("Número de transiciones (M)")
        ax2.set_ylabel("Frecuencia acumulada")
        ax2.set_ylim(0.0, 1.0)
        ax2.grid(True, linestyle=":", alpha=0.6)
        ax2.legend(fontsize=8.5, loc="right")

        plt.tight_layout()
        salida_png = Path(__file__).resolve().parent / "validacion_modelo3_montecarlo.png"
        plt.savefig(salida_png, dpi=180)
        print("-" * 84)
        print(f"Gráfico de validación guardado en: {salida_png}")
    except ImportError:
        print("Nota: matplotlib no está instalado en este entorno; omitiendo PNG.")


if __name__ == "__main__":
    ejecutar_validacion()
