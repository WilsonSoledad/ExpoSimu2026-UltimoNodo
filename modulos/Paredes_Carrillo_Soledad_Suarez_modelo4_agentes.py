#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modelo 4 - Simulación Basada en Agentes: enjambre de bots (Último Nodo).
Modelo de Vicsek extendido con (i) separación entre bots y (ii) atracción hacia la
puerta (firewall) más débil. Módulo standalone (independiente del juego).

Uso:
    python apellido1_apellido2_modelo4_agentes.py            # validación completa
    python apellido1_apellido2_modelo4_agentes.py --show     # muestra los gráficos
    python apellido1_apellido2_modelo4_agentes.py --prng lcg # usa el LCG en vez de MT19937
    python apellido1_apellido2_modelo4_agentes.py --quick    # corrida rápida
    python apellido1_apellido2_modelo4_agentes.py --config 2 --show   # solo la configuración 2 (capturas)

PRNG: MT19937 (implementación propia) y LCG. >>> Confirmar cuál fue el del taller anterior. <<<
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

# ----------------------------------------------------------------------------
# 1. GENERADORES PSEUDOALEATORIOS
# ----------------------------------------------------------------------------


class MT19937:
    """Mersenne Twister de 32 bits (implementación propia)."""

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
    """X_{n+1} = (a X_n + c) mod m."""

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
# 2. MODELO DE ENJAMBRE
# ----------------------------------------------------------------------------
# Puertas (firewalls) con direcciones fijas respecto al enjambre y su "salud".
GATE_ANGLES = np.array([0.0, 2 * math.pi / 3, 4 * math.pi / 3])
GATE_HEALTH = np.array([0.8, 0.3, 0.6])
WEAK = int(np.argmin(GATE_HEALTH))          # puerta más débil


def swarm_run(N, L, r, eta, v0, steps, prng, track_msd=False, w=0.0, r_sep=0.0,
              sep_gain=1.0, window=0.4):
    """
    Estado: x_i en [0,L)^2 (toro) y theta_i. Regla de actualización:
        u_i = (1/n_i) sum_{j in B_r(i)} e^{i theta_j}  +  w e^{i alpha*}
              + g * sum_{j != i, d_ij < r_sep} (1 - d_ij/r_sep) (x_i - x_j)/d_ij
        theta_i(t+1) = arg(u_i) + eta (U - 1/2)
        x_i(t+1)     = x_i(t) + v0 (cos theta_i(t+1), sin theta_i(t+1))
    Con w=0 y r_sep=0 se recupera el modelo de Vicsek.  alpha* = dirección de la puerta más débil.
    Decisión del bot: la puerta k que maximiza cos(theta_i - alpha_k).
    """
    pos = L * prng.array(2 * N).reshape(N, 2)
    theta = 2 * math.pi * prng.array(N) - math.pi
    unwrapped, origin = pos.copy(), pos.copy()
    global_coupling = r >= L
    start = int(steps * (1 - window))
    alpha = GATE_ANGLES[WEAK]
    phi = np.zeros(steps)
    pg = np.full(steps, np.nan)
    dnn = np.full(steps, np.nan)
    msd = np.zeros(steps) if track_msd else None

    for t in range(steps):
        c, s = np.cos(theta), np.sin(theta)
        need_d = (not global_coupling) or r_sep > 0 or t >= start
        if need_d:
            d = pos[:, None, :] - pos[None, :, :]
            d -= L * np.round(d / L)
            dist2 = (d ** 2).sum(-1)
        if global_coupling:
            ux, uy = np.full(N, c.mean()), np.full(N, s.mean())
        else:
            A = (dist2 <= r * r).astype(float)
            n = A.sum(1)
            ux, uy = (A @ c) / n, (A @ s) / n
        if w > 0:
            ux = ux + w * math.cos(alpha)
            uy = uy + w * math.sin(alpha)
        if r_sep > 0:
            dist = np.sqrt(dist2)
            mask = (dist2 < r_sep * r_sep) & (dist2 > 0)
            f = np.where(mask, (1 - dist / r_sep) / np.where(dist > 0, dist, 1.0), 0.0)
            ux = ux + sep_gain * (f * d[:, :, 0]).sum(1)
            uy = uy + sep_gain * (f * d[:, :, 1]).sum(1)
        theta = np.arctan2(uy, ux) + eta * (prng.array(N) - 0.5)
        step = v0 * np.column_stack((np.cos(theta), np.sin(theta)))
        if t >= start:
            d2 = dist2.copy()
            np.fill_diagonal(d2, np.inf)
            dnn[t] = np.sqrt(d2.min(1)).mean()
        pos = (pos + step) % L
        unwrapped += step
        phi[t] = math.hypot(np.cos(theta).mean(), np.sin(theta).mean())
        choice = np.argmax(np.cos(theta[:, None] - GATE_ANGLES[None, :]), axis=1)
        if t >= start:
            pg[t] = float((choice == WEAK).mean())
        if track_msd:
            msd[t] = ((unwrapped - origin) ** 2).sum(1).mean()
    return {"phi": phi, "pg": pg, "dnn": dnn, "msd": msd, "pos": pos, "theta": theta}


