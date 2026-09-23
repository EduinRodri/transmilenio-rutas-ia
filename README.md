# Rutas en TransMilenio con reglas lógicas y búsqueda A*

Sistema que encuentra la mejor ruta entre dos estaciones de TransMilenio (Bogotá).
Combina una base de conocimiento escrita en reglas lógicas con el algoritmo de búsqueda
heurística A*.

Proyecto de la asignatura Inteligencia Artificial — Corporación Universitaria
Iberoamericana, 2026-2.

## Cómo funciona

1. **Base de conocimiento.** Se declaran solo hechos: las estaciones, sus coordenadas, a
   qué troncal pertenece cada una y cuáles están conectadas.
2. **Motor de inferencia.** Aplica cuatro reglas por encadenamiento hacia adelante y
   deduce hechos nuevos. Por ejemplo: *si una estación pertenece a dos troncales, es una
   estación de transbordo*. Así el sistema descubre por sí mismo que Héroes, Av. Jiménez y
   Ricaurte son puntos de transbordo; no están escritos a mano en ninguna parte.
3. **Búsqueda A\*.** Recorre la red buscando la ruta de menor tiempo. Usa como heurística
   la distancia en línea recta hasta el destino (fórmula de Haversine), que nunca
   sobreestima el costo real y por eso garantiza la ruta óptima. Cada transbordo suma
   una penalización de tiempo.

## Requisitos

Python 3.10 o superior. No hay que instalar nada: el proyecto usa solo la biblioteca
estándar, así que puede correr en cualquier computador.

## Cómo ejecutarlo

```
git clone https://github.com/EduinRodri/transmilenio-rutas-ia.git
cd transmilenio-rutas-ia
```

| Comando | Qué hace |
|---|---|
| `python interfaz.py` | Abre la ventana con el mapa. Se eligen origen y destino y la ruta se dibuja sobre las estaciones. |
| `python main.py` | Versión en consola. Muestra primero cómo el motor deduce hechos nuevos y luego pide origen y destino. Escribir `lista` muestra las estaciones; `salir` termina. |
| `python pruebas.py` | Ejecuta los 8 casos de prueba. Debe terminar con *Todas las pruebas terminaron sin errores.* |

Si `python` no responde, probar con `py` o `python3`.

## Estructura y equipo

| Archivo | Contenido | Responsable |
|---|---|---|
| `base_conocimiento.py` | Hechos: 43 estaciones, 7 troncales y sus conexiones | Erika Milena Bernal |
| `motor_reglas.py` | Motor de inferencia y las 4 reglas lógicas | Erika Milena Bernal |
| `busqueda.py` | Algoritmo A*, heurística y costos | Juan Diego Quintero Zambrano |
| `interfaz.py` | Interfaz gráfica con el mapa (Tkinter) | Juan Diego Quintero Zambrano |
| `main.py` | Interfaz de consola y arranque del sistema | Eduin Rodríguez |
| `pruebas.py` | Casos de prueba | Eduin Rodríguez |
| `docs/pruebas-realizadas.pdf` | Resultados de las pruebas | Eduin Rodríguez |

## Datos

Los nombres y las coordenadas de las estaciones vienen del conjunto de datos oficial
*Estaciones Troncales de TRANSMILENIO*, publicado por TransMilenio S.A. en
[Datos Abiertos Bogotá](https://datosabiertos.bogota.gov.co/dataset/estaciones-troncales-de-transmilenio)
(consultado el 20 de septiembre de 2026). De las 153 estaciones del sistema se tomaron 43,
de las troncales Autopista Norte, Caracas, Calle 26, NQS, Américas, Calle 80 y Suba.

Simplificaciones que conviene tener presentes:

- Los nombres omiten el patrocinador comercial (*Héroes* en lugar de *Héroes - Colmena
  Seguros*).
- Ricaurte se modela como una sola estación, aunque en la realidad son dos plataformas
  cercanas.
- El orden de las paradas en cada troncal se reconstruyó por posición geográfica, porque
  el conjunto de datos no lo incluye.
- Para unir troncales que en este modelo no comparten estación se agregaron tres
  conexiones a pie, marcadas como `INTEGRACION` en el código: Polo–Héroes,
  Suba Calle 100–Calle 100 y CAD–CDS Carrera 32.

## Supuestos del modelo

Los tiempos son estimaciones, no datos operativos de TransMilenio. Los valores están al
inicio de `busqueda.py`:

- Velocidad promedio del bus troncal: 20 km/h
- Velocidad caminando en una conexión de integración: 4,5 km/h
- Penalización por transbordo: 5 minutos

Como solo se modeló una parte de la red, algunas rutas entre troncales lejanas dan
tiempos mayores que en la realidad: deben pasar por la única conexión disponible entre
esos grupos de troncales.

## Referencias

- Benítez, R. (2014). *Inteligencia artificial avanzada*. Editorial UOC. Capítulos 2, 3 y 9.
- TransMilenio S.A. (2026). *Estaciones Troncales de TRANSMILENIO* [Conjunto de datos].
  Datos Abiertos Bogotá.

---

Docente: Sandra Isabel Rodríguez Bautista
