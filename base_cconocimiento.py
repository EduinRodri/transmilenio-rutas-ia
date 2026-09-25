
"""
base_conocimiento.py
=====================
Este modulo es la BASE DE CONOCIMIENTO del sistema experto: aqui no hay
ningun algoritmo, solo HECHOS. Un hecho es una afirmacion que el sistema
da por verdadera (por ejemplo: "la estacion Heroes esta en la troncal
Autopista Norte"). El motor de reglas (motor_reglas.py) es quien despues
usa estos hechos para derivar hechos nuevos, y busqueda.py es quien usa
todo eso para calcular rutas.

Por que esta separado en su propio archivo: en un sistema experto real, la
base de conocimiento (los hechos) y el motor de inferencia (como se
razona con ellos) son piezas independientes a proposito. Se supone que se
podria cambiar por completo el mapa de estaciones sin tocar ni una linea
del motor de reglas ni de la busqueda. Esa separacion es justamente lo que
pide la bibliografia de la materia (Benitez, 2014, cap. 2 y 3).

De donde salen los datos (IMPORTANTE para poder defender esto en video):
---------------------------------------------------------------------
Los NOMBRES y las COORDENADAS (latitud/longitud) de las 43 estaciones que
se usan aqui salen del conjunto de datos oficial y abierto "Estaciones
Troncales de TRANSMILENIO", publicado por TransMilenio S.A. en el portal
Datos Abiertos Bogota:
    https://datosabiertos.bogota.gov.co/dataset/estaciones-troncales-de-transmilenio
(descargado en formato GeoJSON el 20 de septiembre de 2026).

A partir de ese archivo oficial se tomaron 43 estaciones reales de 7
troncales (de las cerca de 150 que tiene el sistema completo) para que el
proyecto sea manejable en un trabajo de curso. Sobre esos datos se
hicieron estas DECISIONES DE DISENO, que hay que poder explicar:

1. Los nombres se simplificaron quitando el patrocinador comercial que
   aparece en el dataset oficial (por ejemplo, el dato original dice
   "Heroes - Colmena Seguros"; aqui se deja solo "Heroes", porque el
   patrocinio cambia con el tiempo y no es parte real del nombre de la
   estacion).

2. Las coordenadas SI son las oficiales (solo se redondearon a 5
   decimales, un margen de error de unos 11 metros, mas que suficiente
   para este ejercicio).

3. Ricaurte es, en la realidad, un unico gran intercambiador con dos
   plataformas fisicas separadas por unos 400 metros ("Ricaurte - NQS" y
   "Ricaurte - CL 13" en el dataset oficial). Aqui se modela como UNA sola
   estacion (con las coordenadas promedio de las dos plataformas) porque
   para efectos de esta tarea son el mismo punto de transbordo entre la
   troncal NQS y la troncal Americas.

4. Las CONEXIONES ENTRE ESTACIONES CONSECUTIVAS de una misma troncal
   (cual estacion sigue a cual) se reconstruyeron ordenando las
   estaciones reales por su posicion geografica a lo largo del corredor,
   porque el dataset de estaciones no trae el orden de las paradas. Esto
   es una aproximacion razonable, no el orden oficial verificado tramo
   por tramo, y hay que decirlo asi si preguntan.

5. El sistema real de TransMilenio conecta TODAS sus troncales entre si
   (es una sola red). Modelar cada conexion oficial de transbordo entre
   las 12 troncales reales se sale del alcance de este trabajo. Para que
   el grafo de este proyecto quede conectado de un extremo a otro (que es
   lo que pide el enunciado: "moverse desde un punto A a un punto B en el
   sistema"), se agregaron 3 conexiones marcadas explicitamente como
   "INTEGRACION": representan una caminata corta entre dos estaciones
   reales cercanas de troncales distintas, NO un transbordo oficial
   verificado. Se listan mas abajo y tambien en el README.

Estaciones de TRANSBORDO real (perteneces a mas de una troncal oficial):
Heroes (Autopista Norte / Caracas), Av. Jimenez (Caracas / Eje Ambiental)
y Ricaurte (NQS / Americas). El motor de reglas las vuelve a descubrir
solas a partir de los hechos "estacion_en" (no estan escritas a mano en
ninguna parte como "es_estacion_transbordo"): eso es exactamente lo que
prueba que el motor de inferencia funciona.
"""

from collections import namedtuple