def steady(x, frac=0.4):
    return float(x[int(len(x) * (1 - frac)):].mean())


def replicate(N, L, r, eta, v0, steps, reps, kind, seed0, track_msd=False, w=0.0, r_sep=0.0):
    out = {"phi": [], "pg": [], "dnn": [], "msd": [], "last": None}
    for k in range(reps):
        res = swarm_run(N, L, r, eta, v0, steps, make_prng(kind, seed0 + k), track_msd, w, r_sep)
        out["phi"].append(steady(res["phi"]))
        out["pg"].append(float(np.nanmean(res["pg"])))
        out["dnn"].append(float(np.nanmean(res["dnn"])))
        if track_msd:
            out["msd"].append(res["msd"])
        if k == 0:
            out["last"] = res
    for key in ("phi", "pg", "dnn", "msd"):
        out[key] = np.array(out[key]) if len(out[key]) else None
    return out


def ci95(x):
    x = np.asarray(x, float)
    if len(x) < 2:
        return float(x.mean()), 0.0
    return float(x.mean()), float(stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / math.sqrt(len(x)))


def pct(obt, teo):
    return abs(obt - teo) / abs(teo) * 100 if teo != 0 else float("nan")


# ----------------------------------------------------------------------------
# 3. TEORÍA PARA VALIDAR
# ----------------------------------------------------------------------------
def phi_global_theory(eta):
    """Acoplamiento global: phi = E[cos(eta U)] = sin(eta/2)/(eta/2)."""
    return 1.0 if eta == 0 else math.sin(eta / 2) / (eta / 2)


def phi_uncoupled_theory(N):
    return math.sqrt(math.pi) / (2 * math.sqrt(N))


def pgate_theory(eta, w, r_sep=0.0, uncoupled=False):
    """
    Sin interacción y con ruido total: direcciones uniformes -> 1/G.
    Acoplamiento global con w>0: el enjambre se orienta hacia alpha*, theta_i = alpha* + xi_i,
    xi ~ U(-eta/2, eta/2); elige la puerta débil si |xi| < pi/G  ->  P = min(1, (2 pi/G)/eta).
    """
    G = len(GATE_ANGLES)
    if uncoupled:
        return 1.0 / G
    return min(1.0, (2 * math.pi / G) / eta)


def dnn_theory(N, L):
    """E[d_nn] para N puntos uniformes iid en un toro de lado L: integral de (1 - pi r^2/L^2)^(N-1)."""
    r = np.linspace(0, L / 2, 20001)
    return float(np.trapezoid((1 - math.pi * r ** 2 / L ** 2) ** (N - 1), r))


# ----------------------------------------------------------------------------
# 4. VALIDACIÓN EXPERIMENTAL, SENSIBILIDAD, GRÁFICOS
# ----------------------------------------------------------------------------
CONFIGS = {
    1: dict(nombre="Sin interacción", N=200, L=10.0, r=0.0, eta=2 * math.pi, v0=0.1, w=0.0, r_sep=0.0, steps=300),
    2: dict(nombre="Global, ruido bajo, atracción a puerta débil", N=200, L=10.0, r=10.0, eta=1.0, v0=0.1, w=0.3, r_sep=0.0, steps=300),
    3: dict(nombre="Global, ruido alto, atracción a puerta débil", N=100, L=10.0, r=10.0, eta=4.0, v0=0.1, w=0.3, r_sep=0.0, steps=300),
}


