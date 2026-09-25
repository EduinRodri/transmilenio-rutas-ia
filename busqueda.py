# -*- coding: utf-8 -*-
"""
busqueda.py
===========
Aqui vive el algoritmo que encuentra la MEJOR ruta entre dos estaciones:
A* (A-estrella), una busqueda heuristica (Benitez 2014, cap. 9).

Por que A* y no, por ejemplo, un recorrido a lo ciego (BFS): en este
problema "mejor" no significa "con menos estaciones", significa "con
menos TIEMPO", y el tiempo depende de la distancia real recorrida y de
cuantas veces hay que cambiar de bus (transbordar). A* explora primero
los caminos mas prometedores en vez de revisar la ciudad entera, siempre
y cuando se le de una heuristica que nunca "mienta" quedandose corta en
optimismo: es decir, que nunca sobreestime lo que falta. A eso se le
llama heuristica ADMISIBLE, y es la condicion que garantiza que A*
encuentre siempre la ruta optima (no una aproximada).

La heuristica que se usa aqui es la distancia en linea recta entre dos
estaciones (formula de Haversine, que si tiene en cuenta que la Tierra es
una esfera y no un plano) dividida entre la velocidad MAXIMA que puede
alcanzar cualquier tramo del sistema. Como en la realidad nunca se viaja
mas rapido que esa velocidad maxima, el tiempo real siempre va a ser
mayor o igual que esta estimacion: por eso nunca sobreestima, y por eso
es admisible.
"""

import heapq
import itertools
import math
from collections import namedtuple

from base_conocimiento import ESTACIONES, INTEGRACION


# ---------------------------------------------------------------------
# Supuestos de tiempo del modelo
# ---------------------------------------------------------------------
# Estos numeros son estimaciones razonables para un ejercicio academico,
# NO datos operativos oficiales de TransMilenio (la velocidad comercial
# real varia por hora del dia, por troncal y por congestion). Se dejan
# aqui, en una sola parte del codigo, para que sea facil ajustarlos o
# defenderlos si preguntan de donde salieron.
VELOCIDAD_TRONCAL_KMH = 20.0       # velocidad comercial promedio estimada de un bus troncal
VELOCIDAD_INTEGRACION_KMH = 4.5    # velocidad de caminata para una conexion de integracion
PENALIZACION_TRANSBORDO_MIN = 5.0  # minutos que se pierden al bajar, cruzar el puente y esperar el siguiente bus


class EstacionInexistenteError(Exception):
    """El nombre de estacion que se pidio no existe en la base de conocimiento."""


class RutaImposibleError(Exception):
    """Las dos estaciones existen, pero no hay ningun camino que las una en el grafo actual."""


# Lo que necesita main.py (y pruebas.py) para mostrar una ruta ya calculada.
ResultadoRuta = namedtuple(
    "ResultadoRuta",
    ["estaciones", "tramos_troncal", "tiempo_total_min", "num_transbordos"],
)


def distancia_haversine_km(estacion_a, estacion_b):
    """
    Distancia en linea recta entre dos estaciones, en kilometros, usando
    sus coordenadas geograficas reales. Se usa Haversine (y no el teorema
    de Pitagoras comun) porque la Tierra es una esfera: a la escala de
    una ciudad el error de usar Pitagoras seria pequeno, pero Haversine
    es el estandar para este tipo de calculo y es el que corresponde a un
    capitulo de busquedas heuristicas con coordenadas geograficas reales.
    """
    radio_tierra_km = 6371.0
    lat_a, lon_a = ESTACIONES[estacion_a]
    lat_b, lon_b = ESTACIONES[estacion_b]

    lat_a_rad = math.radians(lat_a)
    lat_b_rad = math.radians(lat_b)
    delta_lat_rad = math.radians(lat_b - lat_a)
    delta_lon_rad = math.radians(lon_b - lon_a)

    termino = (
        math.sin(delta_lat_rad / 2) ** 2
        + math.cos(lat_a_rad) * math.cos(lat_b_rad) * math.sin(delta_lon_rad / 2) ** 2
    )
    angulo_central_rad = 2 * math.asin(math.sqrt(termino))
    return radio_tierra_km * angulo_central_rad