# ---------------------------------------------------------------------
# Que es un "Hecho"
# ---------------------------------------------------------------------
# Un Hecho tiene un predicado (el nombre de la relacion, como "conecta" o
# "estacion_en") y una tupla de argumentos. Usamos una tupla con nombre en
# vez de una lista porque un hecho no se modifica una vez creado: si algo
# cambia, lo que se hace es DERIVAR un hecho nuevo (eso lo hace el motor
# de reglas), no editar uno existente.
_DatosHecho = namedtuple("_DatosHecho", ["predicado", "argumentos"])


def Hecho(predicado, *argumentos):
    """
    Crea un hecho. Ejemplo de uso, igual al que pide el enunciado:
        Hecho("conecta", "Av_Jimenez", "Calle_19", "Caracas")
    Se escribe como funcion (con mayuscula, como si fuera una clase) para
    que a la hora de leer la base de conocimiento se lea casi como
    logica de primer orden: Hecho(predicado, argumento1, argumento2, ...).
    """
    return _DatosHecho(predicado, tuple(argumentos))


# ---------------------------------------------------------------------
# Nombres de las troncales usadas en este proyecto
# ---------------------------------------------------------------------
# Se usan como simples cadenas de texto (no una clase aparte) porque en
# esta base de conocimiento una troncal no necesita comportamiento propio,
# solo un identificador. "INTEGRACION" no es una troncal real: marca las
# conexiones peatonales estimadas explicadas arriba (punto 5).
AUTOPISTA_NORTE = "Autopista_Norte"
CARACAS = "Caracas"
EJE_AMBIENTAL_CALLE_26 = "Eje_Ambiental_Calle_26"
NQS = "NQS"
AMERICAS = "Americas"
CALLE_80 = "Calle_80"
SUBA = "Suba"
INTEGRACION = "INTEGRACION"

# Nombre bonito de cada troncal, solo para mostrar en pantalla.
NOMBRE_VISIBLE_TRONCAL = {
    AUTOPISTA_NORTE: "Autopista Norte",
    CARACAS: "Caracas",
    EJE_AMBIENTAL_CALLE_26: "Eje Ambiental / Calle 26",
    NQS: "NQS (Norte - Quito - Sur)",
    AMERICAS: "Americas",
    CALLE_80: "Calle 80",
    SUBA: "Suba",
    INTEGRACION: "Conexion de integracion (caminata estimada)",
}


# ---------------------------------------------------------------------
# Coordenadas reales de las 43 estaciones (latitud, longitud)
# ---------------------------------------------------------------------
# Fuente: Datos Abiertos Bogota / TransMilenio S.A. (ver docstring del
# modulo). El identificador (la llave del diccionario) es el nombre
# interno que usa el programa; NOMBRE_VISIBLE (mas abajo) tiene el nombre
# bonito para mostrarle al usuario.
ESTACIONES = {
    # --- Troncal Autopista Norte (sur -> norte) ---
    "Heroes": (4.66814, -74.06031),
    "Calle_85": (4.67231, -74.05964),
    "Calle_100": (4.68395, -74.05771),
    "Prado": (4.71456, -74.05256),
    "Calle_146": (4.73089, -74.04981),
    "Toberin": (4.74618, -74.04725),
    "Portal_Norte": (4.75462, -74.04604),

    # --- Troncal Caracas (norte -> sur, arranca en Heroes) ---
    "Calle_76": (4.66303, -74.06126),
    "Calle_72": (4.65824, -74.06207),
    "Calle_63": (4.64840, -74.06487),
    "Calle_45": (4.63145, -74.06788),
    "Av_Jimenez": (4.60305, -74.07909),

    # --- Troncal Eje Ambiental / Calle 26 (este -> oeste) ---
    "Las_Aguas": (4.60258, -74.06840),
    "Museo_Del_Oro": (4.60115, -74.07291),
    "De_La_Sabana": (4.60542, -74.08189),
    "CAD": (4.62342, -74.08418),
    "CAN": (4.64688, -74.09905),
    "Salitre": (4.65086, -74.10165),
    "Portal_El_Dorado": (4.68162, -74.12140),

    # --- Troncal NQS (norte -> sur) ---
    "AV_Chile": (4.66635, -74.07457),
    "Movistar_Arena": (4.65004, -74.07836),
    "Universidad_Nacional": (4.63712, -74.07933),
    "Ricaurte": (4.61235, -74.09217),  # promedio de las 2 plataformas reales (ver docstring)
    "Comuneros": (4.60425, -74.09986),
    "Santa_Isabel": (4.60168, -74.10262),

    # --- Troncal Americas (este -> oeste, arranca en Ricaurte) ---
    "CDS": (4.61614, -74.09395),
    "Carrera_43": (4.62278, -74.10144),
    "Distrito_Grafiti": (4.62785, -74.11158),
    "Marsella": (4.62968, -74.13016),
    "Banderas": (4.63129, -74.14577),
    "Portal_Americas": (4.62938, -74.17306),

    # --- Troncal Calle 80 (este -> oeste) ---
    "Polo": (4.67016, -74.06434),
    "Escuela_Militar": (4.67554, -74.06980),
    "AV_68": (4.68610, -74.08077),
    "Minuto_De_Dios": (4.69688, -74.09193),
    "Carrera_90": (4.70467, -74.10457),
    "Portal_80": (4.70983, -74.11051),

    # --- Troncal Suba (sur -> norte) ---
    "Suba_Calle_100": (4.68697, -74.06444),
    "Puentelargo": (4.69340, -74.06721),
    "Niza": (4.71200, -74.07231),
    "Suba_AV_Boyaca": (4.72127, -74.07471),
    "Gratamira": (4.72746, -74.07472),
    "Portal_Suba": (4.74682, -74.09428),
}

