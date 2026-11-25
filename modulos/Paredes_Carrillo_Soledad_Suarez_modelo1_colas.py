import math
import heapq
import getpass
from datetime import datetime
import matplotlib.pyplot as plt

# ==============================================================================
# GENERADOR PRNG REUTILIZADO DEL TALLER 1 (generadores/congruencial_multiplicativo.py)
# Referencia: Park, S.K. & Miller, K.W. (1988)
# ==============================================================================
def congruencial_multiplicativo(semilla, a, m, cantidad):
    xi_lista = []
    ri_lista = []
    x = semilla
    for _ in range(cantidad):
        x = (a * x) % m
        ri = x / m
        xi_lista.append(x)
        ri_lista.append(ri)
    return xi_lista, ri_lista


class GeneradorParkMiller:
    """Envoltorio con estado del congruencial multiplicativo: gen.random() -> R_i en [0, 1)."""

    def __init__(self, semilla=12345, a=16807, m=2 ** 31 - 1):
        self.a, self.m = a, m
        self.x = int(semilla) % m or 1          # la semilla no puede ser 0
        self.nombre = f"Congruencial multiplicativo (a={a}, m=2^31-1)"

    def random(self):
        xs, rs = congruencial_multiplicativo(self.x, self.a, self.m, 1)
        self.x = xs[0]
        return rs[0]


def exponencial(gen, tasa):
    """Transformada inversa: t = -ln(1 - R_i) / tasa."""
    return -math.log(1.0 - gen.random()) / tasa

# ==============================================================================
# CÁLCULOS TEÓRICOS M/M/c (Fórmula C de Erlang)
# ==============================================================================
def metricas_teoricas_mmc(lam, mu, c):
    rho = lam / (c * mu)
    if rho >= 1:
        raise ValueError("Sistema inestable: rho >= 1")
    a = lam / mu  # Tráfico ofrecido (Erlangs)

    # Probabilidad de sistema vacío (P0)
    suma = sum((a ** k) / math.factorial(k) for k in range(c))
    termino_c = ((a ** c) / math.factorial(c)) * (1 / (1 - rho))
    p0 = 1.0 / (suma + termino_c)

    # Probabilidad de espera (Pw - Erlang C)
    pw = termino_c * p0

    # Métricas de desempeño
    lq = (pw * rho) / (1 - rho)
    wq = lq / lam
    w = wq + (1.0 / mu)
    l = lam * w
    return {"rho": rho, "P0": p0, "Pw": pw, "Lq": lq, "L": l, "Wq": wq, "W": w}

# ==============================================================================
# CÁLCULOS TEÓRICOS M/M/c/K (capacidad finita: el juego usa este modelo)
# ==============================================================================
def teoria_mmck(lam, mu, c, K):
    """Medidas de desempeño en estado estacionario del modelo M/M/c/K.

        P_n = a^n / n! * P0                 n < c
        P_n = a^n / (c! c^(n-c)) * P0       c <= n <= K        (a = lam / mu)
        lam_eff = lam (1 - P_K),  W = L / lam_eff,  Wq = Lq / lam_eff
    No requiere rho < 1 porque la capacidad es finita.
    """
    a = lam / mu
    terminos = []
    for n in range(K + 1):
        if n < c:
            terminos.append(a ** n / math.factorial(n))
        else:
            terminos.append(a ** n / (math.factorial(c) * c ** (n - c)))
    p0 = 1.0 / sum(terminos)
    p = [t * p0 for t in terminos]
    L = sum(n * pn for n, pn in enumerate(p))
    Lq = sum((n - c) * pn for n, pn in enumerate(p) if n > c)
    lam_eff = lam * (1 - p[K])
    W = L / lam_eff if lam_eff > 0 else float("nan")
    Wq = Lq / lam_eff if lam_eff > 0 else float("nan")
    return {"rho": a / c, "P0": p0, "PK": p[K], "L": L, "Lq": Lq, "W": W, "Wq": Wq, "lam_eff": lam_eff}