def _velocidad_del_tramo(troncal):
    """Las conexiones de integracion (caminata) son mucho mas lentas que un bus troncal."""
    if troncal == INTEGRACION:
        return VELOCIDAD_INTEGRACION_KMH
    return VELOCIDAD_TRONCAL_KMH


def _tiempo_del_tramo_min(distancia_km, troncal):
    velocidad_kmh = _velocidad_del_tramo(troncal)
    horas = distancia_km / velocidad_kmh
    return horas * 60.0


def _heuristica_min(estacion, destino):
    """
    Estimacion optimista (nunca sobreestima) del tiempo que falta para
    llegar al destino: distancia en linea recta a la velocidad MAS ALTA
    posible en todo el sistema (la de un bus troncal, no la de caminar).
    No incluye penalizaciones de transbordo a proposito: como esas
    penalizaciones solo pueden SUMAR costo real, ignorarlas en la
    heuristica jamas hace que se sobreestime.
    """
    distancia_km = distancia_haversine_km(estacion, destino)
    return (distancia_km / VELOCIDAD_TRONCAL_KMH) * 60.0


def construir_grafo(hechos):
    """
    Convierte los hechos "conecta" (ya completados en los dos sentidos
    por el motor de reglas) en un diccionario de adyacencia:
        { estacion: [(vecino, troncal_del_tramo, distancia_km), ...] }

    Este grafo se arma a partir de los hechos DERIVADOS por
    motor_reglas.py, no de una lista aparte escrita a mano. Si el motor
    de reglas no hubiera derivado el sentido contrario de cada conexion
    (regla R1), la mitad de las estaciones de este grafo se quedarian
    sin salida.
    """
    grafo = {}
    for h in hechos:
        if h.predicado == "conecta":
            origen, destino, troncal = h.argumentos
            distancia_km = distancia_haversine_km(origen, destino)
            grafo.setdefault(origen, []).append((destino, troncal, distancia_km))
    return grafo


def contar_transbordos(tramos_troncal):
    """
    Cuenta cuantas veces un pasajero realmente se BAJA de un bus para
    montarse en uno de una troncal distinta, a partir de la lista de
    troncales de cada tramo recorrido (en el orden en que se recorren).

    OJO con INTEGRACION (caminar entre dos estaciones de troncales
    distintas, ver base_conocimiento.py punto 5): un tramo de
    integracion NO es "montarse en un bus distinto", es la CAMINATA que
    conecta el bus que se deja con el bus que se va a tomar despues. Por
    eso aqui se salta (no se compara) cualquier tramo cuya troncal sea
    INTEGRACION: la "ultima troncal real" con la que se compara el
    siguiente tramo de bus sigue siendo la de ANTES de caminar. Asi, un
    viaje "bus A -> camina -> bus B" cuenta como UN solo transbordo (el
    que de verdad vive el pasajero), no dos.

    Si los tramos de integracion se compararan como una troncal mas,
    "sale de la troncal A" y "entra a la troncal B" se contarian como DOS
    transbordos separados en vez de uno solo.
    """
    ultima_troncal_real = None
    num_transbordos = 0
    for troncal in tramos_troncal:
        if troncal == INTEGRACION:
            # Caminando no se "cambia de troncal": se sigue en transicion
            # desde la ultima troncal real hasta que se aborde otro bus.
            continue
        if ultima_troncal_real is not None and troncal != ultima_troncal_real:
            num_transbordos += 1
        ultima_troncal_real = troncal
    return num_transbordos