# Nombre para mostrar en pantalla de cada estacion (con tildes y formato
# real). Se separa del identificador interno porque el identificador no
# puede tener tildes ni espacios (se usa como llave y como texto en el
# CLI de forma comoda), pero el nombre real de la estacion si los tiene.
NOMBRE_VISIBLE = {
    "Heroes": "Heroes",
    "Calle_85": "Calle 85",
    "Calle_100": "Calle 100",
    "Prado": "Prado",
    "Calle_146": "Calle 146",
    "Toberin": "Toberin",
    "Portal_Norte": "Portal Norte",
    "Calle_76": "Calle 76",
    "Calle_72": "Calle 72",
    "Calle_63": "Calle 63",
    "Calle_45": "Calle 45",
    "Av_Jimenez": "Av. Jimenez",
    "Las_Aguas": "Las Aguas",
    "Museo_Del_Oro": "Museo del Oro",
    "De_La_Sabana": "De La Sabana",
    "CAD": "CAD",
    "CAN": "CAN",
    "Salitre": "Salitre - El Greco",
    "Portal_El_Dorado": "Portal El Dorado",
    "AV_Chile": "Av. Chile",
    "Movistar_Arena": "Movistar Arena",
    "Universidad_Nacional": "Universidad Nacional",
    "Ricaurte": "Ricaurte",
    "Comuneros": "Comuneros",
    "Santa_Isabel": "Santa Isabel",
    "CDS": "CDS - Carrera 32",
    "Carrera_43": "Carrera 43",
    "Distrito_Grafiti": "Distrito Grafiti",
    "Marsella": "Marsella",
    "Banderas": "Banderas",
    "Portal_Americas": "Portal Americas",
    "Polo": "Polo",
    "Escuela_Militar": "Escuela Militar",
    "AV_68": "Av. 68",
    "Minuto_De_Dios": "Minuto de Dios",
    "Carrera_90": "Carrera 90",
    "Portal_80": "Portal 80",
    "Suba_Calle_100": "Suba - Calle 100",
    "Puentelargo": "Puentelargo",
    "Niza": "Niza - Calle 127",
    "Suba_AV_Boyaca": "Suba - Av. Boyaca",
    "Gratamira": "Gratamira",
    "Portal_Suba": "Portal Suba",
}


