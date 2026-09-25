# -*- coding: utf-8 -*-
"""
interfaz.py
===========
Interfaz grafica del proyecto, hecha SOLO con Tkinter (viene incluido con
Python: no hay que instalar nada con pip). Se ejecuta con:

    python interfaz.py

Por que Tkinter y no otra libreria (por ejemplo PyQt o una pagina web con
Flask): el enunciado del proyecto exige que tres companeros y la docente
puedan ejecutar esto en computadores distintos SIN instalar nada. Tkinter
viene incluido en la instalacion estandar de Python en Windows, Linux y
macOS, asi que es la unica opcion que garantiza "cero dependencias".

Este archivo NO tiene logica de sistema experto ni de busqueda: solo
dibuja pantalla y le pasa los datos a las funciones que YA existen en
los otros modulos. La regla de oro que pidio el enunciado es "no
duplicar logica", asi que aqui:
  - base_conocimiento.py  da los nombres, coordenadas y colores de troncal.
  - motor_reglas.py       dice cuales estaciones son de transbordo.
  - busqueda.py           calcula la ruta (A*) y donde ocurre cada transbordo.
  - main.py               ya sabe como arrancar el sistema completo
                           (motor de reglas + grafo); interfaz.py reutiliza
                           esa misma funcion en vez de repetirla.

Como esta organizada la ventana:
  - Arriba: dos desplegables (origen y destino) y el boton "Buscar ruta".
  - A la izquierda: un Canvas con el mapa de las 43 estaciones, dibujado
    a partir de sus coordenadas reales (latitud/longitud) proyectadas a
    pixeles.
  - A la derecha: la leyenda de colores y el resultado de la busqueda en
    texto (la secuencia de estaciones, los transbordos y el tiempo).
"""

import math
import tkinter as tk
from tkinter import messagebox, ttk

from base_conocimiento import (
    AMERICAS,
    AUTOPISTA_NORTE,
    CALLE_80,
    CARACAS,
    EJE_AMBIENTAL_CALLE_26,
    ESTACIONES,
    HECHOS_CONECTA,
    INTEGRACION,
    NOMBRE_VISIBLE,
    NOMBRE_VISIBLE_TRONCAL,
    NQS,
    SUBA,
)
from busqueda import (
    EstacionInexistenteError,
    RutaImposibleError,
    buscar_mejor_ruta,
    ubicaciones_de_transbordo,
)
from main import construir_grafo_del_sistema
from motor_reglas import obtener_estaciones_transbordo


# ---------------------------------------------------------------------
# Constantes de dibujo
# ---------------------------------------------------------------------
# Un color distinto por troncal, para que el mapa se pueda leer de un
# vistazo (y para la leyenda). Son colores fijos, no hace falta ninguna
# libreria de graficos para definirlos: Tkinter entiende directamente
# cadenas de texto como "#e6194b" o nombres como "red".
COLOR_POR_TRONCAL = {
    AUTOPISTA_NORTE: "#e6194b",
    CARACAS: "#3cb44b",
    EJE_AMBIENTAL_CALLE_26: "#4363d8",
    NQS: "#f58231",
    AMERICAS: "#911eb4",
    CALLE_80: "#009e94",
    SUBA: "#f032e6",
}
COLOR_INTEGRACION = "#999999"   # gris: conexion peatonal estimada, no una troncal real
COLOR_ESTACION_NORMAL = "#333333"
COLOR_RUTA = "#000000"         # la ruta encontrada se resalta en negro grueso
COLOR_ORIGEN = "#1a9850"       # verde
COLOR_DESTINO = "#d73027"      # rojo
COLOR_TRANSBORDO_EN_RUTA = "#ffcc00"  # amarillo: donde ocurre un transbordo de la ruta

# Tamano de ventana pensado para que quepa comodo en un portatil normal
# (1366x768), dejando espacio para la barra de tareas de Windows.
ANCHO_VENTANA = 1300
ALTO_VENTANA = 720

ANCHO_CANVAS = 830
ALTO_CANVAS = 610
MARGEN_MAPA = 30

