"""
Adaptadores de los cinco modelos de simulación.

Cada modelo existe una sola vez, en ../modulos (punto 3.1). Estos archivos
importan su módulo a través de fuentes.py y agregan solo lo propio del juego
(unidades, paredes, métricas del modo ingeniero); la interfaz que usa el juego
está descrita en el docstring de cada uno:

    colas.py       Modelo 1  Colas M/M/c/K          ..._modelo1_colas.py
    caminata.py    Modelo 2  Caminata aleatoria     ..._modelo2_caminatas.py
    montecarlo.py  Modelo 3  Monte Carlo            ..._modelo3_montecarlo.py
    agentes.py     Modelo 4  Basado en agentes      ..._modelo4_agentes.py
    sir.py         Modelo 5  Dinámica de sistemas   ..._modelo5_sir.py
"""
from .colas import ModeloColas, simular_rapido, teoria_mmck
from .caminata import ModeloCaminata
from .montecarlo import ModeloMonteCarlo
from .agentes import ModeloAgentes
from .sir import ModeloSIR
