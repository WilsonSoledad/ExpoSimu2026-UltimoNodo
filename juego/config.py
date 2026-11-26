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

# ---------------------------------------------------------------- Sprites y audio
# Archivos en juego/assets (créditos en assets/audio/CREDITOS.md).
CUADROS_POR_SEGUNDO = 6         # velocidad de las animaciones de los sprites
VOLUMEN_MUSICA = 0.45
VOLUMEN_EFECTOS = 0.6
MUSICA_MENU = "casualty_loop2.ogg"

# ---------------------------------------------------------------- Economía
ENERGIA_MAX = 300
REGEN_ENERGIA = 2.0             # energía por segundo
RECOMPENSA_BASE = 4             # energía por amenaza eliminada (nivel 1)
COSTOS = {
    "servidor": 40,             # +1 servidor (c) en una puerta
    "capacidad": 25,            # +2 de capacidad (K) en una puerta
    "servicio": 30,             # +MU_PASO a la tasa de servicio (mu) de una puerta
    "escaner": 30,
    "predictor": 10,
    "parche": 25,
    "segmentar": 35,
}
MAX_SERVIDORES = 5
MAX_CAPACIDAD = 14
MU_PASO = 0.10                  # aumento de mu por mejora
MAX_MU = 0.75

# ---------------------------------------------------------------- Daño
DANO = {"paquete": 10, "gusano": 5, "bot": 10, "fragmento": 10, "hidra": 20}   # a la integridad
INFECCION = {"paquete": 4, "gusano": 2, "bot": 4, "fragmento": 4, "hidra": 8}  # nodos que infecta (SIR)

VEL_PAQUETE = 80        # px/s
PERIODO_GUSANO = 0.45   # segundos entre pasos de la caminata
PERIODO_ESCANER = 1.0   # segundos entre barridos
PROB_ESCANER = 0.6      # probabilidad de eliminar un gusano vecino

# Hidra (jefe del nivel 3): gusano de generación 2. Cada vez que un escáner
# la alcanza se divide en dos de la generación siguiente (2 -> 1 -> 0), es
# decir, una caminata aleatoria con ramificación. La generación 0 es un gusano común.
HIDRA_GENERACION = 2

# ---------------------------------------------------------------- Oleadas
# Cada oleada: OLEADA_PAUSA s de preparación (no entran amenazas nuevas y se
# puede usar el Predictor) seguidos de OLEADA_DURACION s de ataque. El respaldo
# del Núcleo llega al 100 % al terminar la última oleada (victoria).
OLEADA_PAUSA = 6.0
OLEADA_DURACION = 20.0  # igual al horizonte T del Predictor Monte Carlo

# ---------------------------------------------------------------- Niveles
# camino: celdas (columna, fila) por las que pasa la ruta, en orden.
# puertas: posición de cada firewall como fracción del largo del camino.
# modelos: cuáles de los cinco modelos están activos en el nivel.
NIVELES = [
    {
        "nombre": "Red del campus",
        "musica": "casualty_loop2.ogg",
        "descripcion": "Tutorial · 5 oleadas: firewalls (colas) y gusanos (caminatas).",
        "modelos": {"colas", "caminatas"},
        "oleadas": 5,
        "hidra": set(),             # oleadas en las que entra la Hidra
        "energia": 120,
        "camino": [(0, 7), (5, 7), (5, 3), (11, 3), (11, 11), (16, 11), (16, 7), (19, 7)],
        "puertas": [0.35, 0.72],
        "lam": 0.70, "mu": 0.35, "c": 1, "K": 4,
        "tasa_gusanos": 0.18,
        "p_caminata": (0.40, 0.20, 0.20, 0.20),   # der, izq, arr, aba
        "sir": None,
        "agentes": None,
    },
    {
        "nombre": "Zona de infección",
        "musica": "casualty_loop3.ogg",
        "descripcion": "8 oleadas · se activan el Predictor (Monte Carlo) y la infección (SIR).",
        "modelos": {"colas", "caminatas", "montecarlo", "sir"},
        "oleadas": 8,
        "hidra": set(),
        "energia": 150,
        "camino": [(0, 2), (8, 2), (8, 12), (13, 12), (13, 4), (19, 4)],
        "puertas": [0.30, 0.66],
        "lam": 0.80, "mu": 0.35, "c": 1, "K": 4,
        "tasa_gusanos": 0.18,
        "p_caminata": (0.40, 0.20, 0.20, 0.20),
        "sir": {"N": 100, "beta": 0.35, "gamma": 0.12, "I0": 0},
        "umbral_infeccion": 0.60,
        "agentes": None,
    },
    {
        "nombre": "El Núcleo",
        "musica": "casualty_loop1.ogg",
        "descripcion": "8 oleadas · los cinco modelos, enjambres de bots y la Hidra.",
        "modelos": {"colas", "caminatas", "montecarlo", "sir", "agentes"},
        "oleadas": 8,
        "hidra": {4, 8},
        "energia": 180,
        "camino": [(0, 12), (4, 12), (4, 2), (10, 2), (10, 10), (15, 10), (15, 5), (19, 5)],
        "puertas": [0.25, 0.55, 0.80],
        "lam": 0.85, "mu": 0.35, "c": 1, "K": 4,
        "tasa_gusanos": 0.18,
        "p_caminata": (0.40, 0.20, 0.20, 0.20),
        "sir": {"N": 100, "beta": 0.35, "gamma": 0.12, "I0": 0},
        "umbral_infeccion": 0.60,
        "agentes": {"retraso": 6, "tamano": 6},   # un enjambre por oleada, 6 s después de iniciar
    },
]
