"""
Último Nodo · ExpoSimu 2026 — Casos de prueba automatizados 7, 8 y 9 (sección 4.3).

Ejecuta los niveles del juego sin ventana, importando la lógica tal como está en
juego/ (no la modifica), y repite cada escenario con varias semillas.

    Caso 7: Predictor antes de la oleada 1 del nivel 2 (colas vacías), 30 semillas.
    Caso 8: Predictor antes de las oleadas 2, 3 y 4 del nivel 2 (colas ocupadas), 30 semillas.
    Caso 9: Infección sin parches ni segmentación (niveles 2 y 3), 8 semillas.

Condiciones comunes: el jugador no realiza acciones (no mejora puertas ni instala
escáneres) y la integridad del Núcleo no se agota, para que las oleadas sigan
hasta el final. Una "brecha de la oleada k" es, como en el Predictor, un paquete
que llegó durante la oleada k y fue rechazado en todas las puertas (incluye el
tiempo que tarda en recorrer el camino hasta la última puerta).

Uso (desde la raíz del repositorio):
    python pruebas/casos_automatizados.py
    python pruebas/casos_automatizados.py --caso 7       (solo un caso)
    python pruebas/casos_automatizados.py --detalle      (una fila por semilla)
"""
import argparse
import datetime
import getpass
import math
import platform
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "juego"))
sys.path.insert(0, str(RAIZ))

import config as C                       # noqa: E402
from aleatorio import crear_flujos       # noqa: E402
from logica.nivel import Nivel           # noqa: E402
from logica.entidades import Paquete     # noqa: E402

DT = 1 / C.FPS                           # mismo paso que el juego (60 FPS)
CICLO = C.OLEADA_PAUSA + C.OLEADA_DURACION
SEMILLA_BASE = C.SEMILLA if C.SEMILLA is not None else 2026
DETALLE = False                          # --detalle: imprime una fila por semilla


def fila(texto):
    if DETALLE:
        print(texto)


def inicio_oleada(k):
    """Instante (s) en que empieza el ataque de la oleada k (1, 2, ...)."""
    return (k - 1) * CICLO + C.OLEADA_PAUSA


def crear_nivel(indice, semilla):
    nivel = Nivel(indice, crear_flujos(semilla))
    nivel.brechas_ids = []                               # ids de los paquetes en brecha
    ultima = nivel.puertas[-1].modelo
    llegada_original = ultima.llegada

    def llegada_registrada(id_):                         # envoltura solo para medir
        admitida = llegada_original(id_)
        if not admitida:
            nivel.brechas_ids.append(id_)
        return admitida

    ultima.llegada = llegada_registrada
    return nivel


def avanzar_hasta(nivel, t_fin):
    while nivel.t < t_fin and nivel.estado == "jugando":
        nivel.integridad = 100.0                         # integridad sin límite
        nivel.actualizar(DT)


def hubo_brecha(nivel, id_desde, id_hasta):
    """¿Algún paquete con id en (id_desde, id_hasta] terminó en brecha?"""
    return any(id_desde < i <= id_hasta for i in nivel.brechas_ids)


def correr_con_predictor(indice, semilla, oleadas):
    """Consulta el Predictor 1 s antes de cada oleada indicada y luego deja correr
    el nivel hasta que los paquetes de la última oleada consultada terminan el camino.
    Devuelve una lista de (oleada, en_sistema, p_hat, hubo_brecha)."""
    nivel = crear_nivel(indice, semilla)
    registros = []
    for k in oleadas:
        avanzar_hasta(nivel, inicio_oleada(k) - 1.0)
        en_cola = sum(pu.modelo.en_sistema() for pu in nivel.puertas)
        p, _ = consultar_predictor(nivel)
        registros.append([k, en_cola, p, Paquete._siguiente_id])
    ultima = max(oleadas)
    avanzar_hasta(nivel, inicio_oleada(ultima) + C.OLEADA_DURACION)
    id_fin_ultima = Paquete._siguiente_id
    avanzar_hasta(nivel, inicio_oleada(ultima) + CICLO + 15.0)   # tiempo de recorrido
    salida = []
    for j, (k, en_cola, p, id_ini) in enumerate(registros):
        id_fin = registros[j + 1][3] if j + 1 < len(registros) else id_fin_ultima
        salida.append((k, en_cola, p, hubo_brecha(nivel, id_ini, id_fin)))
    return salida


def consultar_predictor(nivel):
    nivel.energia = max(nivel.energia, C.COSTOS["predictor"])
    nivel.usar_predictor()
    p, margen, n, _ = nivel.prediccion
    return p, margen


def ic95(exitos, n):
    p = exitos / n
    return p, 1.96 * math.sqrt(p * (1 - p) / n)


