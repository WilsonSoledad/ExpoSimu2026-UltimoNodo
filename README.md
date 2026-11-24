# Último Nodo · ExpoSimu 2026

Taller final de **Simulación por Computador** (UPTC, 2026). Tower defense en Python con Pygame
que integra cinco modelos de simulación: colas, caminatas aleatorias, Monte Carlo,
simulación basada en agentes y dinámica de sistemas.

> Año 2049. Un malware llamado La Plaga apaga las redes del país. Ada Rincón, operadora
> de sistemas, debe resistir hasta que el respaldo del Núcleo llegue al 100 %.

## Estructura

```
prng/        Generadores del taller anterior (compartidos por todos los módulos)
modulos/     Punto 3.1: los cinco módulos independientes, ejecutables por separado
juego/       Punto 4: el juego en Pygame (ver juego/README.md)
assets/      Punto 3.2: sprites, audio y bocetos
docs/        Informe, capturas de validación y figuras
```

Cada módulo existe **una sola vez**, en `modulos/`. El juego no copia su código: los archivos
de `juego/modelos/` son adaptadores que lo importan.

## Cómo ejecutar

```
pip install -r requirements.txt

cd juego
python main.py                            # el juego

cd ../modulos
python carrillo_modelo1_colas.py          # un módulo independiente
```

## Estado de los modelos

| N.º | Modelo | Módulo | Responsable | Estado |
|---|---|---|---|---|
| 1 | Colas | `Paredes_Carrillo_Soledad_Suarez_modelo1_colas.py` | Carrillo | Entregado. El juego usa su generador; falta la capacidad K |
| 2 | Caminata aleatoria | `Paredes_Carrillo_Soledad_Suarez_modelo2_caminatas.py` | Carrillo | Entregado. El juego usa su generador; la regla de paso se replica en el adaptador |
| 3 | Monte Carlo | — | Integrante 3 | Pendiente |
| 4 | Basado en agentes | `Paredes_Carrillo_Soledad_Suarez_modelo4_agentes.py` | Paredes | Entregado; pendiente ajustar a acciones discretas |
| 5 | Dinámica de sistemas (SIR) | `Paredes_Carrillo_Soledad_Suarez_modelo5_sir.py` | Paredes | Entregado e integrado (ecuaciones, RK4 y pico teórico) |

Los módulos se importan desde un solo archivo, `juego/fuentes.py`. Mientras un módulo no esté
integrado, el juego usa una versión provisional (ver `juego/modelos/`).

