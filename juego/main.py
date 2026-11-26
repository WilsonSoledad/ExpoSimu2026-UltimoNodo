"""
Último Nodo - ExpoSimu 2026 - Simulación por computador (UPTC)

Ejecutar desde la carpeta juego/:  python main.py

Máquina de estados:
    menu -> controles
    menu -> jugando <-> pausa
    jugando -> nivel_superado -> jugando (siguiente nivel)
    jugando -> game_over -> jugando (reintentar) | menu
    jugando -> victoria -> menu
"""
import sys
from pathlib import Path

# Raíz del repositorio en la ruta de importación, para que los adaptadores
# de modelos/ puedan importar los módulos independientes de ../modulos
# (lo hace fuentes.py: from modulos import Paredes_Carrillo_Soledad_Suarez_modelo1_colas).
RAIZ = Path(__file__).resolve().parent.parent
sys.path.append(str(RAIZ))

import pygame

import config as C
from aleatorio import crear_flujos
from logica.nivel import Nivel
from logica import ui


class Juego:
    OPCIONES = ["Jugar", "Controles", "Salir"]

    def __init__(self):
        self.fuentes = ui.Fuentes()
        self.estado = "menu"
        self.seleccion = 0
        self.nivel = None
        self.indice = 0
        self.ingeniero = False
        self.velocidad = 1
        self.t_menu = 0.0
        self.salir = False

    # ------------------------------------------------------------ niveles
    def cargar_nivel(self, indice):
        self.indice = indice
        semilla = None if C.SEMILLA is None else C.SEMILLA + indice
        self.nivel = Nivel(indice, crear_flujos(semilla))
        self.estado = "jugando"

    # ------------------------------------------------------------ eventos
    def manejar_evento(self, ev):
        if ev.type == pygame.QUIT:
            self.salir = True
            return
        if ev.type == pygame.KEYDOWN:
            getattr(self, f"_tecla_{self.estado}")(ev.key)
        elif ev.type == pygame.MOUSEBUTTONDOWN and self.estado == "jugando":
            shift = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)
            self.nivel.clic(ev.pos[0], ev.pos[1], ev.button, shift)

    def _tecla_menu(self, k):
        if k in (pygame.K_UP, pygame.K_w):
            self.seleccion = (self.seleccion - 1) % len(self.OPCIONES)
        elif k in (pygame.K_DOWN, pygame.K_s):
            self.seleccion = (self.seleccion + 1) % len(self.OPCIONES)
        elif k in (pygame.K_RETURN, pygame.K_SPACE):
            opcion = self.OPCIONES[self.seleccion]
            if opcion == "Jugar":
                self.cargar_nivel(0)
            elif opcion == "Controles":
                self.estado = "controles"
            else:
                self.salir = True

    def _tecla_controles(self, k):
        if k in (pygame.K_RETURN, pygame.K_ESCAPE):
            self.estado = "menu"

    def _tecla_jugando(self, k):
        n = self.nivel
        if k == pygame.K_ESCAPE:
            self.estado = "pausa"
        elif k == pygame.K_F1:
            self.ingeniero = not self.ingeniero
        elif k == pygame.K_v:
            self.velocidad = 2 if self.velocidad == 1 else 1
            n.avisar(f"Velocidad x{self.velocidad}")
        elif k == pygame.K_e:
            n.alternar_escaner()
        elif k == pygame.K_p:
            n.usar_predictor()
        elif k == pygame.K_h:
            n.usar_parche()
        elif k == pygame.K_s:
            n.segmentar()

    def _tecla_pausa(self, k):
        if k == pygame.K_ESCAPE:
            self.estado = "jugando"
        elif k == pygame.K_r:
            self.cargar_nivel(self.indice)
        elif k == pygame.K_m:
            self.estado = "menu"

    def _tecla_nivel_superado(self, k):
        if k == pygame.K_RETURN:
            self.cargar_nivel(self.indice + 1)

    def _tecla_game_over(self, k):
        if k == pygame.K_RETURN:
            self.cargar_nivel(self.indice)
        elif k == pygame.K_m:
            self.estado = "menu"

    def _tecla_victoria(self, k):
        if k == pygame.K_RETURN:
            self.estado = "menu"

    # ------------------------------------------------------------ ciclo
    def actualizar(self, dt):
        self.t_menu += dt
        if self.estado != "jugando":
            return
        self.nivel.actualizar(dt * self.velocidad)
        if self.nivel.estado == "perdido":
            self.estado = "game_over"
        elif self.nivel.estado == "ganado":
            ultimo = self.indice == len(C.NIVELES) - 1
            self.estado = "victoria" if ultimo else "nivel_superado"

    def dibujar(self, sup):
        f = self.fuentes
        if self.estado == "menu":
            ui.pantalla_menu(sup, f, self.OPCIONES, self.seleccion, self.t_menu)
        elif self.estado == "controles":
            ui.pantalla_controles(sup, f)
        else:
            ui.dibujar_nivel(sup, self.nivel, f, self.ingeniero and self.estado == "jugando")
            n = self.nivel
            superadas = n.n_oleadas if n.estado == "ganado" else n.oleada - 1
            resumen = [f"Oleadas superadas: {superadas} de {n.n_oleadas}",
                       f"Amenazas eliminadas: {n.eliminados}", f"Brechas: {n.brechas}",
                       f"Tiempo: {n.t:.0f} s"]
            if self.estado == "pausa":
                ui.pantalla_pausa(sup, f)
            elif self.estado == "nivel_superado":
                ui.pantalla_resultado(sup, f, "RESPALDO PARCIAL", ui.COL["verde"], resumen,
                                      "Enter: siguiente nivel")
            elif self.estado == "game_over":
                ui.pantalla_resultado(sup, f, "NÚCLEO PERDIDO", ui.COL["naranja"],
                                      [n.motivo] + resumen, "Enter: reintentar · M: menú")
            elif self.estado == "victoria":
                ui.pantalla_resultado(sup, f, "RESPALDO COMPLETO", ui.COL["cian"],
                                      ["El archivo de la universidad está a salvo."] + resumen,
                                      "Enter: volver al menú")


def main():
    pygame.init()
    pantalla = pygame.display.set_mode((C.ANCHO, C.ALTO))
    pygame.display.set_caption("Último Nodo · ExpoSimu 2026")
    reloj = pygame.time.Clock()
    juego = Juego()
    while not juego.salir:
        dt = min(reloj.tick(C.FPS) / 1000.0, 0.05)
        for ev in pygame.event.get():
            juego.manejar_evento(ev)
        juego.actualizar(dt)
        juego.dibujar(pantalla)
        pygame.display.flip()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
