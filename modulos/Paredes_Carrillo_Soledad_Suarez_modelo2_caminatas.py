import getpass
from datetime import datetime
import matplotlib.pyplot as plt

# ==============================================================================
# GENERADOR PRNG REUTILIZADO DEL TALLER 1 (generadores/congruencial_lineal.py)
# Referencia: Lehmer, D.H. (1951) / Hull-Dobell
# ==============================================================================
def congruencial_lineal(semilla, a, c, m, cantidad):
    xi_lista = []
    ri_lista = []
    x = semilla
    for _ in range(cantidad):
        x = (a * x + c) % m
        ri = x / m
        xi_lista.append(x)
        ri_lista.append(ri)
    return xi_lista, ri_lista

# ==============================================================================
# SIMULACIÓN DE CAMINATA ALEATORIA SESGADA EN 2D (Gusanos hacia el Núcleo)
# ==============================================================================
def simular_caminata_sesgada(n_pasos, p_der, q_izq, p_arr, p_aba, n_replicas=1000, semilla=98765):
    assert abs((p_der + q_izq + p_arr + p_aba) - 1.0) < 1e-9, "Las probabilidades deben sumar 1"
    
    # Parámetros Hull-Dobell (período máximo m = 2^32)
    a_lcg = 1664525
    c_lcg = 1013904223
    m_lcg = 2 ** 32

    total_numeros = n_pasos * n_replicas
    _, ri = congruencial_lineal(semilla, a_lcg, c_lcg, m_lcg, total_numeros)

    posiciones_finales_x = []
    posiciones_finales_y = []
    trayectorias_muestra = []

    idx = 0
    for rep in range(n_replicas):
        x, y = 0, 0
        ruta_x, ruta_y = [0], [0]

        for _ in range(n_pasos):
            r = ri[idx]
            idx += 1

            if r < p_der:
                x += 1          # Avanza hacia el Núcleo (+X)
            elif r < p_der + q_izq:
                x -= 1          # Retrocede (-X)
            elif r < p_der + q_izq + p_arr:
                y += 1          # Desvío nodo superior (+Y)
            else:
                y -= 1          # Desvío nodo inferior (-Y)

            if rep < 5:
                ruta_x.append(x)
                ruta_y.append(y)

        posiciones_finales_x.append(x)
        posiciones_finales_y.append(y)
        if rep < 5:
            trayectorias_muestra.append((ruta_x, ruta_y))

    media_x_sim = sum(posiciones_finales_x) / n_replicas
    media_y_sim = sum(posiciones_finales_y) / n_replicas

    # Valores teóricos: E[X_n] = n * (p - q) ; E[Y_n] = n * (p_arr - p_aba)
    media_x_teo = n_pasos * (p_der - q_izq)
    media_y_teo = n_pasos * (p_arr - p_aba)

    return {
        "E_X_teo": media_x_teo, "E_X_sim": media_x_sim,
        "E_Y_teo": media_y_teo, "E_Y_sim": media_y_sim,
        "trayectorias": trayectorias_muestra
    }

# ==============================================================================
# EJECUCIÓN DE VALIDACIÓN EXPERIMENTAL (3 CONFIGURACIONES)
# ==============================================================================
if __name__ == "__main__":
    print("=" * 78)
    print("MODELO 2: CAMINATA ALEATORIA SESGADA 2D (GUSANOS - JUEGO 'ÚLTIMO NODO')")
    print(f"Usuario SO : {getpass.getuser()} | Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("PRNG       : Congruencial Lineal Mixto (a=1664525, c=1013904223, m=2^32)")
    print("=" * 78)

    configs = [
        {"nombre": "Config 1 (Sesgo Bajo - Nivel 1)",  "n": 100, "p": 0.40, "q": 0.20, "arr": 0.20, "aba": 0.20, "sem": 111},
        {"nombre": "Config 2 (Sesgo Medio - Nivel 2)", "n": 150, "p": 0.50, "q": 0.15, "arr": 0.175,"aba": 0.175,"sem": 222},
        {"nombre": "Config 3 (Sesgo Alto - Nivel 3)",  "n": 200, "p": 0.60, "q": 0.10, "arr": 0.15, "aba": 0.15, "sem": 333},
    ]

    plt.figure(figsize=(9, 5))
    colores = ["#00d4ff", "#ffb703", "#ff2a85"]

    for idx_c, cfg in enumerate(configs):
        res = simular_caminata_sesgada(
            cfg["n"], cfg["p"], cfg["q"], cfg["arr"], cfg["aba"],
            n_replicas=1000, semilla=cfg["sem"]
        )
        err_x = abs(res["E_X_sim"] - res["E_X_teo"]) / abs(res["E_X_teo"]) * 100

        print(f"\n>>> {cfg['nombre']} | n={cfg['n']} pasos, p={cfg['p']}, q={cfg['q']}")
        print(f"    Teórico  -> E[X_n] = {res['E_X_teo']:.4f} | E[Y_n] = {res['E_Y_teo']:.4f}")
        print(f"    Simulado -> E[X_n] = {res['E_X_sim']:.4f} | E[Y_n] = {res['E_Y_sim']:.4f}")
        print(f"    Error %  -> Err(E[X_n]) = {err_x:.2f}%")

        # Graficar una trayectoria representativa de cada configuración
        rx, ry = res["trayectorias"][0]
        plt.plot(rx, ry, label=f"{cfg['nombre']} (E[X]={res['E_X_sim']:.1f})", color=colores[idx_c], linewidth=1.8)
        plt.scatter([rx[-1]], [ry[-1]], color=colores[idx_c], s=50, zorder=5)

    plt.axhline(0, color="gray", linestyle="--", linewidth=0.8)
    plt.axvline(0, color="gray", linestyle="--", linewidth=0.8)
    plt.xlabel("Avance hacia el Núcleo (Eje X)")
    plt.ylabel("Desviación lateral en la red (Eje Y)")
    plt.title("Validación Modelo 2: Trayectorias de Gusanos en Caminata Aleatoria Sesgada")
    plt.legend()
    plt.grid(True, linestyle=":", alpha=0.5)
    plt.tight_layout()
    plt.savefig("validacion_modelo2_caminatas.png", dpi=150)
    plt.show()
