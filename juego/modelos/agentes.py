"""
Modelo 4 - Simulación basada en agentes: enjambre de bots (PROVISIONAL).

Lo reemplaza el módulo del integrante 2. Sigue la estructura formal vista
en clase:

    AM_a = (RU_a, percibe_a, M_a, mentalUpdate_a, ACT_a, act_a)

    RU_a          universo relevante: vecinos dentro del radio de percepción
                  y las puertas de la red (el bot "escanea" la red)
    percibe_a     transforma RU_a en una percepción P_a (estocástica: el
                  sensor tiene ruido al estimar qué tan débil es cada puerta)
    M_a           estado mental mínimo: la puerta objetivo actual
    mentalUpdate  elige como objetivo la puerta percibida como más débil
    ACT_a         {avanzar, separarse, esperar}
    act_a         combina avanzar hacia el objetivo y separarse de los vecinos

No se necesita memoria: cada bot decide solo con lo que percibe.
Emergencia esperada: el enjambre termina concentrado en la puerta más débil.

Interfaz que usa el juego:
    ModeloAgentes(gen)
    .generar_enjambre(n, x, y)
    .paso(dt, puertas) -> list[(bot, indice_puerta)]   bots que llegaron
         puertas: lista de (x, y, debilidad)
    .metricas() -> list[(nombre, observado, teorico)]
"""
import math

from aleatorio import uniforme


class Bot:
    _siguiente_id = 0

    def __init__(self, x, y):
        Bot._siguiente_id += 1
        self.id = Bot._siguiente_id
        self.x, self.y = x, y
        self.objetivo = None     # M_a
        self.accion = "esperar"


class ModeloAgentes:
    nombre = "Basado en agentes"
    ACT = ("avanzar", "separarse", "esperar")

    def __init__(self, gen, velocidad=70, radio_percepcion=120, radio_separacion=24,
                 ruido_percepcion=0.15, peso_separacion=1.6):
        self.gen = gen
        self.vel = velocidad
        self.r_per = radio_percepcion
        self.r_sep = radio_separacion
        self.ruido = ruido_percepcion
        self.w_sep = peso_separacion
        self.bots = []
        self.decisiones = 0
        self.aciertos = 0          # decisiones que eligieron la puerta realmente más débil
        self.llegadas_por_puerta = {}

    def generar_enjambre(self, n, x, y):
        for _ in range(n):
            self.bots.append(Bot(x + uniforme(self.gen, -20, 20), y + uniforme(self.gen, -60, 60)))

    # ---------------------------------------------------- componentes AM_a
    def universo_relevante(self, bot, puertas):
        vecinos = [b for b in self.bots
                   if b is not bot and math.hypot(b.x - bot.x, b.y - bot.y) < self.r_per]
        return {"vecinos": vecinos, "puertas": puertas}

    def percibir(self, bot, ru):
        debilidades = [d + uniforme(self.gen, -self.ruido, self.ruido) for (_, _, d) in ru["puertas"]]
        cercanos = [b for b in ru["vecinos"] if math.hypot(b.x - bot.x, b.y - bot.y) < self.r_sep]
        return {"debilidades": debilidades, "cercanos": cercanos}

    def actualizar_mental(self, bot, percepcion, puertas):
        d = percepcion["debilidades"]
        bot.objetivo = max(range(len(d)), key=lambda i: d[i])
        real = max(range(len(puertas)), key=lambda i: puertas[i][2])
        self.decisiones += 1
        self.aciertos += int(bot.objetivo == real)

    def actuar(self, bot, percepcion, puertas, dt):
        tx, ty, _ = puertas[bot.objetivo]
        dx, dy = tx - bot.x, ty - bot.y
        dist = math.hypot(dx, dy) or 1.0
        vx, vy = dx / dist, dy / dist
        sx = sy = 0.0
        for o in percepcion["cercanos"]:
            ox, oy = bot.x - o.x, bot.y - o.y
            d = math.hypot(ox, oy) or 1.0
            sx += ox / d
            sy += oy / d
        bot.accion = "separarse" if percepcion["cercanos"] else "avanzar"
        vx += self.w_sep * sx
        vy += self.w_sep * sy
        norma = math.hypot(vx, vy) or 1.0
        bot.x += self.vel * dt * vx / norma
        bot.y += self.vel * dt * vy / norma

    # ---------------------------------------------------- paso del modelo
    def paso(self, dt, puertas):
        if not puertas:
            return []
        llegados = []
        for bot in list(self.bots):
            ru = self.universo_relevante(bot, puertas)
            p = self.percibir(bot, ru)
            if bot.objetivo is None or self.gen.random() < 0.02:
                self.actualizar_mental(bot, p, puertas)
            self.actuar(bot, p, puertas, dt)
            tx, ty, _ = puertas[bot.objetivo]
            if math.hypot(tx - bot.x, ty - bot.y) < 14:
                self.bots.remove(bot)
                self.llegadas_por_puerta[bot.objetivo] = self.llegadas_por_puerta.get(bot.objetivo, 0) + 1
                llegados.append((bot, bot.objetivo))
        return llegados

    def metricas(self):
        if len(self.bots) > 1:
            dist = []
            for b in self.bots:
                dist.append(min(math.hypot(b.x - o.x, b.y - o.y) for o in self.bots if o is not b))
            sep = sum(dist) / len(dist)
        else:
            sep = float("nan")
        acierto = self.aciertos / self.decisiones if self.decisiones else float("nan")
        return [
            ("Bots activos", len(self.bots), float("nan")),
            ("Decisiones tomadas", self.decisiones, float("nan")),
            ("% eligió la puerta más débil", acierto, float("nan")),
            ("Distancia media al vecino (px)", sep, self.r_sep),
        ]