def run_validation(kind, reps, outdir, only=None):
    import matplotlib.pyplot as plt
    rows, store = [], {}
    for k, c in CONFIGS.items():
        if only and k not in only:
            continue
        rp = replicate(c["N"], c["L"], c["r"], c["eta"], c["v0"], c["steps"], reps, kind, 1000 * k,
                       track_msd=(k == 1), w=c["w"], r_sep=c["r_sep"])
        store[k] = rp
        m_phi, h_phi = ci95(rp["phi"])
        m_pg, h_pg = ci95(rp["pg"])
        m_d, h_d = ci95(rp["dnn"])
        if k == 1:
            t_phi = phi_uncoupled_theory(c["N"])
            n = 100
            m_msd, h_msd = ci95(rp["msd"][:, n - 1])
            t_msd = n * c["v0"] ** 2
            rows += [(k, "phi", t_phi, m_phi, h_phi, pct(m_phi, t_phi)),
                     (k, "MSD(n=100)", t_msd, m_msd, h_msd, pct(m_msd, t_msd)),
                     (k, "P(puerta debil)", pgate_theory(c["eta"], c["w"], uncoupled=True), m_pg, h_pg,
                      pct(m_pg, pgate_theory(c["eta"], c["w"], uncoupled=True))),
                     (k, "d_nn medio", dnn_theory(c["N"], c["L"]), m_d, h_d, pct(m_d, dnn_theory(c["N"], c["L"])))]
        else:
            t_phi, t_pg = phi_global_theory(c["eta"]), pgate_theory(c["eta"], c["w"])
            rows += [(k, "phi", t_phi, m_phi, h_phi, pct(m_phi, t_phi)),
                     (k, "P(puerta debil)", t_pg, m_pg, h_pg, pct(m_pg, t_pg)),
                     (k, "d_nn medio (obs.)", None, m_d, h_d, None)]

    print("\n" + "=" * 96)
    print("TABLA DE VALIDACIÓN EXPERIMENTAL - MODELO 4 (enjambre)   [IC 95 %%, %d réplicas]" % reps)
    print("=" * 96)
    print("%-4s %-20s %-12s %-12s %-10s %-8s" % ("Cfg", "Métrica", "Teórico", "Obtenido", "±IC95", "Dif.%"))
    for k, name, teo, obt, h, d in rows:
        print("%-4d %-20s %-12s %-12.5f %-10.5f %-8s" % (
            k, name, "-" if teo is None else "%.5f" % teo, obt, h, "-" if d is None else "%.2f" % d))

    if only:
        return rows, store
    # Figuras individuales (anexos)
    fig, ax = plt.subplots(1, 3, figsize=(15, 5))
    for i, (k, c) in enumerate(CONFIGS.items()):
        last = store[k]["last"]
        p, th = last["pos"], last["theta"]
        ax[i].quiver(p[:, 0], p[:, 1], np.cos(th), np.sin(th), th, cmap="hsv", scale=40, width=0.004)
        ax[i].set_xlim(0, c["L"]); ax[i].set_ylim(0, c["L"]); ax[i].set_aspect("equal")
        ax[i].set_title("Cfg %d: %s\nη=%.2f, r=%.1f, N=%d" % (k, c["nombre"], c["eta"], c["r"], c["N"]), fontsize=9)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "m4_fig1_snapshots.png"), dpi=150)
    return rows, store


def run_sweep(kind, reps, outdir):
    import matplotlib.pyplot as plt
    etas = np.arange(0.0, 6.3, 0.6)
    N, L, v0, steps = 200, 7.0, 0.1, 250
    loc = np.array([ci95(replicate(N, L, 1.0, e, v0, steps, reps, kind, 77)["phi"]) for e in etas])
    glob = np.array([ci95(replicate(N, L, L, e, v0, steps, reps, kind, 99)["phi"]) for e in etas])
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ee = np.linspace(0.01, 2 * math.pi, 200)
    ax.plot(ee, [phi_global_theory(e) for e in ee], "k--", label="Teoría acoplamiento global")
    ax.errorbar(etas, glob[:, 0], glob[:, 1], fmt="s", ms=4, label="Simulación global (r=L)")
    ax.errorbar(etas, loc[:, 0], loc[:, 1], fmt="o-", ms=4, label="Simulación local (r=1, ρ≈4.1)")
    ax.set_xlabel("Amplitud de ruido η [rad]"); ax.set_ylabel("Polarización φ")
    ax.set_title("Transición orden-desorden"); ax.legend(); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "m4_fig5_barrido_ruido.png"), dpi=150)
    return etas, loc, glob


