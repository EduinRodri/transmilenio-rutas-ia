"""
motor_reglas.py
================
Este es el MOTOR DE INFERENCIA del sistema experto: la parte que razona
sobre los hechos de base_conocimiento.py y deriva hechos NUEVOS que nadie
escribio a mano. La tecnica se llama "encadenamiento hacia adelante"
(forward chaining, Benitez 2014, cap. 3): se parte de los hechos que se
conocen y se van aplicando reglas del tipo

    SI (se cumplen ciertas condiciones) ENTONCES (se puede afirmar un
    hecho nuevo)

una y otra vez, hasta que en una vuelta completa ya no aparece NINGUN
hecho nuevo. A ese momento se le llama "punto fijo": el sistema ya sabe
todo lo que podia deducir con las reglas que tiene.

Por que esto no es solo un adorno academico: los hechos "conecta" que
estan en base_conocimiento.py SOLO van en un sentido (de la estacion mas
al sur/este hacia la mas al norte/oeste). Si busqueda.py usara esos
hechos tal cual, la mitad de las rutas no se podrian calcular (un bus se
puede tomar en los dos sentidos). La REGLA 1 de este motor es la que
completa el sentido contrario. Si se borrara esa regla, el programa
completo dejaria de funcionar bien: por eso el motor de reglas es una
pieza necesaria, no decorativa.

Las 4 reglas implementadas:

  R1 (bidireccionalidad):
     SI conecta(A, B, T) ENTONCES conecta(B, A, T)

  R2 (estacion de transbordo):
     SI estacion_en(A, T1) Y estacion_en(A, T2) Y T1 != T2
     ENTONCES es_estacion_transbordo(A)

  R3 (punto de enlace, usa lo que dedujo R2 -> encadenamiento real):
     SI es_estacion_transbordo(A) Y conecta(A, B, T)
     ENTONCES punto_de_enlace(B, T)

  R4 (ruta directa de dos saltos dentro de la misma troncal):
     SI conecta(A, B, T) Y conecta(B, C, T) Y A != C
     ENTONCES ruta_directa(A, C, T)
"""

from base_conocimiento import Hecho


def _regla_bidireccionalidad(hechos):
    """R1: si se puede ir de A a B, tambien se puede ir de B a A."""
    nuevos = []
    for h in hechos:
        if h.predicado == "conecta":
            origen, destino, troncal = h.argumentos
            candidato = Hecho("conecta", destino, origen, troncal)
            if candidato not in hechos and candidato not in nuevos:
                nuevos.append(candidato)
    return nuevos


def _regla_transbordo(hechos):
    """R2: una estacion que aparece en mas de una troncal es de transbordo."""
    troncales_por_estacion = {}
    for h in hechos:
        if h.predicado == "estacion_en":
            estacion, troncal = h.argumentos
            troncales_por_estacion.setdefault(estacion, set()).add(troncal)

    nuevos = []
    for estacion, troncales in troncales_por_estacion.items():
        if len(troncales) > 1:
            candidato = Hecho("es_estacion_transbordo", estacion)
            if candidato not in hechos and candidato not in nuevos:
                nuevos.append(candidato)
    return nuevos


def _regla_punto_de_enlace(hechos):
    """
    R3: la estacion a la que se llega justo despues de una estacion de
    transbordo es un "punto de enlace" de esa troncal. Esta regla depende
    de lo que haya derivado R2 en una vuelta anterior: es la prueba de
    que el motor realmente ENCADENA reglas y no solo las aplica una vez.
    """
    estaciones_transbordo = {
        h.argumentos[0] for h in hechos if h.predicado == "es_estacion_transbordo"
    }

    nuevos = []
    for h in hechos:
        if h.predicado == "conecta":
            origen, destino, troncal = h.argumentos
            if origen in estaciones_transbordo:
                candidato = Hecho("punto_de_enlace", destino, troncal)
                if candidato not in hechos and candidato not in nuevos:
                    nuevos.append(candidato)
    return nuevos


