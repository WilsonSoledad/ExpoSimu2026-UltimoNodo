"""
Único punto donde el juego importa los módulos independientes del grupo
(carpeta ../modulos). Si un archivo cambia de nombre, solo se actualiza aquí.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.append(str(RAIZ))

from modulos import carrillo_modelo1_colas as modelo1                           # noqa: E402
from modulos import carrillo_modelo2_caminatas as modelo2                       # noqa: E402
from modulos import Paredes_Carrillo_Soledad_Suarez_modelo5_sir as modelo5      # noqa: E402
