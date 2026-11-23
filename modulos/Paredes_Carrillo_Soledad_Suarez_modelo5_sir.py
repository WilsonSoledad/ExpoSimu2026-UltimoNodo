#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modelo 5 - Dinámica de Sistemas: modelo epidemiológico SIR con ecuaciones diferenciales.
Módulo standalone (independiente del juego). Aplicación en el juego: propagación de un
efecto/contagio entre la población del nivel.

Uso:
    python apellido1_apellido2_modelo5_sir.py            # validación completa
    python apellido1_apellido2_modelo5_sir.py --show     # muestra los gráficos
    python apellido1_apellido2_modelo5_sir.py --prng lcg # usa el LCG
    python apellido1_apellido2_modelo5_sir.py --quick    # menos réplicas estocásticas
    python apellido1_apellido2_modelo5_sir.py --config 2 --show   # solo la configuración 2 (capturas)

PRNG: MT19937 propio y LCG (Numerical Recipes). >>> Confirmar cuál fue el del taller anterior. <<<
El PRNG se usa en la validación estocástica (algoritmo de Gillespie).
Dependencias: numpy, scipy, matplotlib.
"""
import argparse
import datetime
import getpass
import json
import math
import os
import platform
import sys

import numpy as np
from scipy import stats
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

# ----------------------------------------------------------------------------
# 1. GENERADORES PSEUDOALEATORIOS
# ----------------------------------------------------------------------------


class MT19937:
    def __init__(self, seed=5489):
        self.mt = [0] * 624
        self.idx = 624
        self.mt[0] = seed & 0xFFFFFFFF
        for i in range(1, 624):
            prev = self.mt[i - 1]
            self.mt[i] = (1812433253 * (prev ^ (prev >> 30)) + i) & 0xFFFFFFFF

    def _twist(self):
        mt = self.mt
        for i in range(624):
            y = (mt[i] & 0x80000000) | (mt[(i + 1) % 624] & 0x7FFFFFFF)
            mt[i] = mt[(i + 397) % 624] ^ (y >> 1) ^ (0x9908B0DF if y & 1 else 0)
        self.idx = 0

    def next_u32(self):
        if self.idx >= 624:
            self._twist()
        y = self.mt[self.idx]
        self.idx += 1
        y ^= y >> 11
        y ^= (y << 7) & 0x9D2C5680
        y ^= (y << 15) & 0xEFC60000
        y ^= y >> 18
        return y

    def random(self):
        return self.next_u32() / 4294967296.0

    def array(self, n):
        return np.array([self.random() for _ in range(n)])


class LCG:
    def __init__(self, seed=12345, a=1664525, c=1013904223, m=2 ** 32):
        self.x, self.a, self.c, self.m = seed % m, a, c, m

    def random(self):
        self.x = (self.a * self.x + self.c) % self.m
        return self.x / self.m

    def array(self, n):
        return np.array([self.random() for _ in range(n)])


def make_prng(kind, seed):
    return MT19937(seed) if kind == "mt" else LCG(seed)


def prng_selftest(kind="mt", n=100000, seed=2026):
    g = make_prng(kind, seed)
    u = g.array(n)
    k = 20
    obs, _ = np.histogram(u, bins=k, range=(0, 1))
    chi2 = ((obs - n / k) ** 2 / (n / k)).sum()
    return {"media": float(u.mean()), "var": float(u.var()), "chi2": float(chi2),
            "p_valor": float(1 - stats.chi2.cdf(chi2, k - 1)),
            "vector_referencia_MT": (MT19937(5489).next_u32() == 3499211612) if kind == "mt" else None}


# ----------------------------------------------------------------------------
# 2. MODELO SIR: ECUACIONES E INTEGRADORES PROPIOS
# ----------------------------------------------------------------------------
def sir_rhs(y, beta, gamma, N):
    S, I, R = y
    inf = beta * S * I / N
    return np.array([-inf, inf - gamma * I, gamma * I])


def integrate(method, beta, gamma, N, I0, tf, dt):
    """Integra con 'euler' o 'rk4'. Retorna t (n+1,), y (n+1, 3)."""
    n = int(round(tf / dt))
    t = np.linspace(0, n * dt, n + 1)
    y = np.zeros((n + 1, 3))
    y[0] = [N - I0, I0, 0.0]
    f = lambda v: sir_rhs(v, beta, gamma, N)
    for k in range(n):
        v = y[k]
        if method == "euler":
            y[k + 1] = v + dt * f(v)
        else:  # RK4
            k1 = f(v)
            k2 = f(v + 0.5 * dt * k1)
            k3 = f(v + 0.5 * dt * k2)
            k4 = f(v + dt * k3)
            y[k + 1] = v + dt / 6.0 * (k1 + 2 * k2 + 2 * k3 + k4)
    return t, y


def reference_solution(beta, gamma, N, I0, t):
    sol = solve_ivp(lambda tt, y: sir_rhs(y, beta, gamma, N), (0, t[-1]), [N - I0, I0, 0.0],
                    method="DOP853", t_eval=t, rtol=1e-10, atol=1e-10)
    return sol.y.T


# ----------------------------------------------------------------------------
# 3. TEORÍA (cálculo "manual" analítico)
# ----------------------------------------------------------------------------
def R0(beta, gamma):
    return beta / gamma


def peak_theory(beta, gamma, N, I0):
    """I_max = I0 + S0 - (gamma N/beta)[1 + ln(beta S0/(gamma N))] si R0*S0/N > 1; si no, I0."""
    S0 = N - I0
    if beta * S0 / (gamma * N) <= 1:
        return float(I0)
    return I0 + S0 - (gamma * N / beta) * (1 + math.log(beta * S0 / (gamma * N)))


def S_inf_theory(beta, gamma, N, I0):
    """Raíz de ln(S0/S) = (beta/(gamma N)) (S0 + I0 - S) en (0, S0)."""
    S0, k = N - I0, beta / (gamma * N)
    g = lambda S: math.log(S0 / S) - k * (S0 + I0 - S)
    return brentq(g, 1e-9, S0)


def pct(obt, teo):
    return abs(obt - teo) / abs(teo) * 100 if teo != 0 else float("nan")


# ----------------------------------------------------------------------------
# 4. SIR ESTOCÁSTICO (Gillespie) USANDO EL PRNG
# ----------------------------------------------------------------------------
def gillespie_sir(N, I0, beta, gamma, prng):
    S, I = N - I0, I0
    while I > 0:
        a_inf, a_rec = beta * S * I / N, gamma * I
        a0 = a_inf + a_rec
        prng.random()                       # u1: tiempo (no se registra la trayectoria)
        if prng.random() * a0 < a_inf:      # u2: tipo de evento
            S, I = S - 1, I + 1
        else:
            I -= 1
    return N - S


def attack_fraction_deterministic(R0v):
    """z = 1 - exp(-R0 z) (N grande, I0 -> 0)."""
    return brentq(lambda z: z - 1 + math.exp(-R0v * z), 1e-9, 1.0)


# ----------------------------------------------------------------------------
# 5. VALIDACIÓN, CONVERGENCIA, SENSIBILIDAD, GRÁFICOS
# ----------------------------------------------------------------------------
N0, I00, TF, DT = 10000, 10, 300.0, 0.1
CONFIGS = {
    1: dict(nombre="R0 < 1 (sin epidemia)", beta=0.24, gamma=0.30),
    2: dict(nombre="R0 = 2 (epidemia moderada)", beta=0.40, gamma=0.20),
    3: dict(nombre="R0 = 5 (epidemia intensa)", beta=1.00, gamma=0.20),
}


def metrics(t, y):
    i = int(np.argmax(y[:, 1]))
    return y[i, 1], t[i], y[-1, 0]


def run_validation(outdir, only=None):
    import matplotlib.pyplot as plt
    rows, curves = [], {}
    print("\n" + "=" * 112)
    print("TABLA DE VALIDACIÓN EXPERIMENTAL - MODELO 5 (SIR)  N=%d, I0=%d, RK4 dt=%.2f, tf=%.0f d" % (N0, I00, DT, TF))
    print("=" * 112)
    print("%-3s %-6s %-10s %-14s %-14s %-9s %-14s %-9s" % (
        "Cfg", "R0", "Métrica", "Teórico", "RK4 (propio)", "Dif.%", "solve_ivp", "Dif.%"))
    for k, c in CONFIGS.items():
        if only and k not in only:
            continue
        b, g = c["beta"], c["gamma"]
        t, y = integrate("rk4", b, g, N0, I00, TF, DT)
        ref = reference_solution(b, g, N0, I00, t)
        Imax, tpk, Sinf = metrics(t, y)
        Imax_r, tpk_r, Sinf_r = metrics(t, ref)
        teo_I, teo_S = peak_theory(b, g, N0, I00), S_inf_theory(b, g, N0, I00)
        curves[k] = (t, y, ref)
        for name, teo, obt, rf in (("I_max", teo_I, Imax, Imax_r), ("S_inf", teo_S, Sinf, Sinf_r)):
            rows.append((k, R0(b, g), name, teo, obt, pct(obt, teo), rf, pct(rf, teo)))
            print("%-3d %-6.2f %-10s %-14.4f %-14.4f %-9.4f %-14.4f %-9.4f" % rows[-1])
        print("    t_pico: RK4 = %.1f d | solve_ivp = %.1f d | error máx |I_rk4 - I_ref| = %.3e" % (
            tpk, tpk_r, np.abs(y[:, 1] - ref[:, 1]).max()))
        rows.append((k, R0(b, g), "t_pico", None, tpk, None, tpk_r, None))

    fig, axs = plt.subplots(1, len(curves), figsize=(5 * len(curves) if len(curves) > 1 else 7, 4.2), squeeze=False)
    ax = axs[0]
    for i, (k, (t, y, ref)) in enumerate(curves.items()):
        for j, (nm, col) in enumerate((("S", "tab:blue"), ("I", "tab:red"), ("R", "tab:green"))):
            ax[i].plot(t, y[:, j], color=col, label="%s (RK4)" % nm)
            ax[i].plot(t[::100], ref[::100, j], "k.", ms=3, label="solve_ivp" if j == 0 else None)
        c = CONFIGS[k]
        ax[i].set_xlim(0, 150 if k > 1 else 300)
        ax[i].set_title("Cfg %d: %s (β=%.2f, γ=%.2f)" % (k, c["nombre"], c["beta"], c["gamma"]), fontsize=9)
        ax[i].set_xlabel("t [días]"); ax[i].set_ylabel("Individuos"); ax[i].legend(fontsize=7); ax[i].grid(alpha=.3)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "m5_fig1_curvas.png" if not only else "m5_cfg%d.png" % only[0]), dpi=150)
    global LAST_CURVES
    LAST_CURVES = curves
    return rows


def run_convergence(outdir):
    import matplotlib.pyplot as plt
    b, g, tf = 0.4, 0.2, 100.0
    dts = [2.0, 1.0, 0.5, 0.25, 0.125, 0.0625]
    errs = {"euler": [], "rk4": []}
    print("\n" + "=" * 70)
    print("ANÁLISIS DE CONVERGENCIA (R0=2, tf=100 d): error máx. de I(t) vs DOP853")
    print("=" * 70)
    for dt in dts:
        row = [dt]
        for m in errs:
            t, y = integrate(m, b, g, N0, I00, tf, dt)
            e = np.abs(y[:, 1] - reference_solution(b, g, N0, I00, t)[:, 1]).max()
            errs[m].append(e); row.append(e)
        print("dt=%-7.4f Euler: %.3e   RK4: %.3e" % tuple(row))
    ords = {}
    for m in errs:
        ords[m] = float(np.polyfit(np.log(dts), np.log(errs[m]), 1)[0])
    print("Orden observado -> Euler: %.2f (teórico 1) | RK4: %.2f (teórico 4)" % (ords["euler"], ords["rk4"]))
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    ax.loglog(dts, errs["euler"], "o-", label="Euler (pendiente %.2f)" % ords["euler"])
    ax.loglog(dts, errs["rk4"], "s-", label="RK4 (pendiente %.2f)" % ords["rk4"])
    ax.set_xlabel("Paso Δt [días]"); ax.set_ylabel("Error máximo en I(t)")
    ax.set_title("Convergencia numérica"); ax.legend(); ax.grid(alpha=.3, which="both")
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "m5_fig2_convergencia.png"), dpi=150)
    return dts, errs, ords


def run_stochastic(kind, reps, outdir):
    import matplotlib.pyplot as plt
    N, I0 = 500, 2
    out = {}
    print("\n" + "=" * 92)
    print("VALIDACIÓN ESTOCÁSTICA (Gillespie, N=%d, I0=%d, %d réplicas, PRNG=%s)" % (N, I0, reps, kind.upper()))
    print("=" * 92)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    for i, k in enumerate((2, 3)):
        b, g = CONFIGS[k]["beta"], CONFIGS[k]["gamma"]
        r0 = R0(b, g)
        prng = make_prng(kind, 31337 + k)
        fin = np.array([gillespie_sir(N, I0, b, g, prng) for _ in range(reps)]) / N
        major = fin > 0.1
        p_obs, p_teo = major.mean(), 1 - (1 / r0) ** I0
        z_obs, z_teo = fin[major].mean(), attack_fraction_deterministic(r0)
        out[k] = dict(R0=r0, p_obs=p_obs, p_teo=p_teo, z_obs=z_obs, z_teo=z_teo, fin=fin)
        print("Cfg %d (R0=%.1f): P(brote mayor) teórica=%.3f obs=%.3f (dif %.2f%%) | tamaño final teórico=%.4f obs=%.4f (dif %.2f%%)" % (
            k, r0, p_teo, p_obs, pct(p_obs, p_teo), z_teo, z_obs, pct(z_obs, z_teo)))
        ax[i].hist(fin, bins=25, color="#8172B2", edgecolor="k")
        ax[i].axvline(z_teo, color="r", ls="--", label="z determinista = %.3f" % z_teo)
        ax[i].set_title("Cfg %d (R0=%.1f): tamaño final / N" % (k, r0)); ax[i].legend(); ax[i].set_xlabel("R∞/N")
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "m5_fig3_estocastico.png"), dpi=150)
    return out


def run_sensitivity(outdir):
    import matplotlib.pyplot as plt
    base = dict(beta=0.4, gamma=0.2, I0=10)

    def f(p):
        t, y = integrate("rk4", p["beta"], p["gamma"], N0, p["I0"], 400.0, 0.1)
        Imax, tpk, Sinf = metrics(t, y)
        return Imax / N0 * 100, tpk, (N0 - Sinf) / N0 * 100

    print("\n" + "=" * 90)
    print("ANÁLISIS DE SENSIBILIDAD (base β=0.4, γ=0.2, I0=10): índice normalizado S=(ΔY/Y)/(Δp/p), ±10 %")
    print("=" * 90)
    yb = f(base)
    print("Base: I_max=%.2f %% N | t_pico=%.1f d | ataque final=%.2f %% N" % yb)
    idx = {}
    for par in ("beta", "gamma", "I0"):
        hi, lo = dict(base), dict(base)
        hi[par] *= 1.1; lo[par] *= 0.9
        yh, yl = f(hi), f(lo)
        idx[par] = [((yh[j] - yl[j]) / yb[j]) / 0.2 for j in range(3)]
        print("%-6s S(I_max)=%+.3f  S(t_pico)=%+.3f  S(ataque)=%+.3f" % (par, *idx[par]))
    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(3); w = 0.25
    for i, par in enumerate(idx):
        ax.bar(x + (i - 1) * w, idx[par], w, label=par)
    ax.set_xticks(x); ax.set_xticklabels(["I_max", "t_pico", "Ataque final"]); ax.axhline(0, color="k", lw=.8)
    ax.set_ylabel("Índice de sensibilidad normalizado"); ax.set_title("Sensibilidad local (±10 %)")
    ax.legend(); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "m5_fig4_sensibilidad.png"), dpi=150)
    return yb, idx


def run_flow_diagram(outdir):
    """Diagrama de flujos y niveles (stock-flow) del SIR."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    fig, ax = plt.subplots(figsize=(9, 3))
    ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 3)
    for x, nm in ((1.0, "S\nSusceptibles"), (4.0, "I\nInfectados"), (7.0, "R\nRecuperados")):
        ax.add_patch(FancyBboxPatch((x, 1.0), 2.0, 1.0, boxstyle="round,pad=0.05", fc="#DDEEFF", ec="k"))
        ax.text(x + 1, 1.5, nm, ha="center", va="center")
    ax.annotate("", xy=(4.0, 1.5), xytext=(3.0, 1.5), arrowprops=dict(arrowstyle="->", lw=2))
    ax.annotate("", xy=(7.0, 1.5), xytext=(6.0, 1.5), arrowprops=dict(arrowstyle="->", lw=2))
    ax.text(3.5, 1.8, "β S I / N", ha="center"); ax.text(6.5, 1.8, "γ I", ha="center")
    ax.text(3.5, 0.4, "β: tasa de contacto efectivo", ha="center", fontsize=8)
    ax.text(6.5, 0.4, "γ: tasa de recuperación", ha="center", fontsize=8)
    ax.set_title("Diagrama de flujos y niveles del modelo SIR")
    fig.savefig(os.path.join(outdir, "m5_fig5_flujos.png"), dpi=150, bbox_inches="tight")