RADIO_ESTACION_NORMAL = 3
RADIO_ESTACION_TRANSBORDO = 6
GROSOR_LINEA_TRONCAL = 2
GROSOR_LINEA_RUTA = 4

TEXTO_SELECCIONE = "-- seleccione --"


class VentanaTransMilenio:
    """
    Una sola clase con toda la interfaz. Se usa una clase (y no puras
    funciones sueltas) porque varios botones y dibujos necesitan
    compartir el mismo estado (por ejemplo, el Canvas y el grafo ya
    calculado), y en Tkinter la forma normal de compartir ese estado
    entre callbacks es guardandolo como atributos de self.
    """

    def __init__(self, raiz):
        self.raiz = raiz
        self.raiz.title("Rutas TransMilenio - Sistema experto + busqueda A*")
        self.raiz.geometry(f"{ANCHO_VENTANA}x{ALTO_VENTANA}")
        self.raiz.minsize(1024, 650)

        # ---- 1) Arrancar el "cerebro" del sistema UNA sola vez -------
        # Se reutiliza la misma funcion que usa main.py (la version de
        # consola) para no repetir la logica de arranque: correr el
        # motor de reglas y armar el grafo de busqueda.
        self.hechos_derivados, self.grafo = construir_grafo_del_sistema(mostrar_progreso=False)

        # Las estaciones de transbordo NO estan escritas a mano en
        # ninguna parte: las descubrio el motor de reglas (regla R2) a
        # partir de los hechos. Aqui solo se le pregunta el resultado.
        self.estaciones_transbordo = obtener_estaciones_transbordo(self.hechos_derivados)

        # ---- 2) Preparar los nombres para los desplegables -----------
        # NOMBRE_VISIBLE mapea id_interno -> nombre bonito (por ejemplo
        # "Av_Jimenez" -> "Av. Jimenez"). Para los desplegables se
        # necesita el camino inverso (del nombre bonito al id interno),
        # por eso se arma este diccionario invertido una sola vez aqui.
        self.nombre_a_id = {nombre: id_est for id_est, nombre in NOMBRE_VISIBLE.items()}
        self.nombres_ordenados = sorted(self.nombre_a_id.keys())

        # ---- 3) Convertir lat/lon a pixeles del Canvas ----------------
        self.puntos_canvas = self._proyectar_estaciones_a_pixeles()

        # ---- 4) Construir la pantalla ---------------------------------
        self._construir_controles_superiores()
        self._construir_panel_principal()
        self._dibujar_mapa_base()

    # -------------------------------------------------------------
    # Proyeccion geografica: de (latitud, longitud) a (x, y) en pantalla
    # -------------------------------------------------------------
    def _proyectar_estaciones_a_pixeles(self):
        """
        Convierte las coordenadas reales de las 43 estaciones a
        coordenadas de pantalla (pixeles dentro del Canvas), guardando
        la forma real del mapa lo mejor posible.

        Dos detalles importantes:
        1. En la pantalla el eje Y crece hacia ABAJO, pero la latitud
           crece hacia el NORTE (arriba). Por eso, al calcular "y", se
           usa (lat_maxima - lat) en vez de (lat - lat_minima): asi la
           estacion mas al norte queda arriba en el dibujo.
        2. Un grado de longitud, a la altura de Bogota, mide un poco
           MENOS en el mundo real que un grado de latitud (los
           meridianos se van juntando entre si al alejarse del
           ecuador). Se corrige multiplicando la diferencia de longitud
           por el coseno de la latitud promedio, exactamente la misma
           idea que usa la formula de Haversine en busqueda.py. Sin
           esta correccion el mapa saldria "estirado" de este a oeste.
        """
        latitudes = [lat for lat, lon in ESTACIONES.values()]
        longitudes = [lon for lat, lon in ESTACIONES.values()]
        lat_min, lat_max = min(latitudes), max(latitudes)
        lon_min, lon_max = min(longitudes), max(longitudes)

        lat_promedio_rad = math.radians((lat_min + lat_max) / 2)
        factor_correccion_longitud = math.cos(lat_promedio_rad)

        ancho_geografico = (lon_max - lon_min) * factor_correccion_longitud
        alto_geografico = lat_max - lat_min

        ancho_disponible = ANCHO_CANVAS - 2 * MARGEN_MAPA
        alto_disponible = ALTO_CANVAS - 2 * MARGEN_MAPA

        # Se usa la MISMA escala para X y para Y (min de las dos
        # posibles), para que el mapa no salga deformado: un cuadrado en
        # la realidad debe verse como un cuadrado en pantalla, no como
        # un rectangulo.
        escala = min(
            ancho_disponible / ancho_geografico if ancho_geografico else 1,
            alto_disponible / alto_geografico if alto_geografico else 1,
        )

        # Como el mapa geografico casi nunca llena exactamente el
        # rectangulo disponible, se centra el dibujo sumando la mitad
        # del espacio que sobra en cada eje.
        ancho_usado = ancho_geografico * escala
        alto_usado = alto_geografico * escala
        desplazamiento_x = MARGEN_MAPA + (ancho_disponible - ancho_usado) / 2
        desplazamiento_y = MARGEN_MAPA + (alto_disponible - alto_usado) / 2

        puntos = {}
        for id_estacion, (lat, lon) in ESTACIONES.items():
            x = desplazamiento_x + (lon - lon_min) * factor_correccion_longitud * escala
            y = desplazamiento_y + (lat_max - lat) * escala
            puntos[id_estacion] = (x, y)
        return puntos

    # -------------------------------------------------------------
    # Construccion de la pantalla
    # -------------------------------------------------------------
    def _construir_controles_superiores(self):
        """Fila de arriba: desplegable de origen, de destino, y el boton de buscar."""
        marco_superior = ttk.Frame(self.raiz, padding=10)
        marco_superior.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(marco_superior, text="Estacion de origen:").grid(row=0, column=0, padx=5, sticky="w")
        self.combo_origen = ttk.Combobox(
            marco_superior, values=self.nombres_ordenados, state="readonly", width=28
        )
        self.combo_origen.grid(row=0, column=1, padx=5)
        self.combo_origen.set(TEXTO_SELECCIONE)

        ttk.Label(marco_superior, text="Estacion de destino:").grid(row=0, column=2, padx=5, sticky="w")
        self.combo_destino = ttk.Combobox(
            marco_superior, values=self.nombres_ordenados, state="readonly", width=28
        )
        self.combo_destino.grid(row=0, column=3, padx=5)
        self.combo_destino.set(TEXTO_SELECCIONE)

        boton_buscar = ttk.Button(marco_superior, text="Buscar ruta", command=self._al_hacer_clic_buscar)
        boton_buscar.grid(row=0, column=4, padx=15)

        # Un mensaje de error o exito breve, cerca de los controles, para
        # que sea lo primero que el usuario ve si algo sale mal. Ademas
        # de esto se usa un messagebox para errores mas serios (ver
        # _al_hacer_clic_buscar), pero esta etiqueta evita que el usuario
        # tenga que cerrar un cuadro de dialogo para leer el problema.
        self.etiqueta_estado = ttk.Label(marco_superior, text="", foreground="#a00000")
        self.etiqueta_estado.grid(row=1, column=0, columnspan=5, sticky="w", pady=(8, 0))

    def _construir_panel_principal(self):
        """Debajo de los controles: el mapa (Canvas) a la izquierda y el resultado a la derecha."""
        marco_principal = ttk.Frame(self.raiz, padding=(10, 0, 10, 10))
        marco_principal.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(
            marco_principal, width=ANCHO_CANVAS, height=ALTO_CANVAS, bg="white",
            highlightthickness=1, highlightbackground="#cccccc",
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        marco_lateral = ttk.Frame(marco_principal, padding=(10, 0, 0, 0))
        marco_lateral.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)

        ttk.Label(marco_lateral, text="Leyenda de troncales", font=("TkDefaultFont", 10, "bold")).pack(
            anchor="w"
        )
        self._construir_leyenda(marco_lateral)

        ttk.Separator(marco_lateral, orient="horizontal").pack(fill=tk.X, pady=10)

        ttk.Label(marco_lateral, text="Resultado de la busqueda", font=("TkDefaultFont", 10, "bold")).pack(
            anchor="w"
        )

        # Un Text normal (no hace falta scrolledtext, que ni siquiera es
        # parte del paquete base de tkinter en todas las instalaciones)
        # mas una barra de desplazamiento manual, por si la ruta es larga
        # y el texto no cabe completo en pantalla.
        marco_texto = ttk.Frame(marco_lateral)
        marco_texto.pack(fill=tk.BOTH, expand=True)

        barra_desplazamiento = ttk.Scrollbar(marco_texto, orient="vertical")
        barra_desplazamiento.pack(side=tk.RIGHT, fill=tk.Y)

        self.texto_resultado = tk.Text(
            marco_texto, width=42, wrap="word", font=("Consolas", 10),
            yscrollcommand=barra_desplazamiento.set, state="disabled",
        )
        self.texto_resultado.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        barra_desplazamiento.config(command=self.texto_resultado.yview)

        self._mostrar_texto("Elija una estacion de origen y una de destino, y presione 'Buscar ruta'.")

    def _construir_leyenda(self, contenedor):
        """Un cuadrito de color y el nombre de cada troncal, mas los simbolos del mapa."""
        for troncal, color in COLOR_POR_TRONCAL.items():
            fila = ttk.Frame(contenedor)
            fila.pack(fill=tk.X, pady=1)
            lienzo_color = tk.Canvas(fila, width=16, height=10, highlightthickness=0)
            lienzo_color.create_rectangle(0, 0, 16, 10, fill=color, outline=color)
            lienzo_color.pack(side=tk.LEFT, padx=(0, 6))
            ttk.Label(fila, text=NOMBRE_VISIBLE_TRONCAL[troncal]).pack(side=tk.LEFT)

        fila_integracion = ttk.Frame(contenedor)
        fila_integracion.pack(fill=tk.X, pady=(4, 1))
        lienzo_integracion = tk.Canvas(fila_integracion, width=16, height=10, highlightthickness=0)
        lienzo_integracion.create_line(0, 5, 16, 5, fill=COLOR_INTEGRACION, width=2, dash=(3, 2))
        lienzo_integracion.pack(side=tk.LEFT, padx=(0, 6))
        ttk.Label(fila_integracion, text="Integracion (caminata estimada)").pack(side=tk.LEFT)

        fila_transbordo = ttk.Frame(contenedor)
        fila_transbordo.pack(fill=tk.X, pady=(4, 1))
        lienzo_transbordo = tk.Canvas(fila_transbordo, width=16, height=16, highlightthickness=0)
        lienzo_transbordo.create_oval(3, 3, 13, 13, fill="white", outline="black", width=2)
        lienzo_transbordo.pack(side=tk.LEFT, padx=(0, 6))
        ttk.Label(fila_transbordo, text="Estacion de transbordo (derivada por el motor)").pack(side=tk.LEFT)

    # -------------------------------------------------------------
    # Dibujo del mapa
    # -------------------------------------------------------------
    def _dibujar_mapa_base(self):
        """
        Dibuja, una sola vez al arrancar, las conexiones entre
        estaciones y los puntos de cada estacion. Esto NO se vuelve a
        redibujar en cada busqueda: solo se le agrega encima el
        resaltado de la ruta (ver _resaltar_ruta), asi que aqui se
        pueden usar "tags" (etiquetas) de Canvas para poder borrar mas
        tarde unicamente el resaltado, sin tener que rehacer el mapa
        completo.
        """
        # Las conexiones se leen directo de HECHOS_CONECTA (los hechos
        # ORIGINALES de la base de conocimiento, antes de que el motor
        # de reglas derive el sentido contrario): para DIBUJAR el mapa
        # alcanza con una linea por cada tramo real, no hace falta
        # dibujarla dos veces (una por cada sentido).
        for hecho in HECHOS_CONECTA:
            origen, destino, troncal = hecho.argumentos
            x1, y1 = self.puntos_canvas[origen]
            x2, y2 = self.puntos_canvas[destino]
            if troncal == INTEGRACION:
                self.canvas.create_line(
                    x1, y1, x2, y2, fill=COLOR_INTEGRACION, width=GROSOR_LINEA_TRONCAL,
                    dash=(4, 3), tags=("mapa_base",),
                )
            else:
                self.canvas.create_line(
                    x1, y1, x2, y2, fill=COLOR_POR_TRONCAL[troncal], width=GROSOR_LINEA_TRONCAL,
                    tags=("mapa_base",),
                )

        # Los puntos de estacion se dibujan DESPUES de las lineas para
        # que queden por encima (Canvas dibuja en el orden en que se
        # crean las cosas, como capas de una torta).
        for id_estacion, (x, y) in self.puntos_canvas.items():
            es_transbordo = id_estacion in self.estaciones_transbordo
            radio = RADIO_ESTACION_TRANSBORDO if es_transbordo else RADIO_ESTACION_NORMAL
            color_relleno = "white" if es_transbordo else COLOR_ESTACION_NORMAL
            grosor_borde = 2 if es_transbordo else 1
            self.canvas.create_oval(
                x - radio, y - radio, x + radio, y + radio,
                fill=color_relleno, outline="black", width=grosor_borde,
                tags=("mapa_base", f"estacion_{id_estacion}"),
            )

    def _resaltar_ruta(self, resultado):
        """
        Dibuja la ruta encontrada ENCIMA del mapa base: una linea gruesa
        que sigue la secuencia de estaciones, un marcador verde en el
        origen, uno rojo en el destino, y un punto amarillo en cada
        estacion donde ocurre un transbordo real.
        """
        # Primero se borra el resaltado de la busqueda anterior (si la
        # habia). El mapa base tiene su propio tag distinto
        # ("mapa_base"), asi que borrar "resaltado_ruta" nunca toca las
        # troncales ni las estaciones ya dibujadas.
        self.canvas.delete("resaltado_ruta")

        estaciones = resultado.estaciones
        if len(estaciones) >= 2:
            puntos_de_la_linea = []
            for id_estacion in estaciones:
                x, y = self.puntos_canvas[id_estacion]
                puntos_de_la_linea.extend([x, y])
            self.canvas.create_line(
                *puntos_de_la_linea, fill=COLOR_RUTA, width=GROSOR_LINEA_RUTA,
                capstyle=tk.ROUND, joinstyle=tk.ROUND, tags=("resaltado_ruta",),
            )

        # Estaciones donde el pasajero realmente transborda (reutiliza
        # busqueda.ubicaciones_de_transbordo: la misma funcion que se usa
        # para el texto del panel lateral, para no calcular esto dos
        # veces de dos formas distintas que podrian desacuerdarse).
        for id_estacion, _troncal_desde, _troncal_hacia in ubicaciones_de_transbordo(resultado):
            x, y = self.puntos_canvas[id_estacion]
            radio = RADIO_ESTACION_TRANSBORDO + 3
            self.canvas.create_oval(
                x - radio, y - radio, x + radio, y + radio,
                outline=COLOR_TRANSBORDO_EN_RUTA, width=3, tags=("resaltado_ruta",),
            )

        # Origen y destino se marcan al final para que queden siempre
        # visibles por encima de todo lo demas.
        x_origen, y_origen = self.puntos_canvas[estaciones[0]]
        self.canvas.create_oval(
            x_origen - 8, y_origen - 8, x_origen + 8, y_origen + 8,
            outline=COLOR_ORIGEN, width=3, tags=("resaltado_ruta",),
        )
        x_destino, y_destino = self.puntos_canvas[estaciones[-1]]
        self.canvas.create_rectangle(
            x_destino - 7, y_destino - 7, x_destino + 7, y_destino + 7,
            outline=COLOR_DESTINO, width=3, tags=("resaltado_ruta",),
        )

    # -------------------------------------------------------------
    # Logica del boton "Buscar ruta"
    # -------------------------------------------------------------
    def _al_hacer_clic_buscar(self):
        """
        Se ejecuta cuando el usuario presiona el boton. Todo el manejo
        de errores esta aqui: la idea es que NINGUN error termine en una
        traza de Python en la consola, siempre en un mensaje entendible
        dentro de la misma ventana (con messagebox o con la etiqueta de
        estado de arriba).
        """
        self._limpiar_mensaje_de_estado()

        nombre_origen = self.combo_origen.get()
        nombre_destino = self.combo_destino.get()

        if nombre_origen == TEXTO_SELECCIONE or nombre_destino == TEXTO_SELECCIONE:
            self._mostrar_error("Debe elegir una estacion de origen y una de destino.")
            return

        if nombre_origen == nombre_destino:
            self._mostrar_error("El origen y el destino no pueden ser la misma estacion.")
            return

        id_origen = self.nombre_a_id[nombre_origen]
        id_destino = self.nombre_a_id[nombre_destino]

        try:
            resultado = buscar_mejor_ruta(self.grafo, id_origen, id_destino)
        except EstacionInexistenteError as error:
            # En teoria no deberia pasar nunca (los desplegables solo
            # ofrecen estaciones validas), pero se captura de todas
            # formas: es mejor un mensaje claro que una excepcion sin
            # controlar si algo cambiara en el futuro.
            self._mostrar_error(str(error))
            return
        except RutaImposibleError as error:
            self._mostrar_error(str(error))
            return
        except Exception as error:  # noqa: BLE001 - ver comentario abajo
            # Cualquier otro error inesperado (que no deberia ocurrir)
            # tambien se atrapa aqui: el requisito explicito del
            # enunciado es que el usuario NUNCA vea una traza de Python
            # en la consola, sin importar que salga mal.
            self._mostrar_error(f"Ocurrio un error inesperado: {error}")
            return

        self._resaltar_ruta(resultado)
        self._mostrar_resultado_texto(resultado)

    def _mostrar_error(self, mensaje):
        self.etiqueta_estado.config(text=mensaje)
        messagebox.showerror("No se pudo calcular la ruta", mensaje)

    def _limpiar_mensaje_de_estado(self):
        self.etiqueta_estado.config(text="")

    def _mostrar_resultado_texto(self, resultado):
        """Arma el texto del panel lateral con la ruta, los transbordos y el tiempo."""
        lineas = []
        lineas.append("Ruta encontrada:")
        for indice, id_estacion in enumerate(resultado.estaciones, start=1):
            lineas.append(f"  {indice}. {NOMBRE_VISIBLE[id_estacion]}")

        lineas.append("")
        lineas.append(f"Estaciones en la ruta : {len(resultado.estaciones)}")
        lineas.append(f"Transbordos           : {resultado.num_transbordos}")
        lineas.append(f"Tiempo estimado       : {resultado.tiempo_total_min:.1f} minutos")

        ubicaciones = ubicaciones_de_transbordo(resultado)
        if ubicaciones:
            lineas.append("")
            lineas.append("Donde ocurre cada transbordo:")
            for id_estacion, troncal_desde, troncal_hacia in ubicaciones:
                nombre_estacion = NOMBRE_VISIBLE[id_estacion]
                nombre_desde = NOMBRE_VISIBLE_TRONCAL[troncal_desde]
                nombre_hacia = NOMBRE_VISIBLE_TRONCAL[troncal_hacia]
                lineas.append(f"  - En {nombre_estacion}: {nombre_desde} -> {nombre_hacia}")
        elif resultado.num_transbordos == 0:
            lineas.append("")
            lineas.append("No hace falta transbordar: toda la ruta va en la misma troncal.")

        self._mostrar_texto("\n".join(lineas))

    def _mostrar_texto(self, texto):
        """
        El widget Text de Tkinter se deja en state='disabled' para que
        el usuario no pueda escribir encima del resultado por
        accidente. Por eso, para CAMBIAR el texto, hay que habilitarlo
        un instante, borrar y escribir, y volver a deshabilitarlo.
        """
        self.texto_resultado.config(state="normal")
        self.texto_resultado.delete("1.0", tk.END)
        self.texto_resultado.insert(tk.END, texto)
        self.texto_resultado.config(state="disabled")


def main():
    raiz = tk.Tk()
    VentanaTransMilenio(raiz)
    raiz.mainloop()


if __name__ == "__main__":
    main()
