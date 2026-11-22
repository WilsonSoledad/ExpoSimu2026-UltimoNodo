"""
Configuración global de Último Nodo.

Todos los parámetros de balance y de los modelos están aquí para poder
ajustarlos sin tocar la lógica del juego (útil para el punto 4.2,
"ajustes realizados").
"""

# ---------------------------------------------------------------- Pantalla
ANCHO, ALTO = 1100, 660
FPS = 60
CELDA = 40
COLS, FILAS = 20, 15            # campo de 800 x 600 px
HUD_ALTO = 60
CAMPO_X, CAMPO_Y = 0, HUD_ALTO
PANEL_X = COLS * CELDA          # el panel derecho empieza en x = 800
PANEL_ANCHO = ANCHO - PANEL_X

# Semilla base de los generadores. Con un valor fijo el juego es
# reproducible (útil para validar). Con None se usa la hora del sistema.
SEMILLA = 2026

# ---------------------------------------------------------------- Paleta
# Estética cyber/neón. La tabla con los códigos va en el punto 3.2.
PALETA = {
    "fondo":      "#0B1020",   # fondo general
    "grilla":     "#16213A",   # líneas de la grilla
    "camino":     "#1F3B57",   # ruta de los paquetes
    "panel":      "#101830",   # panel lateral y HUD
    "cian":       "#00E5FF",   # firewalls, Núcleo, interfaz
    "magenta":    "#FF2E88",   # paquetes maliciosos (La Plaga)
    "verde":      "#39FF14",   # escáneres, nodos sanos
    "amarillo":   "#FFD23F",   # energía, alertas
    "naranja":    "#FF8C42",   # brechas
    "rojo":       "#FF3B3B",   # gusanos, nodos infectados
    "violeta":    "#9D4EDD",   # bots del enjambre (agentes)
    "texto":      "#E6F1FF",   # texto principal
    "texto2":     "#6B7A99",   # texto secundario
}

# ---------------------------------------------------------------- Economía
ENERGIA_MAX = 300
REGEN_ENERGIA = 2.0             # energía por segundo
RECOMPENSA_BASE = 4             # energía por amenaza eliminada (nivel 1)
COSTOS = {
    "servidor": 40,             # +1 servidor (c) en una puerta
    "capacidad": 25,            # +2 de capacidad (K) en una puerta
    "escaner": 30,
    "predictor": 10,
    "parche": 25,
    "segmentar": 35,
}
MAX_SERVIDORES = 5
MAX_CAPACIDAD = 14

# ---------------------------------------------------------------- Daño
DANO = {"paquete": 10, "gusano": 5, "bot": 10}        # a la integridad
INFECCION = {"paquete": 4, "gusano": 2, "bot": 4}   # nodos que infecta (SIR)

VEL_PAQUETE = 80        # px/s
PERIODO_GUSANO = 0.45   # segundos entre pasos de la caminata
PERIODO_ESCANER = 1.0   # segundos entre barridos
PROB_ESCANER = 0.6      # probabilidad de eliminar un gusano vecino

# ---------------------------------------------------------------- Niveles
# camino: celdas (columna, fila) por las que pasa la ruta, en orden.
# puertas: posición de cada firewall como fracción del largo del camino.
# modelos: cuáles de los cinco modelos están activos en el nivel.
NIVELES = [
    {
        "nombre": "Red del campus",
        "descripcion": "Nivel tutorial: firewalls (colas) y gusanos (caminatas).",
        "modelos": {"colas", "caminatas"},
        "duracion": 75,             # segundos para completar el respaldo
        "energia": 120,
        "camino": [(0, 7), (5, 7), (5, 3), (11, 3), (11, 11), (16, 11), (16, 7), (19, 7)],
        "puertas": [0.35, 0.72],
        "lam": 0.65, "mu": 0.35, "c": 1, "K": 4,
        "tasa_gusanos": 0.15,
        "p_caminata": (0.40, 0.20, 0.20, 0.20),   # der, izq, arr, aba
        "sir": None,
        "agentes": None,
    },
    {
        "nombre": "Zona de infección",
        "descripcion": "Se activan el Predictor (Monte Carlo) y la infección de la red (SIR).",
        "modelos": {"colas", "caminatas", "montecarlo", "sir"},
        "duracion": 90,
        "energia": 150,
        "camino": [(0, 2), (8, 2), (8, 12), (13, 12), (13, 4), (19, 4)],
        "puertas": [0.30, 0.66],
        "lam": 0.80, "mu": 0.35, "c": 1, "K": 4,
        "tasa_gusanos": 0.18,
        "p_caminata": (0.40, 0.20, 0.20, 0.20),
        "sir": {"N": 100, "beta": 0.35, "gamma": 0.12, "I0": 0},
        "umbral_infeccion": 0.50,
        "agentes": None,
    },
    {
        "nombre": "El Núcleo",
        "descripcion": "Los cinco modelos activos y el enjambre de bots.",
        "modelos": {"colas", "caminatas", "montecarlo", "sir", "agentes"},
        "duracion": 110,
        "energia": 180,
        "camino": [(0, 12), (4, 12), (4, 2), (10, 2), (10, 10), (15, 10), (15, 5), (19, 5)],
        "puertas": [0.25, 0.55, 0.80],
        "lam": 0.85, "mu": 0.35, "c": 1, "K": 4,
        "tasa_gusanos": 0.18,
        "p_caminata": (0.40, 0.20, 0.20, 0.20),
        "sir": {"N": 100, "beta": 0.35, "gamma": 0.12, "I0": 0},
        "umbral_infeccion": 0.50,
        "agentes": {"periodo": 18, "tamano": 6},
    },
]