def composite_figure(curves_cfg, conv, sto, sens, outdir):
    """Figura única de validación (Figura 6 del informe): 4 paneles."""
    import matplotlib.pyplot as plt
    dts, errs, ords = conv
    yb, idx = sens
    fig, ax = plt.subplots(2, 2, figsize=(11, 8))
    for k, (t, y, ref) in curves_cfg.items():
        line, = ax[0, 0].plot(t, y[:, 1] / N0, label="Cfg %d (R0=%.1f)" % (k, R0(CONFIGS[k]["beta"], CONFIGS[k]["gamma"])))
        ax[0, 0].plot(t[::100], ref[::100, 1] / N0, "k.", ms=3)
    ax[0, 0].set_xlim(0, 120); ax[0, 0].set_title("(a) I(t)/N: RK4 (línea) y solve_ivp (puntos)")
    ax[0, 0].set_xlabel("t [días]"); ax[0, 0].legend(); ax[0, 0].grid(alpha=.3)
    ax[0, 1].loglog(dts, errs["euler"], "o-", label="Euler (orden %.2f)" % ords["euler"])
    ax[0, 1].loglog(dts, errs["rk4"], "s-", label="RK4 (orden %.2f)" % ords["rk4"])
    ax[0, 1].set_title("(b) Convergencia"); ax[0, 1].set_xlabel("Δt [días]"); ax[0, 1].set_ylabel("Error máx. en I")
    ax[0, 1].legend(); ax[0, 1].grid(alpha=.3, which="both")
    ax[1, 0].hist(sto[2]["fin"], bins=25, color="#8172B2", edgecolor="k")
    ax[1, 0].axvline(sto[2]["z_teo"], color="r", ls="--", label="z determinista")
    ax[1, 0].set_title("(c) Gillespie, R0=2: tamaño final / N"); ax[1, 0].legend()
    x = np.arange(3); w = 0.25
    for i, par in enumerate(idx):
        ax[1, 1].bar(x + (i - 1) * w, idx[par], w, label=par)
    ax[1, 1].set_xticks(x); ax[1, 1].set_xticklabels(["I_max", "t_pico", "Ataque final"])
    ax[1, 1].axhline(0, color="k", lw=.8); ax[1, 1].legend(); ax[1, 1].grid(alpha=.3)
    ax[1, 1].set_title("(d) Índices de sensibilidad (±10 %)")
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "m5_fig_validacion.png"), dpi=170)


