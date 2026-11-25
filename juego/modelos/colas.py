"""
Modelo 1 - Sistema de colas M/M/c/K para los firewalls.

Adaptador del módulo de Carrillo (modulos/..._modelo1_colas.py): el juego usa
directamente su clase ModeloColas, sus fórmulas M/M/c/K (teoria_mmck) y su
simulación de eventos discretos (simular_rapido, que usa el Predictor).
Aquí no se reimplementa nada; si el módulo cambia, el juego cambia con él.

Interfaz que usa el juego:
    ModeloColas(gen_llegadas, gen_servicio, lam, mu, c, K, llegadas_poisson)
    .interllegada() / .llegada(id) / .paso(dt) / .posicion(id)
    .agregar_servidor() / .ampliar_capacidad(n)
    .metricas() -> list[(nombre, observado, teorico)]
"""
from fuentes import modelo1

ModeloColas = modelo1.ModeloColas
teoria_mmck = modelo1.teoria_mmck
simular_rapido = modelo1.simular_rapido