# ---------------------------------------------------------------------
# Hechos: en que troncal(es) esta cada estacion
# ---------------------------------------------------------------------
# Ojo: Heroes, Av_Jimenez y Ricaurte aparecen DOS veces, una por cada
# troncal a la que pertenecen en la vida real. El motor de reglas usa
# justamente esa repeticion para descubrir que son estaciones de
# transbordo (regla R2 en motor_reglas.py). No se declara en ninguna
# parte "Heroes es transbordo" a mano: eso se DERIVA.
HECHOS_ESTACION_EN = [
    # Autopista Norte
    Hecho("estacion_en", "Heroes", AUTOPISTA_NORTE),
    Hecho("estacion_en", "Calle_85", AUTOPISTA_NORTE),
    Hecho("estacion_en", "Calle_100", AUTOPISTA_NORTE),
    Hecho("estacion_en", "Prado", AUTOPISTA_NORTE),
    Hecho("estacion_en", "Calle_146", AUTOPISTA_NORTE),
    Hecho("estacion_en", "Toberin", AUTOPISTA_NORTE),
    Hecho("estacion_en", "Portal_Norte", AUTOPISTA_NORTE),

    # Caracas (Heroes se repite: es transbordo con Autopista Norte)
    Hecho("estacion_en", "Heroes", CARACAS),
    Hecho("estacion_en", "Calle_76", CARACAS),
    Hecho("estacion_en", "Calle_72", CARACAS),
    Hecho("estacion_en", "Calle_63", CARACAS),
    Hecho("estacion_en", "Calle_45", CARACAS),
    Hecho("estacion_en", "Av_Jimenez", CARACAS),

    # Eje Ambiental / Calle 26 (Av_Jimenez se repite: transbordo con Caracas)
    Hecho("estacion_en", "Av_Jimenez", EJE_AMBIENTAL_CALLE_26),
    Hecho("estacion_en", "Las_Aguas", EJE_AMBIENTAL_CALLE_26),
    Hecho("estacion_en", "Museo_Del_Oro", EJE_AMBIENTAL_CALLE_26),
    Hecho("estacion_en", "De_La_Sabana", EJE_AMBIENTAL_CALLE_26),
    Hecho("estacion_en", "CAD", EJE_AMBIENTAL_CALLE_26),
    Hecho("estacion_en", "CAN", EJE_AMBIENTAL_CALLE_26),
    Hecho("estacion_en", "Salitre", EJE_AMBIENTAL_CALLE_26),
    Hecho("estacion_en", "Portal_El_Dorado", EJE_AMBIENTAL_CALLE_26),

    # NQS
    Hecho("estacion_en", "AV_Chile", NQS),
    Hecho("estacion_en", "Movistar_Arena", NQS),
    Hecho("estacion_en", "Universidad_Nacional", NQS),
    Hecho("estacion_en", "Ricaurte", NQS),
    Hecho("estacion_en", "Comuneros", NQS),
    Hecho("estacion_en", "Santa_Isabel", NQS),

    # Americas (Ricaurte se repite: transbordo con NQS)
    Hecho("estacion_en", "Ricaurte", AMERICAS),
    Hecho("estacion_en", "CDS", AMERICAS),
    Hecho("estacion_en", "Carrera_43", AMERICAS),
    Hecho("estacion_en", "Distrito_Grafiti", AMERICAS),
    Hecho("estacion_en", "Marsella", AMERICAS),
    Hecho("estacion_en", "Banderas", AMERICAS),
    Hecho("estacion_en", "Portal_Americas", AMERICAS),

    # Calle 80
    Hecho("estacion_en", "Polo", CALLE_80),
    Hecho("estacion_en", "Escuela_Militar", CALLE_80),
    Hecho("estacion_en", "AV_68", CALLE_80),
    Hecho("estacion_en", "Minuto_De_Dios", CALLE_80),
    Hecho("estacion_en", "Carrera_90", CALLE_80),
    Hecho("estacion_en", "Portal_80", CALLE_80),

    # Suba
    Hecho("estacion_en", "Suba_Calle_100", SUBA),
    Hecho("estacion_en", "Puentelargo", SUBA),
    Hecho("estacion_en", "Niza", SUBA),
    Hecho("estacion_en", "Suba_AV_Boyaca", SUBA),
    Hecho("estacion_en", "Gratamira", SUBA),
    Hecho("estacion_en", "Portal_Suba", SUBA),
]


