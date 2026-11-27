# Último Nodo · ExpoSimu 2026

Taller final de **Simulación por Computador** (UPTC, 2026). Tower defense en Python con Pygame
que integra cinco modelos de simulación: colas M/M/c/K, caminata aleatoria, Monte Carlo,
simulación basada en agentes y dinámica de sistemas (SIR).

> Año 2049. Un malware llamado La Plaga apaga las redes del país. Ada Rincón, operadora
> de sistemas, debe resistir las oleadas de ataques hasta que el respaldo del Núcleo llegue al 100 %.

**Autores:** Jaider Fabian Paredes Villamizar · Juan David Carrillo Parra ·
David Alejandro Suarez Cardenas · Wilson Javier Soledad Martinez
**Docente:** Alex Puertas González

## Requisitos

- Python 3.10 o superior (probado con 3.12 en Windows y 3.13 en Linux)
- Dependencias: `pygame`, `numpy` (2.0 o superior), `scipy`, `matplotlib`

## Instalación

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Ejecutar el juego

```
cd juego
python main.py
```

En el menú: flechas para elegir y Enter para confirmar.

### Controles

| Acción | Tecla / botón |
|---|---|
| Agregar servidor a una puerta (c + 1) | Clic izquierdo sobre la puerta |
| Ampliar capacidad (K + 2) | Clic derecho sobre la puerta |
| Mejorar servicio (μ + 0.10) | Shift + clic izquierdo sobre la puerta |
| Instalar escáner contra gusanos | E y clic en una celda libre |
| Predictor Monte Carlo | P |
| Parche (γ × 3 durante 10 s) | H |
| Segmentar la red (β × 0.75) | S |
| Modo ingeniero (observado vs. teórico) | F1 |
| Velocidad normal / doble | V |
| Pausa (R reinicia, M vuelve al menú) | ESC |

### Niveles

| Nivel | Oleadas | Modelos activos | Derrota |
|---|---|---|---|
| 1. Red del campus | 5 | Colas, caminata | Integridad en 0 |
| 2. Zona de infección | 8 | Colas, caminata, Monte Carlo, SIR | Integridad en 0 o infección > 60 % |
| 3. El Núcleo | 8 (Hidra en las oleadas 4 y 8) | Los cinco | Integridad en 0 o infección > 60 % |

Cada oleada tiene 6 s de preparación y 20 s de ataque. El nivel se gana al superar la última oleada.

## Módulos independientes (punto 3.1)

Cada modelo se ejecuta sin el juego, desde la carpeta `modulos/`:

```
cd modulos
python Paredes_Carrillo_Soledad_Suarez_modelo1_colas.py
python Paredes_Carrillo_Soledad_Suarez_modelo2_caminatas.py
python Paredes_Carrillo_Soledad_Suarez_modelo3_montecarlo.py
python Paredes_Carrillo_Soledad_Suarez_modelo4_agentes.py
python Paredes_Carrillo_Soledad_Suarez_modelo5_sir.py
```

| N.º | Modelo | PRNG del módulo | Salidas |
|---|---|---|---|
| 1 | Colas M/M/c y M/M/c/K | Congruencial multiplicativo (Park-Miller) | `validacion_modelo1_colas.png`, `validacion_modelo1_colas_mmck.png` |
| 2 | Caminata aleatoria sesgada 2D | Congruencial lineal (a = 1664525, c = 1013904223, m = 2^32) | `validacion_modelo2_caminatas.png` |
| 3 | Monte Carlo (Predictor y cadena de Markov) | Congruencial aditivo (k = 5, m = 2^31 − 1) | `validacion_modelo3_montecarlo.png` |
| 4 | Basado en agentes (enjambre) | MT19937 propio o LCG (`--prng lcg`) | carpeta `figs/` (`m4_*.png`, `m4_resultados.json`) |
| 5 | Dinámica de sistemas (SIR) | MT19937 propio o LCG (`--prng lcg`) | carpeta `figs/` (`m5_*.png`) |

