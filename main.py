# -*- coding: utf-8 -*-
"""
main.py
=======
Punto de entrada del programa (se ejecuta con: python main.py).

Este archivo NO tiene logica de inteligencia artificial: solo le pide
datos al usuario, llama a los demas modulos (base_conocimiento,
motor_reglas, busqueda) y muestra los resultados de forma legible.
Separar esto del resto es lo que permite que cada integrante del equipo
trabaje en su propio archivo sin pisar el trabajo de los demas (ver la
seccion "Estructura y equipo" en el README).
"""

import unicodedata

from base_conocimiento import HECHOS_ESTACION_EN, HECHOS_CONECTA, NOMBRE_VISIBLE
from motor_reglas import encadenar_hacia_adelante, imprimir_resumen
from busqueda import construir_grafo, buscar_mejor_ruta, RutaImposibleError


def normalizar_texto(texto):
    """
    Pasa un texto a minusculas, le quita las tildes y le quita signos de
    puntuacion (puntos, comas, guiones) y espacios de mas, para que el
    usuario pueda escribir "avenida jimenez", "Av. Jimenez", "AV JIMENEZ"
    o incluso "Av Jimenez" (sin el punto) y el programa reconozca todas
    esas formas como la misma estacion. unicodedata es parte de la
    biblioteca estandar de Python: no hace falta instalar nada para
    usarla.
    """
    texto_sin_tildes = unicodedata.normalize("NFKD", texto)
    texto_sin_tildes = "".join(
        caracter for caracter in texto_sin_tildes if not unicodedata.combining(caracter)
    )
    texto_en_minuscula = texto_sin_tildes.strip().lower()

    # Se reemplaza cada signo de puntuacion por un espacio (no se borra
    # sin mas) para que "Av.Jimenez" no termine pegado como "avjimenez".
    signos_a_quitar = ".,-_/"
    for signo in signos_a_quitar:
        texto_en_minuscula = texto_en_minuscula.replace(signo, " ")

    # "  ".join(texto.split()) es la forma estandar en Python de colapsar
    # cualquier cantidad de espacios seguidos en uno solo.
    return " ".join(texto_en_minuscula.split())


def buscar_id_estacion(texto_del_usuario):
    """
    Busca el identificador interno de una estacion (el que usa
    ESTACIONES en base_conocimiento.py) a partir de lo que escribio el
    usuario, comparando contra el nombre visible ya normalizado.
    Devuelve None si no encuentra ninguna coincidencia.
    """
    texto_normalizado = normalizar_texto(texto_del_usuario)
    for id_estacion, nombre_visible in NOMBRE_VISIBLE.items():
        if normalizar_texto(nombre_visible) == texto_normalizado:
            return id_estacion
    return None


def construir_grafo_del_sistema(mostrar_progreso=False):
    """
    Corre el motor de inferencia sobre la base de conocimiento y arma el
    grafo que va a usar la busqueda A*. Se separa de preparar_sistema()
    (mas abajo) para que este mismo arranque lo pueda reutilizar
    cualquier punto de entrada del programa sin repetir la logica: lo usa
    tanto la CLI de este archivo como interfaz.py (la version grafica),
    para garantizar que las dos arrancan el sistema EXACTAMENTE igual.

    Devuelve una tupla (hechos_derivados, grafo): hechos_derivados hace
    falta ademas para cosas como imprimir_resumen() o para que la
    interfaz grafica sepa que estaciones son de transbordo
    (motor_reglas.obtener_estaciones_transbordo).
    """
    hechos_iniciales = list(HECHOS_ESTACION_EN) + list(HECHOS_CONECTA)
    hechos_derivados = encadenar_hacia_adelante(hechos_iniciales, mostrar_progreso=mostrar_progreso)
    return hechos_derivados, construir_grafo(hechos_derivados)


def preparar_sistema():
    """
    Corre el motor de inferencia UNA sola vez, al arrancar el programa, y
    arma el grafo que va a usar la busqueda. No tendria sentido volver a
    calcular los hechos derivados en cada consulta: la base de
    conocimiento no cambia mientras el programa esta corriendo.
    """
    print("Aplicando el motor de inferencia sobre la base de conocimiento...")
    hechos_derivados, grafo = construir_grafo_del_sistema(mostrar_progreso=True)
    print()
    imprimir_resumen(hechos_derivados)
    print()

    return grafo


def mostrar_lista_de_estaciones():
    print("Estaciones disponibles (43 en total, agrupadas alfabeticamente):")
    nombres_ordenados = sorted(NOMBRE_VISIBLE.values())
    for nombre in nombres_ordenados:
        print(f"  - {nombre}")


def mostrar_resultado(resultado):
    print()
    print("Ruta encontrada:")
    for id_estacion in resultado.estaciones:
        print(f"  -> {NOMBRE_VISIBLE[id_estacion]}")
    print()
    print(f"Numero de estaciones en la ruta : {len(resultado.estaciones)}")
    print(f"Numero de transbordos           : {resultado.num_transbordos}")
    print(f"Tiempo estimado de viaje        : {resultado.tiempo_total_min:.1f} minutos")


def pedir_una_estacion(mensaje, grafo):
    """
    Pide una estacion por consola hasta que el usuario escriba algo
    valido, o los comandos especiales 'lista' (mostrar estaciones) o
    'salir' (terminar el programa). Devuelve el identificador interno de
    la estacion, o None si el usuario pidio salir.
    """
    while True:
        texto = input(mensaje).strip()

        if normalizar_texto(texto) == "salir":
            return None

        if normalizar_texto(texto) == "lista":
            mostrar_lista_de_estaciones()
            continue

        id_estacion = buscar_id_estacion(texto)
        if id_estacion is not None:
            return id_estacion

        print(f"No reconozco la estacion '{texto}'.")
        print("Escriba 'lista' para ver los nombres exactos, o 'salir' para terminar.")


def main():
    grafo = preparar_sistema()

    print("=" * 70)
    print("Sistema de rutas de TransMilenio (reglas logicas + busqueda A*)")
    print("Escriba 'lista' para ver las estaciones disponibles.")
    print("Escriba 'salir' en cualquier momento para terminar el programa.")
    print("=" * 70)

    while True:
        print()
        id_origen = pedir_una_estacion("Estacion de origen: ", grafo)
        if id_origen is None:
            break

        id_destino = pedir_una_estacion("Estacion de destino: ", grafo)
        if id_destino is None:
            break

        try:
            resultado = buscar_mejor_ruta(grafo, id_origen, id_destino)
            mostrar_resultado(resultado)
        except RutaImposibleError as error:
            print(f"No se pudo calcular la ruta: {error}")

    print()
    print("Gracias por usar el sistema. Hasta pronto.")


if __name__ == "__main__":
    main()
