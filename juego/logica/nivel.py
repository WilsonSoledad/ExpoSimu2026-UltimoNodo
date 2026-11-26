"""Lógica de un nivel: une los cinco modelos con las entidades del juego."""
import config as C
from aleatorio import exponencial, entero, bernoulli
from modelos import (ModeloColas, ModeloCaminata, ModeloMonteCarlo, ModeloAgentes,
                     ModeloSIR, simular_rapido)
from .entidades import Camino, Paquete, Gusano, Escaner, Puerta, celda_de


class Nivel:
    def __init__(self, indice, flujos):
        cfg = C.NIVELES[indice]
        self.indice = indice
        self.cfg = cfg
        self.flujos = flujos
        self.activos = set(cfg["modelos"])
        self.camino = Camino(cfg["camino"])

        # Modelo 1: una cola por puerta
        self.puertas = [
            Puerta(i, self.camino, f,
                   ModeloColas(flujos["llegadas"], flujos["servicio"],
                               cfg["lam"], cfg["mu"], cfg["c"], cfg["K"],
                               llegadas_poisson=(i == 0)))
            for i, f in enumerate(cfg["puertas"])
        ]
        # Modelo 2
        self.caminata = ModeloCaminata(flujos["caminata"], *cfg["p_caminata"])
        # Modelo 3
        self.mc = ModeloMonteCarlo(flujos["montecarlo"]) if "montecarlo" in self.activos else None
        # Modelo 4
        self.agentes = ModeloAgentes(flujos["agentes"]) if "agentes" in self.activos else None
        # Modelo 5
        self.sir = ModeloSIR(**cfg["sir"]) if "sir" in self.activos else None

        self.paquetes = {}
        self.gusanos = []
        self.escaneres = []
        self.energia = cfg["energia"]
        self.integridad = 100.0
        self.respaldo = 0.0
        self.t = 0.0
        self.parches = 0                 # parches gratis obtenidos como recompensa
        self.modo_escaner = False
        self.mensajes = []               # (texto, color, segundos restantes)
        self.prediccion = None           # (p, margen, n, segundos restantes)
        self.estado = "jugando"          # jugando | ganado | perdido
        self.motivo = ""
        self.eliminados = 0
        self.brechas = 0
        # Eventos del último fotograma ("brecha", "mejora", ...). main.py los
        # convierte en efectos de sonido; la lógica no depende del audio.
        self.eventos = []

        # Oleadas: preparación (OLEADA_PAUSA s) + ataque (OLEADA_DURACION s)
        self.n_oleadas = cfg["oleadas"]
        self.ciclo = C.OLEADA_PAUSA + C.OLEADA_DURACION
        self.oleada = 1                  # oleada actual o próxima (1..n)
        self.en_oleada = False           # False = preparación
        self.t_fase = 0.0                # segundos transcurridos en la fase actual
        self.enjambre_lanzado = False
        self.hidras = 0                  # Hidras que han entrado al campo

        self.t_sig_paquete = self.puertas[0].modelo.interllegada()
        self.t_sig_gusano = exponencial(flujos["general"], cfg["tasa_gusanos"])
        self.t_paso_gusano = 0.0

    # ================================================================ update
    def actualizar(self, dt):
        if self.estado != "jugando":
            return
        self.t += dt
        self.energia = min(C.ENERGIA_MAX, self.energia + C.REGEN_ENERGIA * dt)
        self.respaldo = min(100.0, 100.0 * self.t / (self.n_oleadas * self.ciclo))
        self._actualizar_oleada()

        self._actualizar_paquetes(dt)
        self._actualizar_gusanos(dt)
        self._actualizar_escaneres(dt)
        if self.agentes:
            self._actualizar_agentes(dt)
        if self.sir:
            self.sir.paso(dt)

        self.mensajes = [(t, c, s - dt) for t, c, s in self.mensajes if s - dt > 0]
        if self.prediccion:
            p, m, n, s = self.prediccion
            self.prediccion = (p, m, n, s - dt) if s - dt > 0 else None

        self._revisar_fin()

    def _actualizar_oleada(self):
        """Fase actual según el reloj: preparación -> oleada -> preparación ..."""
        k = int(self.t // self.ciclo)                      # oleadas ya terminadas
        if k >= self.n_oleadas:
            self.en_oleada = False
            return
        fase = self.t - k * self.ciclo
        en_oleada = fase >= C.OLEADA_PAUSA
        self.t_fase = fase - C.OLEADA_PAUSA if en_oleada else fase
        if en_oleada and not self.en_oleada:                 # empieza la oleada k+1
            self.enjambre_lanzado = False
            self.eventos.append("oleada")
            self.avisar(f"¡Oleada {k + 1} de {self.n_oleadas}!", C.PALETA["magenta"], 3)
            if (k + 1) in self.cfg["hidra"]:
                self._lanzar_hidra()
        elif not en_oleada and self.en_oleada:               # termina una oleada
            self.avisar(f"Oleada {k} superada"
                        + (" · P para predecir la siguiente" if self.mc else ""), C.PALETA["verde"], 4)
        self.oleada = k + 1
        self.en_oleada = en_oleada

    def _lanzar_hidra(self):
        fila = entero(self.flujos["general"], 3, C.FILAS - 4)
        self.gusanos.append(Gusano(0, fila, generacion=C.HIDRA_GENERACION))
        self.hidras += 1
        self.avisar("¡La Hidra entró a la red! Se divide al ser escaneada", C.PALETA["rojo"], 4)

    def _actualizar_paquetes(self, dt):
        # Llegadas de Poisson al inicio del camino, solo durante las oleadas
        if self.en_oleada:
            self.t_sig_paquete -= dt
        while self.t_sig_paquete <= 0:
            p = Paquete()
            self.paquetes[p.id] = p
            self.t_sig_paquete += self.puertas[0].modelo.interllegada()

        for p in list(self.paquetes.values()):
            if p.estado != "moviendo":
                continue
            p.avanzar(dt)
            if p.sig_puerta < len(self.puertas) and p.s >= self.puertas[p.sig_puerta].s:
                self._llegar_a_puerta(p, p.sig_puerta)
            elif p.s >= self.camino.largo:
                self._impacto(p.tipo)
                del self.paquetes[p.id]

        for puerta in self.puertas:
            for id_ in puerta.modelo.paso(dt):
                if id_ in self.paquetes:
                    del self.paquetes[id_]
                    self._recompensa()

    def _llegar_a_puerta(self, p, indice):
        puerta = self.puertas[indice]
        p.s = puerta.s
        if puerta.modelo.llegada(p.id):
            p.estado = "puerta"
            p.puerta = indice
        else:
            p.brecha = True
            p.sig_puerta = indice + 1
            p.s += 1.0

    def _actualizar_gusanos(self, dt):
        if self.en_oleada:
            self.t_sig_gusano -= dt
        while self.t_sig_gusano <= 0:
            self.gusanos.append(Gusano(0, entero(self.flujos["general"], 0, C.FILAS - 1)))
            self.t_sig_gusano += exponencial(self.flujos["general"], self.cfg["tasa_gusanos"])

        self.t_paso_gusano += dt
        while self.t_paso_gusano >= C.PERIODO_GUSANO:
            self.t_paso_gusano -= C.PERIODO_GUSANO
            for g in list(self.gusanos):
                dx, dy = self.caminata.paso()
                g.rastro = (g.rastro + [(g.col, g.fila)])[-3:]
                g.col = max(0, g.col + dx)               # pared izquierda
                g.fila = min(C.FILAS - 1, max(0, g.fila + dy))
                g.pasos += 1
                if g.col >= C.COLS - 1:
                    self.caminata.registrar_cruce(g.pasos)
                    self.gusanos.remove(g)
                    self._impacto(g.tipo)

    def _actualizar_escaneres(self, dt):
        for e in self.escaneres:
            e.destello = max(0.0, e.destello - dt)
            e.reloj += dt
            if e.reloj < C.PERIODO_ESCANER:
                continue
            e.reloj = 0.0
            for g in list(self.gusanos):
                if max(abs(g.col - e.col), abs(g.fila - e.fila)) <= 1:
                    if bernoulli(self.flujos["general"], C.PROB_ESCANER):
                        self.gusanos.remove(g)
                        e.destello = 0.3
                        self.eventos.append("gusano_eliminado")
                        self._recompensa()
                        if g.generacion > 0:
                            self.eventos.append("hidra_division")
                            self._dividir(g)

    def _dividir(self, g):
        """La Hidra (o un fragmento) se divide en dos de la generación siguiente."""
        for df in (-1, 1):
            fila = min(C.FILAS - 1, max(0, g.fila + df))
            self.gusanos.append(Gusano(g.col, fila, generacion=g.generacion - 1, pasos=g.pasos))

    def _actualizar_agentes(self, dt):
        cfg_ag = self.cfg["agentes"]
        if self.en_oleada and not self.enjambre_lanzado and self.t_fase >= cfg_ag["retraso"]:
            self.enjambre_lanzado = True
            fila = entero(self.flujos["agentes"], 2, C.FILAS - 3)
            self.agentes.generar_enjambre(cfg_ag["tamano"], C.CAMPO_X + 10,
                                          C.CAMPO_Y + fila * C.CELDA)
            self.avisar("Se aproxima un enjambre de bots", C.PALETA["violeta"])
        objetivos = [(pu.x, pu.y, pu.debilidad()) for pu in self.puertas]
        for _bot, indice in self.agentes.paso(dt, objetivos):
            p = Paquete(s=self.puertas[indice].s, sig_puerta=indice, tipo="bot")
            self.paquetes[p.id] = p
            self._llegar_a_puerta(p, indice)

    def _impacto(self, tipo):
        self.integridad = max(0.0, self.integridad - C.DANO[tipo])
        self.brechas += 1
        self.eventos.append("brecha")
        if self.sir:
            self.sir.infectar(C.INFECCION[tipo])

    def _recompensa(self):
        self.eliminados += 1
        if not self.mc:
            self.energia = min(C.ENERGIA_MAX, self.energia + C.RECOMPENSA_BASE)
            return
        if self.mc.siguiente_recompensa() == "energia":
            self.energia = min(C.ENERGIA_MAX, self.energia + C.RECOMPENSA_BASE + 2)
        else:
            self.parches += 1

    def _revisar_fin(self):
        if self.integridad <= 0:
            self.estado, self.motivo = "perdido", "La integridad del Núcleo llegó a 0."
        elif self.sir and self.sir.fraccion_infectada() > self.cfg["umbral_infeccion"]:
            umbral = int(self.cfg["umbral_infeccion"] * 100)
            self.estado, self.motivo = "perdido", f"Más del {umbral} % de la red quedó infectada."
        elif self.t >= self.n_oleadas * self.ciclo:
            self.respaldo = 100.0
            self.estado = "ganado"

    # ================================================================ acciones
    def avisar(self, texto, color=None, segundos=2.5):
        self.mensajes.append((texto, color or C.PALETA["texto"], segundos))
        self.mensajes = self.mensajes[-4:]

    def gastar(self, costo):
        if self.energia < costo:
            self.avisar("Energía insuficiente", C.PALETA["naranja"])
            self.eventos.append("energia_insuficiente")
            return False
        self.energia -= costo
        return True

    def clic(self, x, y, boton, shift=False):
        for pu in self.puertas:
            if pu.contiene(x, y):
                m = pu.modelo
                if boton == 1 and shift:
                    if m.mu >= C.MAX_MU - 1e-9:
                        self.avisar("Tasa de servicio máxima en esta puerta")
                    elif self.gastar(C.COSTOS["servicio"]):
                        m.mejorar_servicio(C.MU_PASO)
                        self.eventos.append("mejora")
                        self.avisar(f"Puerta {pu.indice + 1}: μ = {m.mu:.2f}", C.PALETA["cian"])
                elif boton == 1:
                    if m.c >= C.MAX_SERVIDORES:
                        self.avisar("Máximo de servidores en esta puerta")
                    elif self.gastar(C.COSTOS["servidor"]):
                        m.agregar_servidor()
                        self.eventos.append("mejora")
                        self.avisar(f"Puerta {pu.indice + 1}: c = {m.c}", C.PALETA["cian"])
                elif boton == 3:
                    if m.K >= C.MAX_CAPACIDAD:
                        self.avisar("Capacidad máxima en esta puerta")
                    elif self.gastar(C.COSTOS["capacidad"]):
                        m.ampliar_capacidad(2)
                        self.eventos.append("mejora")
                        self.avisar(f"Puerta {pu.indice + 1}: K = {m.K}", C.PALETA["cian"])
                return
        if self.modo_escaner and boton == 1:
            col, fila = celda_de(x, y)
            if not (0 <= col < C.COLS and 0 <= fila < C.FILAS):
                return
            ocupada = (col, fila) in self.camino.celdas or any(
                e.col == col and e.fila == fila for e in self.escaneres)
            if ocupada:
                self.avisar("No se puede instalar ahí", C.PALETA["naranja"])
            elif self.gastar(C.COSTOS["escaner"]):
                self.escaneres.append(Escaner(col, fila))
                self.eventos.append("mejora")

    def alternar_escaner(self):
        self.modo_escaner = not self.modo_escaner

    def usar_predictor(self, n=400, horizonte=C.OLEADA_DURACION):
        if not self.mc:
            self.avisar("El Predictor se desbloquea en el nivel 2")
            return
        if not self.gastar(C.COSTOS["predictor"]):
            return
        lam = self.cfg["lam"]
        llegadas_esperadas = max(1, int(lam * horizonte))
        params = [(pu.modelo.mu, pu.modelo.c, pu.modelo.K) for pu in self.puertas]

        def experimento(gen):
            bloqueadas, _ = simular_rapido(gen, gen, lam, *params[0], llegadas_esperadas)
            for mu, c, K in params[1:]:
                if not bloqueadas:
                    break
                bloqueadas, _ = simular_rapido(gen, gen, lam, mu, c, K, 0, llegadas=bloqueadas)
            return len(bloqueadas) > 0

        p, margen = self.mc.estimar_probabilidad(experimento, n)
        self.mc.ultima = ("P(brecha en 20 s)", p, margen, n, float("nan"))
        self.prediccion = (p, margen, n, 8.0)
        self.eventos.append("predictor")

    def usar_parche(self):
        if not self.sir:
            self.avisar("Los parches se usan desde el nivel 2")
            return
        if self.parches > 0:
            self.parches -= 1
        elif not self.gastar(C.COSTOS["parche"]):
            return
        self.sir.aplicar_parche(duracion=10.0, factor=3.0)
        self.eventos.append("parche")
        self.avisar("Parche aplicado: γ × 3 durante 10 s", C.PALETA["verde"])

    def segmentar(self):
        if not self.sir:
            self.avisar("La segmentación se usa desde el nivel 2")
            return
        if self.gastar(C.COSTOS["segmentar"]):
            self.sir.segmentar(0.75)
            self.eventos.append("segmentar")
            self.avisar(f"Red segmentada: β = {self.sir.beta:.3f}", C.PALETA["verde"])

    # ================================================================ métricas
    def metricas_ingeniero(self):
        """Bloques (título, filas) para el modo ingeniero."""
        bloques = []
        for pu in self.puertas:
            m = pu.modelo
            bloques.append((f"Colas · Puerta {pu.indice + 1} (c={m.c}, K={m.K}, μ={m.mu}) · "
                            f"ventana {m.t_estad:.0f} s", m.metricas()))
        bloques.append(("Caminata aleatoria", self.caminata.metricas(C.COLS - 1)[:3]))
        if self.mc:
            bloques.append(("Monte Carlo (recompensas Markov y Predictor)", self.mc.metricas()))
        if self.agentes:
            bloques.append(("Basado en agentes", self.agentes.metricas()))
        if self.sir:
            bloques.append(("Dinámica de sistemas (SIR)", self.sir.metricas()))
        return bloques