def header():
    print("=" * 112)
    print("MODELO 5 - DINÁMICA DE SISTEMAS (SIR)  |  Fecha/hora: %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("Usuario: %s  |  SO: %s  |  Python %s" % (getpass.getuser(), platform.platform(), sys.version.split()[0]))
    print("=" * 112)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prng", choices=["mt", "lcg"], default="mt")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--outdir", default="figs")
    ap.add_argument("--config", type=int, choices=[1, 2, 3], help="ejecuta solo una configuración (para capturas)")
    a = ap.parse_args()
    if not a.show:
        import matplotlib
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    os.makedirs(a.outdir, exist_ok=True)

    header()
    print("PRNG: %s | autotest: %s" % (a.prng.upper(), json.dumps(prng_selftest(a.prng))))
    for k, c in CONFIGS.items():
        if a.config and k != a.config:
            continue
        print("  Cfg %d: %s | β=%.2f γ=%.2f R0=%.2f" % (k, c["nombre"], c["beta"], c["gamma"], R0(c["beta"], c["gamma"])))
    if a.config:
        run_validation(a.outdir, only=[a.config])
        print("\nFigura guardada en: %s" % os.path.abspath(os.path.join(a.outdir, "m5_cfg%d.png" % a.config)))
        if a.show:
            plt.show()
        return
    rows = run_validation(a.outdir)
    conv = run_convergence(a.outdir)
    sto = run_stochastic(a.prng, 100 if a.quick else 300, a.outdir)
    sens = run_sensitivity(a.outdir)
    run_flow_diagram(a.outdir)
    composite_figure(LAST_CURVES, conv, sto, sens, a.outdir)
    with open(os.path.join(a.outdir, "m5_resultados.json"), "w") as f:
        json.dump({"rows": rows, "conv_orders": conv[2], "stoch": {k: {x: y for x, y in v.items() if x != "fin"} for k, v in sto.items()},
                   "sens_base": sens[0], "sens_idx": sens[1]}, f, default=float, indent=1)
    print("\nFiguras guardadas en: %s" % os.path.abspath(a.outdir))
    if a.show:
        plt.show()


if __name__ == "__main__":
    main()