# ------------------------------------------------------------------ casos
def caso_7(n_semillas=30):
    print("\nCASO 7 · Predictor antes de la oleada 1 del nivel 2 (colas vacías)")
    fila(f"{'semilla':>8} {'P̂ (Predictor)':>15} {'¿brecha real?':>14}")
    estimaciones, brechas = [], 0
    for s in range(n_semillas):
        semilla = SEMILLA_BASE + s
        (_, _, p, b), = correr_con_predictor(1, semilla, (1,))
        estimaciones.append(p)
        brechas += b
        fila(f"{semilla:>8} {p:>15.3f} {'sí' if b else 'no':>14}")
    p_media = sum(estimaciones) / len(estimaciones)
    f, m = ic95(brechas, n_semillas)
    print(f"{n_semillas} semillas ({SEMILLA_BASE}–{SEMILLA_BASE + n_semillas - 1}) · P̂ media = {p_media:.3f} · frecuencia real = {f:.3f} "
          f"(IC 95 % de la frecuencia: {max(0, f - m):.3f} – {min(1, f + m):.3f})")
    estado = "Pass" if abs(p_media - f) <= m else "Fail"
    print(f"Resultado: {estado} (Pass si P̂ media cae dentro del IC 95 % de la frecuencia real)")


def caso_8(n_semillas=30, oleadas=(2, 3, 4)):
    print("\nCASO 8 · Predictor antes de las oleadas 2 a 4 del nivel 2 (colas ocupadas)")
    fila(f"{'semilla':>8} {'oleada':>7} {'en cola':>8} {'P̂ (Predictor)':>15} {'¿brecha real?':>14}")
    estimaciones, brechas, total = [], 0, 0
    for s in range(n_semillas):
        semilla = SEMILLA_BASE + s
        for k, en_cola, p, b in correr_con_predictor(1, semilla, oleadas):
            estimaciones.append(p)
            brechas += b
            total += 1
            fila(f"{semilla:>8} {k:>7} {en_cola:>8} {p:>15.3f} {'sí' if b else 'no':>14}")
    p_media = sum(estimaciones) / len(estimaciones)
    f, m = ic95(brechas, total)
    print(f"{n_semillas} semillas × {len(oleadas)} oleadas = {total} consultas · P̂ media = {p_media:.3f} · frecuencia real = {f:.3f} "
          f"(IC 95 %: {max(0, f - m):.3f} – {min(1, f + m):.3f})")
    estado = "Pass" if abs(p_media - f) <= m else "Fail"
    print(f"Resultado: {estado} (Pass si P̂ media cae dentro del IC 95 % de la frecuencia real)")


def caso_9(n_semillas=8):
    print("\nCASO 9 · Infección sin parches ni segmentación (niveles 2 y 3)")
    fila(f"{'nivel':>6} {'semilla':>8} {'pico de I':>10} {'infección máx.':>15} {'¿supera el umbral?':>19}")
    picos = []
    for indice in (1, 2):
        umbral = C.NIVELES[indice]["umbral_infeccion"]
        for s in range(n_semillas):
            semilla = SEMILLA_BASE + s
            nivel = crear_nivel(indice, semilla)
            avanzar_hasta(nivel, C.NIVELES[indice]["oleadas"] * CICLO)
            pico = nivel.sir.pico_I / nivel.sir.N
            picos.append(pico)
            fila(f"{indice + 1:>6} {semilla:>8} {nivel.sir.pico_I:>10.1f} {pico * 100:>14.1f} % "
                 f"{'sí' if pico > umbral else 'no':>19}")
    activada = any(p > C.NIVELES[1]["umbral_infeccion"] for p in picos)
    print(f"{n_semillas} semillas por nivel ({SEMILLA_BASE}–{SEMILLA_BASE + n_semillas - 1}) · infección máxima entre {min(picos) * 100:.1f} % y {max(picos) * 100:.1f} % "
          f"(umbral {C.NIVELES[1]['umbral_infeccion'] * 100:.0f} %)")
    print(f"Resultado: {'Pass' if activada else 'Fail'} "
          f"(Pass si la infección supera el umbral y causa la derrota)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--caso", type=int, choices=(7, 8, 9), help="ejecutar solo un caso")
    ap.add_argument("--detalle", action="store_true", help="imprimir una fila por semilla")
    args = ap.parse_args()
    global DETALLE
    DETALLE = args.detalle

    print("=" * 72)
    print("Último Nodo · Casos de prueba automatizados (sección 4.3)")
    print(f"Fecha y hora: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"Usuario: {getpass.getuser()} · Equipo: {platform.node()} · Python {platform.python_version()}")
    print(f"Semilla base: {SEMILLA_BASE} · paso de simulación: 1/{C.FPS} s")
    print("Sin acciones del jugador · integridad sin límite · juego sin modificar")
    print("=" * 72)
    casos = {7: caso_7, 8: caso_8, 9: caso_9}
    for numero in ([args.caso] if args.caso else (7, 8, 9)):
        casos[numero]()


if __name__ == "__main__":
    main()