def _regla_ruta_directa(hechos):
    """R4: si se puede ir de A a B y de B a C por la misma troncal, hay ruta directa de A a C."""
    conexiones = [h for h in hechos if h.predicado == "conecta"]

    nuevos = []
    for primer_tramo in conexiones:
        a, b, troncal_1 = primer_tramo.argumentos
        for segundo_tramo in conexiones:
            b2, c, troncal_2 = segundo_tramo.argumentos
            if b == b2 and troncal_1 == troncal_2 and a != c:
                candidato = Hecho("ruta_directa", a, c, troncal_1)
                if candidato not in hechos and candidato not in nuevos:
                    nuevos.append(candidato)
    return nuevos


# El orden de esta lista no cambia el resultado final (el punto fijo es
# el mismo), pero si cambia cuantas vueltas tarda en llegar a el. Se deja
# en este orden porque es el orden logico de dependencia: primero se
# completan las conexiones (R1), despues se descubren los transbordos
# (R2), y las reglas que dependen de esas dos (R3 y R4) van al final.
REGLAS = [
    _regla_bidireccionalidad,
    _regla_transbordo,
    _regla_punto_de_enlace,
    _regla_ruta_directa,
]


def encadenar_hacia_adelante(hechos_iniciales, mostrar_progreso=False):
    """
    Aplica todas las reglas de REGLAS, una y otra vez, hasta que una
    vuelta completa no produzca ningun hecho nuevo (punto fijo).

    Devuelve la lista completa de hechos: los que ya se tenian mas todos
    los que se lograron derivar. Con mostrar_progreso=True se imprime
    cuantos hechos nuevos aparecieron en cada vuelta, que es la forma mas
    directa de DEMOSTRAR que el encadenamiento hacia adelante esta
    funcionando de verdad.
    """
    hechos = list(hechos_iniciales)
    numero_de_ronda = 0

    while True:
        numero_de_ronda += 1
        hechos_nuevos_en_esta_ronda = []

        for regla in REGLAS:
            hechos_que_propone_la_regla = regla(hechos)
            for hecho_propuesto in hechos_que_propone_la_regla:
                ya_esta = (
                    hecho_propuesto in hechos
                    or hecho_propuesto in hechos_nuevos_en_esta_ronda
                )
                if not ya_esta:
                    hechos_nuevos_en_esta_ronda.append(hecho_propuesto)

        if not hechos_nuevos_en_esta_ronda:
            if mostrar_progreso:
                print(f"  Ronda {numero_de_ronda}: no aparecieron hechos nuevos. Punto fijo alcanzado.")
            break

        if mostrar_progreso:
            print(f"  Ronda {numero_de_ronda}: se derivaron {len(hechos_nuevos_en_esta_ronda)} hechos nuevos.")

        hechos.extend(hechos_nuevos_en_esta_ronda)

    return hechos


def contar_hechos_por_predicado(hechos):
    """Util para imprimir un resumen legible: cuantos hechos hay de cada tipo."""
    conteo = {}
    for h in hechos:
        conteo[h.predicado] = conteo.get(h.predicado, 0) + 1
    return conteo


def obtener_estaciones_transbordo(hechos):
    """
    Devuelve el conjunto de identificadores de estacion que el motor de
    reglas DERIVO como transbordo (el predicado "es_estacion_transbordo",
    que produce la regla R2). Se deja como funcion aparte, en vez de
    repetir esta misma linea en cada lugar que la necesita (imprimir_resumen
    aqui abajo, y ademas interfaz.py para dibujar el mapa), para que solo
    exista UN lugar del codigo que sabe como leer ese hecho.
    """
    return {h.argumentos[0] for h in hechos if h.predicado == "es_estacion_transbordo"}


def imprimir_resumen(hechos):
    """Muestra en pantalla, de forma legible, que aprendio el motor de reglas."""
    conteo = contar_hechos_por_predicado(hechos)
    print("Resumen de hechos despues del encadenamiento hacia adelante:")
    for predicado, cantidad in sorted(conteo.items()):
        print(f"  - {predicado}: {cantidad} hechos")

    estaciones_transbordo = sorted(obtener_estaciones_transbordo(hechos))
    print("Estaciones de transbordo DERIVADAS por el motor (no estaban escritas a mano):")
    for estacion in estaciones_transbordo:
        print(f"  - {estacion}")
