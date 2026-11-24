"""
Modelo 1 - Sistema de colas M/M/c/K para los firewalls (PROVISIONAL).

Lo reemplaza el módulo del integrante 1. Para que la integración sea
directa, el módulo definitivo debería ofrecer esta misma interfaz:

    ModeloColas(gen_llegadas, gen_servicio, lam, mu, c, K)
    .interllegada() -> float          tiempo hasta la próxima llegada, Exp(lambda)
    .llegada(id) -> bool              False = sistema lleno (bloqueo -> brecha)
    .paso(dt) -> list[id]             entidades que terminaron su servicio
    .posicion(id) -> ("servicio"|"cola", indice) o None
    .agregar_servidor() / .ampliar_capacidad(n)
    .teoria(lam) -> dict              fórmulas M/M/c/K
    .metricas() -> list[(nombre, observado, teorico)]

Cada entidad atendida queda en self.registro con AT, WT, ST y ET
(ET = AT + WT + ST), igual que la tabla vista en clase.
"""
import math

from aleatorio import exponencial


class ModeloColas:
    nombre = "Colas M/M/c/K"

    def __init__(self, gen_llegadas, gen_servicio, lam, mu, c, K, llegadas_poisson=True):
        self.gen_ll = gen_llegadas
        # False en las puertas 2 y 3: les llegan desbordes y bots, no un Poisson(lambda)
        self.llegadas_poisson = llegadas_poisson
        self.gen_sv = gen_servicio
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


def teoria_mmck(lam, mu, c, K):
    """Medidas de desempeño en estado estacionario del modelo M/M/c/K."""
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


def simular_rapido(gen_ll, gen_sv, lam, mu, c, K, n, llegadas=None):
    """Simulación de eventos discretos de una puerta, sin gráficos.

    Si se pasan 'llegadas' (tiempos absolutos), se usan esas en vez de
    generar llegadas de Poisson. Devuelve (tiempos de las bloqueadas, n).
    Se usa en el Predictor Monte Carlo.
    """
    if llegadas is None:
        llegadas, t = [], 0.0
        for _ in range(n):
            t += exponencial(gen_ll, lam)
            llegadas.append(t)
    libres = [0.0] * c          # instante en que se libera cada servidor
    salidas = []                # instantes de salida de las entidades en el sistema
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