# ==============================================================================
# SIMULACIÓN DE EVENTOS DISCRETOS M/M/c (Firewalls analizando amenazas)
# ==============================================================================
def simular_colas_mmc(lam, mu, c, num_amenazas=20000, semilla=12345):
    # Parámetros Park-Miller (período máximo 2^31 - 2)
    a_prng = 16807
    m_prng = 2147483647

    # Necesitamos 2 números uniformes por cada entidad (llegada y servicio)
    _, ri = congruencial_multiplicativo(semilla, a_prng, m_prng, num_amenazas * 2 + 10)
    idx_r = 0

    def exp_inversa(tasa):
        nonlocal idx_r
        r = ri[idx_r]
        idx_r += 1
        return -math.log(1.0 - r) / tasa

    reloj = 0.0
    servidores_libres_en = [0.0] * c  # Min-heap con el tiempo en que se libera cada firewall
    heapq.heapify(servidores_libres_en)

    tiempos_espera = []
    tiempos_sistema = []

    for _ in range(num_amenazas):
        # Generar próxima llegada
        reloj += exp_inversa(lam)

        tiempo_servicio = exp_inversa(mu)
        prox_libre = heapq.heappop(servidores_libres_en)

        if prox_libre <= reloj:
            # Hay al menos un firewall libre: atención inmediata
            espera = 0.0
            inicio_servicio = reloj
        else:
            # Todos los firewalls ocupados: la amenaza espera en buffer
            espera = prox_libre - reloj
            inicio_servicio = prox_libre

        fin_servicio = inicio_servicio + tiempo_servicio
        heapq.heappush(servidores_libres_en, fin_servicio)

        tiempos_espera.append(espera)
        tiempos_sistema.append(espera + tiempo_servicio)

    wq_sim = sum(tiempos_espera) / num_amenazas
    w_sim = sum(tiempos_sistema) / num_amenazas
    lq_sim = lam * wq_sim  # Ley de Little: Lq = lambda * Wq
    l_sim = lam * w_sim    # Ley de Little: L = lambda * W

    return {"Wq": wq_sim, "W": w_sim, "Lq": lq_sim, "L": l_sim}

# ==============================================================================
# SIMULACIÓN DE EVENTOS DISCRETOS M/M/c/K
# ==============================================================================
def simular_colas_mmck(lam, mu, c, K, num_amenazas=30000, semilla=12345):
    """DES de un firewall con c servidores y capacidad total K (FIFO).

    Una amenaza que llega con K entidades en el sistema se bloquea (brecha).
    Llegadas y servicios usan flujos Park-Miller distintos, como se vio en clase.
    """
    gen_ll = GeneradorParkMiller(semilla)
    gen_sv = GeneradorParkMiller(semilla + 7919)
    reloj = 0.0
    libres = [0.0] * c          # instante en que se libera cada servidor
    salidas = []                # instantes de salida de las entidades en el sistema
    bloqueadas = 0
    esperas, sistemas = [], []
    for _ in range(num_amenazas):
        reloj += exponencial(gen_ll, lam)
        salidas = [s for s in salidas if s > reloj]
        if len(salidas) >= K:
            bloqueadas += 1
            continue
        i = min(range(c), key=lambda j: libres[j])
        inicio = max(reloj, libres[i])
        fin = inicio + exponencial(gen_sv, mu)
        libres[i] = fin
        salidas.append(fin)
        esperas.append(inicio - reloj)
        sistemas.append(fin - reloj)
    atendidas = len(sistemas)
    lam_eff = atendidas / reloj
    w_sim = sum(sistemas) / atendidas
    wq_sim = sum(esperas) / atendidas
    return {"W": w_sim, "Wq": wq_sim, "L": lam_eff * w_sim, "Lq": lam_eff * wq_sim,
            "PK": bloqueadas / num_amenazas}


def simular_rapido(gen_ll, gen_sv, lam, mu, c, K, n, llegadas=None):
    """Simulación de eventos discretos de una puerta, sin estadísticas.

    Si se pasan 'llegadas' (tiempos absolutos), se usan esas en vez de
    generar llegadas de Poisson. Devuelve (tiempos de las bloqueadas, n).
    La usa el Predictor Monte Carlo del juego.
    """
    if llegadas is None:
        llegadas, t = [], 0.0
        for _ in range(n):
            t += exponencial(gen_ll, lam)
            llegadas.append(t)
    libres = [0.0] * c
    salidas = []
    bloqueadas = []
    for at in llegadas:
        salidas = [s for s in salidas if s > at]
        if len(salidas) >= K:
            bloqueadas.append(at)
            continue
        i = min(range(c), key=lambda j: libres[j])
        inicio = max(at, libres[i])
        fin = inicio + exponencial(gen_sv, mu)
        libres[i] = fin
        salidas.append(fin)
    return bloqueadas, len(llegadas)