# ---------------------------------------------------------------------
# Hechos: conexiones directas entre estaciones consecutivas
# ---------------------------------------------------------------------
# Cada conexion se declara UNA sola vez, en un solo sentido. El motor de
# reglas (regla R1, "bidireccionalidad") es quien deriva el sentido
# contrario. Esto no es solo por ahorrar lineas: demuestra que el motor
# de inferencia realmente hace falta para que la busqueda funcione (si
# alguien borrara la regla R1, la mitad de las rutas dejarian de
# encontrarse).
HECHOS_CONECTA = [
    # Autopista Norte (sur -> norte)
    Hecho("conecta", "Heroes", "Calle_85", AUTOPISTA_NORTE),
    Hecho("conecta", "Calle_85", "Calle_100", AUTOPISTA_NORTE),
    Hecho("conecta", "Calle_100", "Prado", AUTOPISTA_NORTE),
    Hecho("conecta", "Prado", "Calle_146", AUTOPISTA_NORTE),
    Hecho("conecta", "Calle_146", "Toberin", AUTOPISTA_NORTE),
    Hecho("conecta", "Toberin", "Portal_Norte", AUTOPISTA_NORTE),

    # Caracas (norte -> sur, arranca en Heroes)
    Hecho("conecta", "Heroes", "Calle_76", CARACAS),
    Hecho("conecta", "Calle_76", "Calle_72", CARACAS),
    Hecho("conecta", "Calle_72", "Calle_63", CARACAS),
    Hecho("conecta", "Calle_63", "Calle_45", CARACAS),
    Hecho("conecta", "Calle_45", "Av_Jimenez", CARACAS),

    # Eje Ambiental / Calle 26 (este -> oeste)
    Hecho("conecta", "Las_Aguas", "Museo_Del_Oro", EJE_AMBIENTAL_CALLE_26),
    Hecho("conecta", "Museo_Del_Oro", "Av_Jimenez", EJE_AMBIENTAL_CALLE_26),
    Hecho("conecta", "Av_Jimenez", "De_La_Sabana", EJE_AMBIENTAL_CALLE_26),
    Hecho("conecta", "De_La_Sabana", "CAD", EJE_AMBIENTAL_CALLE_26),
    Hecho("conecta", "CAD", "CAN", EJE_AMBIENTAL_CALLE_26),
    Hecho("conecta", "CAN", "Salitre", EJE_AMBIENTAL_CALLE_26),
    Hecho("conecta", "Salitre", "Portal_El_Dorado", EJE_AMBIENTAL_CALLE_26),

    # NQS (norte -> sur)
    Hecho("conecta", "AV_Chile", "Movistar_Arena", NQS),
    Hecho("conecta", "Movistar_Arena", "Universidad_Nacional", NQS),
    Hecho("conecta", "Universidad_Nacional", "Ricaurte", NQS),
    Hecho("conecta", "Ricaurte", "Comuneros", NQS),
    Hecho("conecta", "Comuneros", "Santa_Isabel", NQS),

    # Americas (este -> oeste, arranca en Ricaurte)
    Hecho("conecta", "Ricaurte", "CDS", AMERICAS),
    Hecho("conecta", "CDS", "Carrera_43", AMERICAS),
    Hecho("conecta", "Carrera_43", "Distrito_Grafiti", AMERICAS),
    Hecho("conecta", "Distrito_Grafiti", "Marsella", AMERICAS),
    Hecho("conecta", "Marsella", "Banderas", AMERICAS),
    Hecho("conecta", "Banderas", "Portal_Americas", AMERICAS),

    # Calle 80 (este -> oeste)
    Hecho("conecta", "Polo", "Escuela_Militar", CALLE_80),
    Hecho("conecta", "Escuela_Militar", "AV_68", CALLE_80),
    Hecho("conecta", "AV_68", "Minuto_De_Dios", CALLE_80),
    Hecho("conecta", "Minuto_De_Dios", "Carrera_90", CALLE_80),
    Hecho("conecta", "Carrera_90", "Portal_80", CALLE_80),

    # Suba (sur -> norte)
    Hecho("conecta", "Suba_Calle_100", "Puentelargo", SUBA),
    Hecho("conecta", "Puentelargo", "Niza", SUBA),
    Hecho("conecta", "Niza", "Suba_AV_Boyaca", SUBA),
    Hecho("conecta", "Suba_AV_Boyaca", "Gratamira", SUBA),
    Hecho("conecta", "Gratamira", "Portal_Suba", SUBA),

    # --- Conexiones de INTEGRACION (caminata estimada, ver punto 5 arriba) ---
    # Polo (Calle 80) y Heroes (Autopista Norte / Caracas) quedan a unos
    # 450 m en linea recta.
    Hecho("conecta", "Polo", "Heroes", INTEGRACION),
    # Suba - Calle 100 (Suba) y Calle 100 (Autopista Norte) quedan a
    # unos 350 m en linea recta.
    Hecho("conecta", "Suba_Calle_100", "Calle_100", INTEGRACION),
    # CAD (Eje Ambiental / Calle 26) y CDS - Carrera 32 (Americas) quedan
    # a poco menos de 1.4 km: es la unica conexion que une el grupo
    # {Autopista Norte, Caracas, Eje Ambiental, Calle 80, Suba} con el
    # grupo {NQS, Americas}. Sin ella el grafo quedaria partido en dos.
    Hecho("conecta", "CAD", "CDS", INTEGRACION),
]
