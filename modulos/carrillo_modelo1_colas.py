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
    lq = (a * c * pw) / (math.factorial(c) * ((1 - rho) ** 2) * c) if c > 1 else (rho ** 2) / (1 - rho)
    # Simplificación estándar equivalente para Lq en M/M/c:
    lq = (pw * rho) / (1 - rho)
    wq = lq / lam
    w = wq + (1.0 / mu)
    l = lam * w
    return {"rho": rho, "P0": p0, "Pw": pw, "Lq": lq, "L": l, "Wq": wq, "W": w}

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
    historial_tiempo = []
    historial_cola = []
    cola_actual = 0

    for i in range(num_amenazas):
        # Generar próxima llegada
        reloj += exp_inversa(lam)
        
        # Liberar servidores que ya terminaron antes del reloj actual
        while servidores_libres_en[0] <= reloj and cola_actual > 0:
            # Este bloque mantiene coherencia de seguimiento de cola
            break

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

        # Guardar muestra de evolución (primeras 200 amenazas para graficar)
        if i < 200:
            en_cola = sum(1 for t in servidores_libres_en if t > reloj)
            historial_tiempo.append(reloj)
            historial_cola.append(max(0, en_cola - c))

    wq_sim = sum(tiempos_espera) / num_amenazas
    w_sim = sum(tiempos_sistema) / num_amenazas
    lq_sim = lam * wq_sim  # Ley de Little: Lq = lambda * Wq
    l_sim = lam * w_sim    # Ley de Little: L = lambda * W

    return {
        "Wq": wq_sim, "W": w_sim, "Lq": lq_sim, "L": l_sim,
        "hist_t": historial_tiempo, "hist_q": historial_cola
    }

# ==============================================================================
# EJECUCIÓN DE VALIDACIÓN EXPERIMENTAL (3 CONFIGURACIONES)
# ==============================================================================
if __name__ == "__main__":
    print("=" * 78)
    print("MODELO 1: SISTEMA DE COLAS M/M/c (FIREWALLS - JUEGO 'ÚLTIMO NODO')")
    print(f"Usuario SO : {getpass.getuser()} | Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("PRNG       : Congruencial Multiplicativo (Park-Miller: a=16807, m=2^31-1)")
    print("=" * 78)

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
    plt.show()