# ==============================================================================
# MODELO CON ESTADO PARA EL JUEGO (una puerta / firewall en tiempo real)
# ==============================================================================
class ModeloColas:
    """Cola M/M/c/K que avanza con el reloj del juego (paso(dt)).

    Cada entidad atendida queda en self.registro con AT, WT, ST y ET
    (ET = AT + WT + ST), igual que la tabla vista en clase.
    """
    nombre = "Colas M/M/c/K"

    def __init__(self, gen_llegadas, gen_servicio, lam, mu, c, K, llegadas_poisson=True):
        self.gen_ll = gen_llegadas
        self.gen_sv = gen_servicio
        # False en las puertas 2 y 3: les llegan desbordes y bots, no un Poisson(lambda)
        self.llegadas_poisson = llegadas_poisson
        self.lam, self.mu = lam, mu
        self.c, self.K = c, max(K, c)
        self.t = 0.0
        self.servidores = []    # dicts: id, AT, inicio, ST, fin
        self.cola = []          # tuplas (id, AT)
        self.reiniciar_estadisticas()

    # ------------------------------------------------------------ dinámica
    def interllegada(self):
        return exponencial(self.gen_ll, self.lam)

    def en_sistema(self):
        return len(self.servidores) + len(self.cola)

    def llegada(self, id_):
        """Registra una llegada. Retorna False si el sistema está lleno (bloqueo)."""
        self.llegadas += 1
        if self.en_sistema() >= self.K:
            self.bloqueos += 1
            return False
        if len(self.servidores) < self.c:
            self._iniciar_servicio(id_, self.t, self.t)
        else:
            self.cola.append((id_, self.t))
        return True

    def _iniciar_servicio(self, id_, at, inicio):
        st = exponencial(self.gen_sv, self.mu)
        self.servidores.append({"id": id_, "AT": at, "inicio": inicio, "ST": st, "fin": inicio + st})

    def paso(self, dt):
        """Avanza el reloj dt segundos y devuelve los ids que salieron."""
        self.area_L += self.en_sistema() * dt
        self.t_estad += dt
        self.t += dt
        terminados = []
        while self.servidores:
            primero = min(self.servidores, key=lambda s: s["fin"])
            if primero["fin"] > self.t:
                break
            self.servidores.remove(primero)
            terminados.append(primero["id"])
            wt = primero["inicio"] - primero["AT"]
            self.atendidos += 1
            self.suma_W += wt + primero["ST"]
            self.suma_Wq += wt
            self.registro.append((primero["id"], primero["AT"], wt, primero["ST"],
                                  primero["AT"] + wt + primero["ST"]))
            if self.cola:
                id_, at = self.cola.pop(0)
                self._iniciar_servicio(id_, at, primero["fin"])
        while len(self.servidores) < self.c and self.cola:
            id_, at = self.cola.pop(0)
            self._iniciar_servicio(id_, at, self.t)
        return terminados

    def posicion(self, id_):
        for i, s in enumerate(self.servidores):
            if s["id"] == id_:
                return ("servicio", i)
        for i, (cid, _) in enumerate(self.cola):
            if cid == id_:
                return ("cola", i)
        return None

    # ------------------------------------------------------------ mejoras
    def agregar_servidor(self):
        self.c += 1
        self.K = max(self.K, self.c)
        self.reiniciar_estadisticas()

    def ampliar_capacidad(self, n=2):
        self.K += n
        self.reiniciar_estadisticas()

    def mejorar_servicio(self, delta):
        """Aumenta mu. Los servicios en curso conservan su ST; los nuevos usan la nueva tasa."""
        self.mu = round(self.mu + delta, 4)
        self.reiniciar_estadisticas()

    def reiniciar_estadisticas(self):
        """Las métricas se miden desde el último cambio de c o K."""
        self.llegadas = self.bloqueos = self.atendidos = 0
        self.suma_W = self.suma_Wq = 0.0
        self.area_L = 0.0
        self.t_estad = 0.0
        self.registro = []

    # ------------------------------------------------------------ teoría
    def teoria(self, lam=None):
        return teoria_mmck(lam if lam is not None else self.lam, self.mu, self.c, self.K)

    def metricas(self):
        # La teoría se evalúa con la tasa observada: a las puertas 2 y 3 solo
        # llegan los desbordes de la anterior y los bots. Con menos de 10
        # llegadas no hay datos suficientes y se muestra "—".
        lam_obs = self.llegadas / self.t_estad if self.t_estad > 0 else 0.0
        if self.llegadas >= 10:
            teo = self.teoria(lam_obs)
        else:
            teo = dict.fromkeys(("L", "W", "Wq", "PK"), float("nan"))
        w_obs = self.suma_W / self.atendidos if self.atendidos else float("nan")
        wq_obs = self.suma_Wq / self.atendidos if self.atendidos else float("nan")
        l_obs = self.area_L / self.t_estad if self.t_estad > 0 else float("nan")
        pb_obs = self.bloqueos / self.llegadas if self.llegadas else float("nan")
        return [
            ("λ (llegadas/s)", lam_obs, self.lam if self.llegadas_poisson else float("nan")),
            ("L (en sistema)", l_obs, teo["L"]),
            ("W (s en sistema)", w_obs, teo["W"]),
            ("Wq (s en cola)", wq_obs, teo["Wq"]),
            ("P(bloqueo)", pb_obs, teo["PK"]),
        ]

    def exportar_csv(self, ruta):
        """Tabla AT, WT, ST, ET de las entidades atendidas (para el informe)."""
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("id,AT,WT,ST,ET\n")
            for fila in self.registro:
                f.write(",".join(f"{v:.5f}" if isinstance(v, float) else str(v) for v in fila) + "\n")