Todos imprimen en consola la fecha, la hora, el usuario y la tabla de validación.
Los módulos 1 y 2 abren la gráfica al final; hay que cerrar la ventana para terminar.
Opciones de los módulos 4 y 5: `--quick` (corrida rápida), `--show` (mostrar gráficos),
`--config 1|2|3` (una sola configuración, para capturas), `--prng mt|lcg`, `--outdir carpeta`.

## Cómo usa el juego cada modelo

Cada modelo existe una sola vez, en `modulos/`. Los archivos de `juego/modelos/` son adaptadores
que importan los módulos a través de `juego/fuentes.py`; no copian su código.

| Modelo | Adaptador en el juego | Qué usa del módulo | Generador en el juego |
|---|---|---|---|
| Colas | `juego/modelos/colas.py` | `ModeloColas`, `teoria_mmck`, `simular_rapido` | Park-Miller (llegadas y servicio en flujos separados) |
| Caminata | `juego/modelos/caminata.py` | `paso_caminata` y generador congruencial lineal | Congruencial lineal |
| Monte Carlo | `juego/modelos/montecarlo.py` | `ModeloMonteCarlo` y matriz de transición | Congruencial lineal |
| Agentes | `juego/modelos/agentes.py` | `regla_rumbo`, `phi_global_theory` | Congruencial lineal |
| SIR | `juego/modelos/sir.py` | `sir_rhs`, `peak_theory` | Ninguno (modelo determinista, RK4) |

## Estructura del repositorio

```
modulos/            Punto 3.1: los cinco módulos independientes
juego/
  main.py           Punto de entrada y máquina de estados (menú, niveles, pausa, resultados)
  config.py         Parámetros de balance, oleadas, paleta y niveles
  aleatorio.py      Flujos de números pseudoaleatorios y transformaciones (exponencial, Bernoulli...)
  fuentes.py        Único punto de importación de los módulos
  modelos/          Adaptadores de los cinco modelos
  logica/           Niveles, entidades e interfaz gráfica
  recursos.py       Carga de sprites y audio (si falta un archivo, el juego sigue sin él)
  assets/
    sprites/        Paquete, gusano, bot, Hidra y fragmento (4 cuadros cada uno)
    audio/          Música, efectos y CREDITOS.md
docs/arte/          Sprites base y script que los adapta al juego (punto 3.2)
requirements.txt
```

## Sprites y audio (punto 3.2)

| Entidad | Sprite | Color de la paleta |
|---|---|---|
| Paquete malicioso | Araña | Magenta `#FF2E88` |
| Gusano de red | Serpiente | Rojo `#FF3B3B` |
| Bot del enjambre | Robot | Violeta `#9D4EDD` |
| Hidra y sus fragmentos | Dragón | Rojo y naranja `#FF8C42` |

Puertas, escáneres y el Núcleo se dibujan con figuras geométricas. Los sprites se generan
desde las imágenes base con `docs/arte/procesar_sprites.py` (separa los 4 cuadros, los limpia,
los reduce al tamaño de la grilla y los recolorea a la paleta):

```
python docs/arte/procesar_sprites.py docs/arte/base juego/assets/sprites docs/arte
```

**Música:** Music by Karl Casey @ White Bat Audio (*Free Cyberpunk Loop Pack*).
**Efectos:** Kenney (*Sci-Fi Sounds* e *Interface Sounds*, CC0).
Detalle archivo por archivo en `juego/assets/audio/CREDITOS.md`.

## Reproducibilidad

`SEMILLA = 2026` en `juego/config.py` hace que cada partida sea reproducible (cada nivel usa
`SEMILLA + índice del nivel`). Con `SEMILLA = None` se usa la hora del sistema.

## Video

Video de gameplay (5–8 min): https://drive.google.com/file/d/1flzZZBvMhpBC5Zeoez76gHOEDOJ8P-oH/view?usp=sharing
Los videos no se suben al repositorio porque GitHub rechaza archivos de más de 100 MB.

## Informe

El informe del taller documenta el diseño, la validación de cada modelo, la integración,
las pruebas y el uso de herramientas de inteligencia artificial.