def ubicaciones_de_transbordo(resultado):
    """
    A partir de un ResultadoRuta ya calculado, devuelve en que estacion
    ocurre CADA transbordo real: una lista de tuplas
    (id_estacion, troncal_de_la_que_se_baja, troncal_a_la_que_se_sube).

    Se usa la MISMA logica de contar_transbordos() (saltarse los tramos
    de INTEGRACION al comparar troncales), para que el numero de
    ubicaciones que devuelve esta funcion siempre sea igual a
    resultado.num_transbordos. Por eso esta funcion no repite esa logica
    desde cero: la vuelve a recorrer con el detalle extra de en que
    estacion pasa cada cosa, que es lo que necesita la interfaz grafica
    para mostrarle al usuario "el transbordo ocurre aqui".

    resultado.tramos_troncal[j] es el tramo que va de
    resultado.estaciones[j] a resultado.estaciones[j + 1]. Entonces,
    cuando el tramo j resulta ser de una troncal real distinta a la
    ultima troncal real (posiblemente varios tramos atras, si hubo una
    caminata de INTEGRACION en el medio), la estacion donde el pasajero
    SE SUBE al bus nuevo es resultado.estaciones[j] (el inicio de ese
    tramo): ya sea que vengan de bajarse del bus anterior ahi mismo, o de
    llegar caminando hasta ahi.
    """
    ubicaciones = []
    ultima_troncal_real = None
    for indice_tramo, troncal in enumerate(resultado.tramos_troncal):
        if troncal == INTEGRACION:
            continue
        if ultima_troncal_real is not None and troncal != ultima_troncal_real:
            estacion_del_transbordo = resultado.estaciones[indice_tramo]
            ubicaciones.append((estacion_del_transbordo, ultima_troncal_real, troncal))
        ultima_troncal_real = troncal
    return ubicaciones


def _reconstruir_resultado(nodo_padre, edge_troncal_usado, estado_final, tiempo_total_min):
    """
    A* guarda, para cada estado visitado, cual fue el estado anterior
    (nodo_padre) y con que troncal se llego a el (edge_troncal_usado).
    Para armar la ruta final hay que "devolverse" desde el destino hasta
    el origen siguiendo esos padres, y luego invertir la lista para que
    quede en el orden en que se recorre de verdad.
    """
    secuencia_de_estados = []
    estado = estado_final
    while estado is not None:
        secuencia_de_estados.append(estado)
        estado = nodo_padre[estado]
    secuencia_de_estados.reverse()

    estaciones = [estado[0] for estado in secuencia_de_estados]
    # El primer estado es el origen: no se llego a el por ningun tramo,
    # por eso se descarta aqui (edge_troncal_usado no tiene entrada para
    # el estado inicial).
    tramos_troncal = [edge_troncal_usado[estado] for estado in secuencia_de_estados[1:]]

    num_transbordos = contar_transbordos(tramos_troncal)

    return ResultadoRuta(estaciones, tramos_troncal, tiempo_total_min, num_transbordos)


