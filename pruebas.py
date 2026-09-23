# -*- coding: utf-8 -*-
"""
pruebas.py
==========
Pruebas del sistema completo (base de conocimiento + motor de reglas +
busqueda). No se usa ningun framework externo como pytest, para
cumplir con la regla de "cero dependencias" del proyecto: se ejecuta con

    python pruebas.py

Cada prueba imprime la ruta que encontro (para poder revisarla a simple
vista) y ademas usa "assert" para que el programa se detenga solo, con un
mensaje claro, si algun resultado deja de cumplirse en el futuro (por
ejemplo, si alguien cambia una coordenada y sin querer rompe una ruta).

Los numeros exactos que se comprueban aqui (cuantos transbordos tiene
cada ruta, etc.) no se inventaron: se sacaron de correr el programa una
vez, revisar que la ruta tuviera sentido geografico, y solo despues
escribirlos como el resultado esperado.
"""

from base_conocimiento import HECHOS_ESTACION_EN, HECHOS_CONECTA, NOMBRE_VISIBLE, ESTACIONES
from motor_reglas import encadenar_hacia_adelante
from busqueda import (
    construir_grafo,
    buscar_mejor_ruta,
    ubicaciones_de_transbordo,
    EstacionInexistenteError,
)


def preparar_grafo_de_prueba():
    """Arma el grafo exactamente igual que main.py, para probar el sistema completo y no una version simplificada."""
    hechos_iniciales = list(HECHOS_ESTACION_EN) + list(HECHOS_CONECTA)
    hechos_derivados = encadenar_hacia_adelante(hechos_iniciales)
    return construir_grafo(hechos_derivados)


def imprimir_encabezado(titulo):
    print()
    print("=" * 72)
    print(titulo)
    print("=" * 72)


def estaciones_de_transbordo(resultado):
    """Lista de las estaciones donde ocurre cada transbordo, en orden."""
    return [estacion for estacion, _, _ in ubicaciones_de_transbordo(resultado)]


def imprimir_ruta(resultado):
    nombres = [NOMBRE_VISIBLE[id_estacion] for id_estacion in resultado.estaciones]
    print(" -> ".join(nombres))
    print(
        f"Estaciones: {len(resultado.estaciones)}  |  "
        f"Transbordos: {resultado.num_transbordos}  |  "
        f"Tiempo estimado: {resultado.tiempo_total_min:.1f} min"
    )


def prueba_1_ruta_directa_sin_transbordo(grafo):
    imprimir_encabezado("Prueba 1: ruta directa, sin transbordo (misma troncal)")
    resultado = buscar_mejor_ruta(grafo, "Portal_Norte", "Calle_85")
    imprimir_ruta(resultado)
    assert resultado.num_transbordos == 0, "Se esperaba una ruta sin transbordos"
    print("OK: la ruta se queda en la troncal Autopista Norte de principio a fin.")


def prueba_2_ruta_con_un_transbordo(grafo):
    imprimir_encabezado("Prueba 2: ruta con exactamente un transbordo")
    resultado = buscar_mejor_ruta(grafo, "Portal_Norte", "Calle_72")
    imprimir_ruta(resultado)
    assert resultado.num_transbordos == 1, f"Se esperaba 1 transbordo y hubo {resultado.num_transbordos}"
    assert estaciones_de_transbordo(resultado) == ["Heroes"], "El transbordo deberia ocurrir en Heroes"
    print("OK: el transbordo ocurre en Heroes, que el motor de reglas detecto solo como estacion de transbordo.")


def prueba_3_ruta_con_dos_transbordos(grafo):
    imprimir_encabezado("Prueba 3: ruta con exactamente dos transbordos")
    resultado = buscar_mejor_ruta(grafo, "Portal_Norte", "Portal_El_Dorado")
    imprimir_ruta(resultado)
    assert resultado.num_transbordos == 2, f"Se esperaban 2 transbordos y hubo {resultado.num_transbordos}"
    assert estaciones_de_transbordo(resultado) == ["Heroes", "Av_Jimenez"], (
        "Los transbordos deberian ocurrir en Heroes y en Av. Jimenez, en ese orden"
    )
    print("OK: transbordos en Heroes (Autopista Norte -> Caracas) y en Av. Jimenez (Caracas -> Eje Ambiental).")


def prueba_4_origen_igual_a_destino(grafo):
    imprimir_encabezado("Prueba 4: origen igual al destino")
    resultado = buscar_mejor_ruta(grafo, "Heroes", "Heroes")
    imprimir_ruta(resultado)
    assert resultado.estaciones == ["Heroes"], "La ruta deberia contener solo la estacion de salida"
    assert resultado.num_transbordos == 0
    assert resultado.tiempo_total_min == 0.0
    print("OK: el sistema no intenta moverse si el origen y el destino son la misma estacion.")