# ==============================================================================
# EJECUCIÓN DE VALIDACIÓN EXPERIMENTAL (3 CONFIGURACIONES M/M/c + 3 M/M/c/K)
# ==============================================================================
if __name__ == "__main__":
    print("=" * 78)
    print("MODELO 1: SISTEMA DE COLAS M/M/c y M/M/c/K (FIREWALLS - JUEGO 'ÚLTIMO NODO')")
    print(f"Usuario SO : {getpass.getuser()} | Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("PRNG       : Congruencial Multiplicativo (Park-Miller: a=16807, m=2^31-1)")
    print("=" * 78)

    # ---------------------------------------------------------------- M/M/c
    print("\n--- PARTE A: M/M/c (capacidad infinita, Erlang-C) ---")
    configuraciones = [
        {"nombre": "Config 1 (Nivel 1 - 1 Firewall)",   "lam": 4.0,  "mu": 6.0, "c": 1, "semilla": 101},
        {"nombre": "Config 2 (Nivel 2 - 2 Firewalls)",  "lam": 10.0, "mu": 8.0, "c": 2, "semilla": 202},
        {"nombre": "Config 3 (Nivel 3 - Carga Alta)",   "lam": 18.0, "mu": 8.0, "c": 3, "semilla": 303},
    ]

    resultados_grafica = []

    for cfg in configuraciones:
        teo = metricas_teoricas_mmc(cfg["lam"], cfg["mu"], cfg["c"])
        sim = simular_colas_mmc(cfg["lam"], cfg["mu"], cfg["c"], num_amenazas=30000, semilla=cfg["semilla"])

        err_wq = abs(sim["Wq"] - teo["Wq"]) / teo["Wq"] * 100
        err_l  = abs(sim["L"]  - teo["L"])  / teo["L"]  * 100

        print(f"\n>>> {cfg['nombre']} | Parámetros: lambda={cfg['lam']}, mu={cfg['mu']}, c={cfg['c']} (rho={teo['rho']:.3f})")
        print(f"    Teórico  -> Wq = {teo['Wq']:.4f} | W = {teo['W']:.4f} | Lq = {teo['Lq']:.4f} | L = {teo['L']:.4f}")
        print(f"    Simulado -> Wq = {sim['Wq']:.4f} | W = {sim['W']:.4f} | Lq = {sim['Lq']:.4f} | L = {sim['L']:.4f}")
        print(f"    Error %  -> Err(Wq) = {err_wq:.2f}% | Err(L) = {err_l:.2f}%")
        resultados_grafica.append((cfg["nombre"], teo["Wq"], sim["Wq"]))

    # Gráfica de validación: Tiempo promedio en cola (Teórico vs Simulado)
    nombres = [r[0].split("(")[0].strip() for r in resultados_grafica]
    wq_teoricos = [r[1] for r in resultados_grafica]
    wq_simulados = [r[2] for r in resultados_grafica]

    x = range(len(nombres))
    plt.figure(figsize=(8, 5))
    plt.bar([i - 0.15 for i in x], wq_teoricos, width=0.3, label="Teórico (Fórmula Erlang-C)", color="#00d4ff")
    plt.bar([i + 0.15 for i in x], wq_simulados, width=0.3, label="Simulado (PRNG Multiplicativo)", color="#ff2a85")
    plt.xticks(x, nombres)
    plt.ylabel("Tiempo promedio en cola (Wq)")
    plt.title("Validación Modelo 1: Sistema de Colas M/M/c (Teórico vs Simulado)")
    plt.legend()
    plt.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig("validacion_modelo1_colas.png", dpi=150)

    # -------------------------------------------------------------- M/M/c/K
    # Mismos lambda y mu del juego (config.py), con las mejoras que puede comprar el jugador.
    print("\n--- PARTE B: M/M/c/K (capacidad finita, la que usa el juego) ---")
    configs_k = [
        {"nombre": "Config 4 (Nivel 1 inicial)",   "lam": 0.65, "mu": 0.35, "c": 1, "K": 4,  "semilla": 404},
        {"nombre": "Config 5 (Nivel 2, c=2, K=6)", "lam": 0.80, "mu": 0.35, "c": 2, "K": 6,  "semilla": 505},
        {"nombre": "Config 6 (Nivel 3, c=3, K=8)", "lam": 0.85, "mu": 0.35, "c": 3, "K": 8,  "semilla": 606},
    ]
    res_k = []
    for cfg in configs_k:
        teo = teoria_mmck(cfg["lam"], cfg["mu"], cfg["c"], cfg["K"])
        sim = simular_colas_mmck(cfg["lam"], cfg["mu"], cfg["c"], cfg["K"], 30000, cfg["semilla"])
        err = {k: abs(sim[k] - teo[k]) / teo[k] * 100 for k in ("PK", "W", "Wq", "L")}
        print(f"\n>>> {cfg['nombre']} | lambda={cfg['lam']}, mu={cfg['mu']}, c={cfg['c']}, K={cfg['K']} "
              f"(a/c={teo['rho']:.3f})")
        print(f"    Teórico  -> P(bloqueo) = {teo['PK']:.4f} | W = {teo['W']:.4f} | Wq = {teo['Wq']:.4f} | L = {teo['L']:.4f}")
        print(f"    Simulado -> P(bloqueo) = {sim['PK']:.4f} | W = {sim['W']:.4f} | Wq = {sim['Wq']:.4f} | L = {sim['L']:.4f}")
        print(f"    Error %  -> Err(PK) = {err['PK']:.2f}% | Err(W) = {err['W']:.2f}% | "
              f"Err(Wq) = {err['Wq']:.2f}% | Err(L) = {err['L']:.2f}%")
        res_k.append((cfg["nombre"].split("(")[0].strip(), teo["PK"], sim["PK"]))

    plt.figure(figsize=(8, 5))
    xk = range(len(res_k))
    plt.bar([i - 0.15 for i in xk], [r[1] for r in res_k], width=0.3, label="Teórico M/M/c/K", color="#00d4ff")
    plt.bar([i + 0.15 for i in xk], [r[2] for r in res_k], width=0.3, label="Simulado (PRNG Multiplicativo)", color="#ff2a85")
    plt.xticks(xk, [r[0] for r in res_k])
    plt.ylabel("Probabilidad de bloqueo P_K (brecha)")
    plt.title("Validación Modelo 1: M/M/c/K (Teórico vs Simulado)")
    plt.legend()
    plt.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig("validacion_modelo1_colas_mmck.png", dpi=150)
    plt.show()
