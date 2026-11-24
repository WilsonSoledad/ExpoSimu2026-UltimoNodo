"""
Los cinco modelos de simulación. Cada archivo es PROVISIONAL y lo
reemplaza el integrante responsable, conservando la interfaz descrita en
su docstring:

    colas.py       Modelo 1  Colas M/M/c/K          (integrante 1)
    caminata.py    Modelo 2  Caminata aleatoria     (integrante 1)
    montecarlo.py  Modelo 3  Monte Carlo            (integrante 3)
    agentes.py     Modelo 4  Basado en agentes      (integrante 2)
    sir.py         Modelo 5  Dinámica de sistemas   (integrante 2)
"""
from .colas import ModeloColas, simular_rapido, teoria_mmck
from .caminata import ModeloCaminata
from .montecarlo import ModeloMonteCarlo
from .agentes import ModeloAgentes
from .sir import ModeloSIR