def buscar_mejor_ruta(grafo, origen, destino):
    """
    Calcula la ruta de menor tiempo estimado entre "origen" y "destino"
    usando A*. Lanza EstacionInexistenteError si alguna de las dos
    estaciones no esta en la base de conocimiento, y RutaImposibleError
    si ambas existen pero el grafo no las conecta.
    """
    if origen not in ESTACIONES:
        raise EstacionInexistenteError(
            f"La estacion de origen '{origen}' no existe en la base de conocimiento."
        )
    if destino not in ESTACIONES:
        raise EstacionInexistenteError(
            f"La estacion de destino '{destino}' no existe en la base de conocimiento."
        )

    if origen == destino:
        # Caso trivial: no hay que moverse. Se resuelve aparte para no
        # complicar el bucle principal de A* con un caso especial.
        return ResultadoRuta([origen], [], 0.0, 0)

    # El "estado" de la busqueda no es solo la estacion: tambien incluye
    # la ULTIMA TRONCAL REAL en la que se viene viajando (la del ultimo
    # BUS abordado, no la del ultimo tramo caminado). Esto es necesario
    # para poder calcular la penalizacion de transbordo del siguiente
    # tramo (si el estado solo fuera la estacion, no habria forma de
    # saber si el bus que se toma despues es el mismo que ya se traia).
    # El origen todavia no ha usado ninguna troncal, por eso se marca
    # con None.
    #
    # Por que "ultima troncal REAL" y no simplemente "troncal del tramo
    # con el que se llego": un tramo de INTEGRACION (caminar entre dos
    # estaciones de troncales distintas) no es subirse a un bus, asi que
    # no debe borrar de la memoria del estado cual fue el ultimo bus real
    # que se tomo. Si guardara la troncal del ULTIMO TRAMO (fuera bus o
    # caminata), "bajarse de la troncal A para caminar" y "de la caminata
    # montarse en la troncal B" se cobrarian como DOS transbordos en vez
    # de UNO solo (ver contar_transbordos()).
    estado_inicial = (origen, None)

    costo_acumulado = {estado_inicial: 0.0}
    nodo_padre = {estado_inicial: None}
    # Troncal REAL del tramo (bus o INTEGRACION) con el que se llego a
    # cada estado, solo para poder reconstruir la ruta al final (mostrar
    # por que troncal se viaja en cada tramo). No es parte del estado de
    # busqueda: ver la nota de estado_inicial arriba.
    edge_troncal_usado = {}
    visitados = set()

    # Se usa un contador como segundo criterio de orden en la cola de
    # prioridad. Sin el, si dos estados llegaran a tener EXACTAMENTE la
    # misma prioridad, Python intentaria comparar los estados entre si
    # (estacion, troncal) y podria fallar al comparar None con texto.
    # Es un detalle tecnico de heapq, no una regla del algoritmo.
    contador_de_desempate = itertools.count()
    cola_de_prioridad = [
        (_heuristica_min(origen, destino), next(contador_de_desempate), estado_inicial)
    ]

    while cola_de_prioridad:
        _, _, estado_actual = heapq.heappop(cola_de_prioridad)

        if estado_actual in visitados:
            continue
        visitados.add(estado_actual)

        estacion_actual, ultima_troncal_real = estado_actual
        if estacion_actual == destino:
            return _reconstruir_resultado(
                nodo_padre, edge_troncal_usado, estado_actual, costo_acumulado[estado_actual]
            )

        for vecino, troncal_del_tramo, distancia_km in grafo.get(estacion_actual, []):
            costo_del_tramo = _tiempo_del_tramo_min(distancia_km, troncal_del_tramo)

            if troncal_del_tramo == INTEGRACION:
                # Caminar no es "abordar un bus distinto": no se cobra
                # aqui la penalizacion de transbordo (ese costo ya esta
                # reflejado en que se camina mas despacio que un bus, ver
                # VELOCIDAD_INTEGRACION_KMH). La troncal real con la que
                # se viene NO cambia: seguimos "en transicion" desde el
                # ultimo bus real hasta que abordemos otro.
                hay_transbordo = False
                nueva_ultima_troncal_real = ultima_troncal_real
            else:
                # Solo se cobra penalizacion de transbordo si YA se venia
                # usando una troncal real (ultima_troncal_real no es
                # None) Y esa troncal es distinta de la que se va a
                # tomar ahora. Si en el medio hubo un tramo de
                # INTEGRACION caminado, ultima_troncal_real sigue siendo
                # la de ANTES de caminar (ver arriba), asi que aqui se
                # cobra UN solo transbordo por todo el evento "me bajo,
                # camino, me subo a otro bus", no dos.
                hay_transbordo = (
                    ultima_troncal_real is not None and ultima_troncal_real != troncal_del_tramo
                )
                nueva_ultima_troncal_real = troncal_del_tramo

            if hay_transbordo:
                costo_del_tramo += PENALIZACION_TRANSBORDO_MIN

            nuevo_estado = (vecino, nueva_ultima_troncal_real)
            nuevo_costo_acumulado = costo_acumulado[estado_actual] + costo_del_tramo

            si_no_se_conocia = nuevo_estado not in costo_acumulado
            si_se_encontro_algo_mejor = (
                not si_no_se_conocia and nuevo_costo_acumulado < costo_acumulado[nuevo_estado]
            )

            if si_no_se_conocia or si_se_encontro_algo_mejor:
                costo_acumulado[nuevo_estado] = nuevo_costo_acumulado
                nodo_padre[nuevo_estado] = estado_actual
                edge_troncal_usado[nuevo_estado] = troncal_del_tramo
                prioridad = nuevo_costo_acumulado + _heuristica_min(vecino, destino)
                heapq.heappush(
                    cola_de_prioridad,
                    (prioridad, next(contador_de_desempate), nuevo_estado),
                )

    raise RutaImposibleError(
        f"No se encontro ningun camino entre '{origen}' y '{destino}' con los datos actuales."
    )