def run_sensitivity(kind, reps, outdir):
    """One-at-a-time alrededor del caso base."""
    import matplotlib.pyplot as plt
    base = dict(N=200, L=7.0, r=1.0, eta=2.0, v0=0.1, w=0.3, r_sep=0.0)
    grid = {"eta": [0.5, 2.0, 4.0], "r": [0.3, 1.0, 2.0], "N": [50, 200, 400],
            "r_sep": [0.0, 0.2, 0.5], "w": [0.0, 0.3, 1.0]}
    out = {}
    print("\n" + "=" * 100)
    print("ANÁLISIS DE SENSIBILIDAD (base N=200, L=7, r=1, η=2, v0=0.1, w=0.3, r_sep=0; %d réplicas)" % reps)
    print("=" * 100)
    for par, vals in grid.items():
        res = []
        for v in vals:
            p = dict(base); p[par] = v
            rp = replicate(p["N"], p["L"], p["r"], p["eta"], p["v0"], 250, reps, kind, 555, w=p["w"], r_sep=p["r_sep"])
            res.append((v, ci95(rp["phi"])[0], ci95(rp["pg"])[0], ci95(rp["dnn"])[0]))
        out[par] = res
        rg = [max(x[j] for x in res) - min(x[j] for x in res) for j in (1, 2, 3)]
        print("%-6s " % par + " | ".join("%s: φ=%.3f P=%.3f d=%.3f" % x for x in res) +
              "  || rango φ=%.3f P=%.3f d=%.3f" % tuple(rg))
    names = list(out)
    rng = np.array([[max(x[j] for x in out[p]) - min(x[j] for x in out[p]) for j in (1, 2, 3)] for p in names])
    rel = rng / rng.max(0)
    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(len(names)); w_ = 0.27
    for j, nm in enumerate(("φ", "P(puerta débil)", "d_nn")):
        ax.bar(x + (j - 1) * w_, rel[:, j], w_, label=nm)
    ax.set_xticks(x); ax.set_xticklabels(names); ax.set_ylabel("Efecto relativo (rango / máximo)")
    ax.set_title("Sensibilidad del enjambre"); ax.legend(); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "m4_fig6_sensibilidad.png"), dpi=150)
    return out, names, rng


def composite_figure(store, sweep, sens_pack, outdir):
    """Figura única de validación (Figura 5 del informe): 4 paneles."""
    import matplotlib.pyplot as plt
    etas, loc, glob = sweep
    sens, names, rng = sens_pack
    rel = rng / rng.max(0)
    fig, ax = plt.subplots(2, 2, figsize=(11, 8))
    for k, c in CONFIGS.items():
        line, = ax[0, 0].plot(store[k]["last"]["phi"], label="Cfg %d" % k)
        t = phi_uncoupled_theory(c["N"]) if k == 1 else phi_global_theory(c["eta"])
        ax[0, 0].axhline(t, ls="--", color=line.get_color(), alpha=.7)
    ax[0, 0].set_title("(a) φ(t); punteado = teoría"); ax[0, 0].set_xlabel("t"); ax[0, 0].legend(); ax[0, 0].grid(alpha=.3)
    n = np.arange(1, CONFIGS[1]["steps"] + 1)
    mm = store[1]["msd"].mean(0)
    ax[0, 1].plot(n, mm, label="Simulación"); ax[0, 1].plot(n, n * CONFIGS[1]["v0"] ** 2, "k--", label="n·v0²")
    ax[0, 1].set_title("(b) MSD, configuración 1"); ax[0, 1].set_xlabel("n"); ax[0, 1].legend(); ax[0, 1].grid(alpha=.3)
    ee = np.linspace(0.01, 2 * math.pi, 200)
    ax[1, 0].plot(ee, [phi_global_theory(e) for e in ee], "k--", label="Teoría global")
    ax[1, 0].errorbar(etas, glob[:, 0], glob[:, 1], fmt="s", ms=3, label="Global")
    ax[1, 0].errorbar(etas, loc[:, 0], loc[:, 1], fmt="o-", ms=3, label="Local (r=1)")
    ax[1, 0].set_title("(c) φ frente a η"); ax[1, 0].set_xlabel("η [rad]"); ax[1, 0].legend(); ax[1, 0].grid(alpha=.3)
    x = np.arange(len(names)); w_ = 0.27
    for j, nm in enumerate(("φ", "P(puerta débil)", "d_nn")):
        ax[1, 1].bar(x + (j - 1) * w_, rel[:, j], w_, label=nm)
    ax[1, 1].set_xticks(x); ax[1, 1].set_xticklabels(names); ax[1, 1].legend()
    ax[1, 1].set_title("(d) Efecto relativo de cada parámetro"); ax[1, 1].grid(alpha=.3)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "m4_fig_validacion.png"), dpi=170)