def prueba_5_estacion_inexistente(grafo):
    imprimir_encabezado("Prueba 5: se pide una estacion que no existe")
    try:
        buscar_mejor_ruta(grafo, "Estacion_Que_No_Existe", "Portal_Norte")
        raise AssertionError("Se esperaba un EstacionInexistenteError y no se lanzo ninguno")
    except EstacionInexistenteError as error:
        print("OK: el sistema rechazo la estacion inexistente con este mensaje:")
        print(f"    {error}")


def prueba_6_ruta_larga_extremo_a_extremo(grafo):
    imprimir_encabezado("Prueba 6: ruta larga, de un extremo de la ciudad al otro")
    resultado = buscar_mejor_ruta(grafo, "Portal_Norte", "Portal_Americas")
    imprimir_ruta(resultado)
    assert len(resultado.estaciones) > 15, "Se esperaba una ruta larga, con muchas estaciones"
    assert resultado.num_transbordos == 3, f"Se esperaban 3 transbordos y hubo {resultado.num_transbordos}"

    # Comprobacion geografica: la ruta tiene dos fases y cada una va en una sola direccion.
    # 1) Desde Portal Norte hasta Av. Jimenez baja hacia el sur (la latitud nunca aumenta).
    # 2) Desde Av. Jimenez hasta Portal Americas avanza hacia el occidente (la longitud
    #    nunca aumenta). En esta fase la latitud sube un poco, y es correcto: Portal
    #    Americas esta mas al norte que Av. Jimenez.
    corte = resultado.estaciones.index("Av_Jimenez")
    latitudes = [ESTACIONES[e][0] for e in resultado.estaciones[: corte + 1]]
    longitudes = [ESTACIONES[e][1] for e in resultado.estaciones[corte:]]
    assert all(a >= b for a, b in zip(latitudes, latitudes[1:])), "En la primera fase la ruta volvio hacia el norte"
    assert all(a >= b for a, b in zip(longitudes, longitudes[1:])), "En la segunda fase la ruta volvio hacia el oriente"

    print("OK: la ruta baja por la Autopista Norte y la Caracas hasta Av. Jimenez, y desde ahi")
    print("    avanza hacia el occidente por la Calle 26 y la troncal Americas sin devolverse.")
    print(f"    Transbordos en: {', '.join(NOMBRE_VISIBLE[e] for e in estaciones_de_transbordo(resultado))}.")


def prueba_7_usa_conexiones_de_integracion(grafo):
    imprimir_encabezado("Prueba 7 (extra): ruta que depende de las conexiones de integracion")
    resultado = buscar_mejor_ruta(grafo, "Portal_Suba", "Portal_80")
    imprimir_ruta(resultado)
    tramos_a_pie = resultado.tramos_troncal.count("INTEGRACION")
    assert tramos_a_pie >= 1, "Se esperaba que la ruta usara al menos una conexion de integracion"
    print(f"OK: Suba y Calle 80 no comparten estacion en este modelo, asi que la ruta usa {tramos_a_pie}")
    print("    conexiones de integracion (caminatas) declaradas en base_conocimiento.py.")


def prueba_8_resultado_determinista(grafo):
    imprimir_encabezado("Prueba 8 (extra): dos consultas seguidas devuelven siempre el mismo resultado")
    resultado_1 = buscar_mejor_ruta(grafo, "Calle_45", "Universidad_Nacional")
    resultado_2 = buscar_mejor_ruta(grafo, "Calle_45", "Universidad_Nacional")
    imprimir_ruta(resultado_1)
    assert resultado_1.estaciones == resultado_2.estaciones
    assert resultado_1.tiempo_total_min == resultado_2.tiempo_total_min
    print("OK: A* es determinista con estos datos: la misma consulta siempre da la misma ruta.")


def main():
    grafo = preparar_grafo_de_prueba()

    prueba_1_ruta_directa_sin_transbordo(grafo)
    prueba_2_ruta_con_un_transbordo(grafo)
    prueba_3_ruta_con_dos_transbordos(grafo)
    prueba_4_origen_igual_a_destino(grafo)
    prueba_5_estacion_inexistente(grafo)
    prueba_6_ruta_larga_extremo_a_extremo(grafo)
    prueba_7_usa_conexiones_de_integracion(grafo)
    prueba_8_resultado_determinista(grafo)

    print()
    print("=" * 72)
    print("Todas las pruebas terminaron sin errores.")
    print("=" * 72)


if __name__ == "__main__":
    main()