def config_figure(k, store, outdir):
    """Figura de una sola configuración (para la captura de pantalla)."""
    import matplotlib.pyplot as plt
    c, rp = CONFIGS[k], store[k]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.8))
    p, th = rp["last"]["pos"], rp["last"]["theta"]
    ax[0].quiver(p[:, 0], p[:, 1], np.cos(th), np.sin(th), th, cmap="hsv", scale=40, width=0.004)
    ax[0].set_xlim(0, c["L"]); ax[0].set_ylim(0, c["L"]); ax[0].set_aspect("equal")
    ax[0].set_title("Cfg %d: estado final del enjambre\nN=%d, r=%.1f, η=%.2f, w=%.1f" % (k, c["N"], c["r"], c["eta"], c["w"]), fontsize=10)
    ax[1].plot(rp["last"]["phi"], label="φ(t) simulado")
    t = phi_uncoupled_theory(c["N"]) if k == 1 else phi_global_theory(c["eta"])
    ax[1].axhline(t, color="r", ls="--", label="φ teórico = %.4f" % t)
    ax[1].set_xlabel("Paso t"); ax[1].set_ylabel("Polarización φ"); ax[1].legend(); ax[1].grid(alpha=.3)
    ax[1].set_title("Cfg %d: evolución de la polarización" % k, fontsize=10)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "m4_cfg%d.png" % k), dpi=150)


def header():
    print("=" * 96)
    print("MODELO 4 - ENJAMBRE DE BOTS  |  Fecha/hora: %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("Usuario: %s  |  SO: %s  |  Python %s" % (getpass.getuser(), platform.platform(), sys.version.split()[0]))
    print("=" * 96)


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
    reps = 4 if a.quick else 10

    header()
    print("PRNG: %s | autotest: %s" % (a.prng.upper(), json.dumps(prng_selftest(a.prng))))
    print("Puertas (ángulo, salud): %s ; puerta más débil = #%d" % (list(zip(np.round(GATE_ANGLES, 3), GATE_HEALTH)), WEAK + 1))
    for k, c in CONFIGS.items():
        if a.config and k != a.config:
            continue
        print("  Cfg %d: %s" % (k, {x: (round(y, 4) if isinstance(y, float) else y) for x, y in c.items()}))
    if a.config:
        rows, store = run_validation(a.prng, reps, a.outdir, only=[a.config])
        config_figure(a.config, store, a.outdir)
        print("\nFigura guardada en: %s" % os.path.abspath(os.path.join(a.outdir, "m4_cfg%d.png" % a.config)))
        if a.show:
            plt.show()
        return
    rows, store = run_validation(a.prng, reps, a.outdir)
    sweep = run_sweep(a.prng, 3 if a.quick else 5, a.outdir)
    sens = run_sensitivity(a.prng, 3 if a.quick else 5, a.outdir)
    composite_figure(store, sweep, sens, a.outdir)
    with open(os.path.join(a.outdir, "m4_resultados.json"), "w") as f:
        json.dump({"rows": rows, "sens": sens[0]}, f, default=float, indent=1)
    print("\nFiguras guardadas en: %s" % os.path.abspath(a.outdir))
    if a.show:
        plt.show()


if __name__ == "__main__":
    main()