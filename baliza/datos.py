"""Capa de datos y modelos. Todo lo que lee de disco pasa por aqui y se cachea.

Regla de la app: los ficheros del equipo no se tocan. Si un formato cambia, se
adapta en este modulo y ninguna pagina se entera.
"""
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"
MODELOS = RAIZ / "modelos"

sys.path.insert(0, str(RAIZ / "baliza"))

ANIO = 2024

# Ampliacion propia de los corredores del equipo, deducida del fichero de tramos
CORREDORES_EXTRA = DATOS / "corredores_extra.json"
# Catalogo de trayectos con dos formas de ir, para la pantalla de comparacion
COMPARATIVAS = DATOS / "comparativas.json"
# Por debajo de esta parte de kilometros con aforo, una ruta no se declara ganadora
COBERTURA_MINIMA_RUTA = 0.90
# Diferencia de indice por debajo de la cual dos rutas se consideran iguales
EMPATE_INDICE = 8.0

# Un solo formato para todo lo que la app escribe y lee: coma de separador y punto
# decimal, que es el CSV estandar. Lo que se lee es mucho mas tolerante que lo que
# se escribe, porque el usuario pasa el fichero por Excel y vuelve con lo que sea.
SEPARADOR_CSV = ","
DECIMAL_CSV = "."
SEPARADORES_ACEPTADOS = (",", ";", "\t", "|")
# Nombres que se admiten para cada columna del formato por ciudades
ALIAS_COLUMNAS = {
    "origen": ("origen", "desde", "salida", "ciudad_origen", "from"),
    "destino": ("destino", "hasta", "llegada", "ciudad_destino", "to"),
    "paso": ("paso", "via", "por", "pasando_por", "intermedia", "escala"),
    "viajes_semana": ("viajes_semana", "viajes", "frecuencia", "viajes/semana",
                      "viajes_por_semana"),
}

# Modelo de provincias de Miki: coeficientes en JSON y la funcion en
# baliza/predecir_provincia.py, los dos sin modificar.
COEFICIENTES_PROVINCIAS = MODELOS / "coeficientes_provincias.json"
# Mismo corte que el aviso de crecimiento de la funcion de Miki
UMBRAL_CAUTELA = 0.20
# Por debajo de esta parte del trafico medido, el indice provincial se apoya en poca red
UMBRAL_COBERTURA = 0.60
VARIANTES_PROVINCIAS = {
    "pred_naive": ("Repetir el año anterior",
                   "Los accidentes del año anterior, tal cual"),
    "pred_explicativo": ("Explicativo",
                         "Tráfico, región, año y temperatura, sin mirar el año anterior"),
    "pred_predictivo": ("Predictivo",
                        "Lo mismo, más los accidentes del año anterior"),
    "pred_jerarquico": ("Jerárquico (el de esta web)",
                        "El predictivo, con un ajuste propio para cada provincia"),
}

# Nombres descriptivos de la maestra frente a las tres categorias del modelo de Anna
TIPO_VIA_MODELO = {
    "Autopista libre y autovía": "Autopista_autovia",
    "Autopista de peaje": "Autopista_autovia",
    "Autovía": "Autopista_autovia",
    "Multicarril": "Multicarril",
    "Convencional": "Convencional",
}

# Las categorias que entiende el modelo son mas amplias que las descripciones
# administrativas de la tabla maestra. La interfaz usa estos tres nombres para
# no presentar como clases distintas variantes que el modelo trata igual.
TIPO_VIA_PRESENTACION = {
    "Autopista_autovia": "Autopista o autovía",
    "Multicarril": "Vía multicarril",
    "Convencional": "Carretera convencional",
}

# Codigo provincial del INE, usado para enlazar los indicadores del proyecto
# con la geometria del mapa. El enlace por codigo evita problemas con nombres
# bilingues como Araba/Alava o Alacant/Alicante.
CODIGO_PROVINCIA = {
    "Álava": "01", "Albacete": "02", "Alicante": "03", "Almería": "04",
    "Ávila": "05", "Badajoz": "06", "Barcelona": "08", "Burgos": "09",
    "Cáceres": "10", "Cádiz": "11", "Castellón": "12", "Ciudad Real": "13",
    "Córdoba": "14", "A Coruña": "15", "Cuenca": "16", "Girona": "17",
    "Granada": "18", "Guadalajara": "19", "Huelva": "21", "Huesca": "22",
    "Jaén": "23", "León": "24", "Lleida": "25", "La Rioja": "26",
    "Lugo": "27", "Madrid": "28", "Málaga": "29", "Murcia": "30",
    "Navarra": "31", "Ourense": "32", "Asturias": "33", "Palencia": "34",
    "Pontevedra": "36", "Salamanca": "37", "Cantabria": "39", "Segovia": "40",
    "Sevilla": "41", "Soria": "42", "Tarragona": "43", "Teruel": "44",
    "Toledo": "45", "Valencia": "46", "Valladolid": "47", "Bizkaia": "48",
    "Zamora": "49", "Zaragoza": "50",
}


@st.cache_data(show_spinner=False)
def tramos_puntuados() -> pd.DataFrame:
    """Los 7.250 tramos de 2024 con la probabilidad del modelo de Anna y los
    accidentes de su tabla v2, que son las mismas etiquetas con las que se evalua.

    Los 518 tramos que quedan fuera de la evaluacion no tienen recuento: N_ACC
    va vacio y siguen en el ranking por riesgo estimado. VEH_KM se calcula igual
    que en la maestra y queda vacio en los dos tramos con trafico imputado."""
    pred = pd.read_csv(DATOS / "predicciones_tramos_2024.csv", sep=";", encoding="utf-8-sig")
    acc = pd.read_csv(DATOS / "accidentes_tramos_2024.csv", sep=";", encoding="utf-8-sig")
    df = pred.merge(acc[["TRAMO_ID", "N_ACCIDENTES", "TIPO_VIA_DETALLE"]],
                    on="TRAMO_ID", how="left", validate="one_to_one")
    df["longitud_km"] = df.pk_fin_km - df.pk_inicio_km
    df["N_ACC"] = df.N_ACCIDENTES
    df["VEH_KM"] = df.imd_total * df.longitud_km * 365
    df["TASA_100M"] = df.N_ACC / df.VEH_KM * 1e8
    df["acc_por_km"] = df.N_ACC / df.longitud_km.replace(0, np.nan)
    df["tipo_via_presentacion"] = (
        df["tipo_via"].map(TIPO_VIA_PRESENTACION).fillna("Tipo de vía no disponible")
    )
    df["tipo_via_detalle"] = df["TIPO_VIA_DETALLE"]
    df["banda"] = banda_riesgo(df.PROB_ACCIDENTE_TRAMO_ANIO)
    df["percentil"] = percentil_2024(df.PROB_ACCIDENTE_TRAMO_ANIO)
    return df


@st.cache_data(show_spinner=False)
def maestra_completa() -> pd.DataFrame:
    return pd.read_csv(DATOS / "tabla_maestra.csv", sep=None, engine="python",
                       encoding="utf-8-sig")


@st.cache_data(show_spinner=False)
def provincias() -> pd.DataFrame:
    """Serie provincia-anio de Miki con el indice base 100 ya calculado.

    Mismo universo que la tabla de modelado v2 de Anna (72.806 accidentes), no
    que la tabla maestra. El indice es la tasa por 100 M veh-km de la provincia
    dividida por la media de la Red del Estado del mismo anio. Nunca se ensena el
    conteo absoluto como titular.

    COBERTURA_VEH_KM es la parte del trafico medido que sigue en la v2 tras las
    exclusiones. Por debajo de UMBRAL_COBERTURA la pantalla avisa.
    """
    df = pd.read_csv(DATOS / "provincias_2016_2024.csv", sep=";", encoding="utf-8-sig")
    df["tasa"] = df.N_ACC / df.VEH_KM * 1e8
    nacional = df.groupby("ANYO").apply(
        lambda g: g.N_ACC.sum() / g.VEH_KM.sum() * 1e8, include_groups=False)
    df["tasa_nacional"] = df.ANYO.map(nacional)
    df["indice"] = df.tasa / df.tasa_nacional * 100
    df["poca_cobertura"] = df.COBERTURA_VEH_KM < UMBRAL_COBERTURA
    return df


@st.cache_data(show_spinner=False)
def prevision_provincias() -> pd.DataFrame:
    """Prevision de Miki para el anio siguiente al ultimo con datos.

    Supuesto de la entrega: VEH_KM, IMD y temperatura se arrastran del ultimo
    anio y el lag son sus accidentes reales. Solo entran las provincias con dato
    ese anio (Alava y Bizkaia se quedan fuera).

    El indice se calcula sobre la tasa, igual que la serie historica: esperados
    entre VEH_KM de la provincia, frente a esperados entre VEH_KM del conjunto.
    Sobre el conteo, Madrid saldria arriba solo por tener mas trafico.
    """
    from predecir_provincia import predecir_provincia

    serie = provincias()
    ultimo = serie[serie.ANYO == serie.ANYO.max()]
    anio = int(ultimo.ANYO.iloc[0]) + 1
    esperados = [
        predecir_provincia(f.PROV, anio, veh_km=f.VEH_KM, imd_10000=f.IMD_MEDIA / 1e4,
                           lag1_n_acc=f.N_ACC, temperatura_media_c=f.TEMPERATURA_MEDIA_C,
                           ruta_json=COEFICIENTES_PROVINCIAS)["n_acc_esperado"]
        for f in ultimo.itertuples()
    ]
    df = pd.DataFrame({
        "PROV": ultimo.PROV.to_numpy(),
        "ANYO": anio,
        "N_ACC_ESPERADO": esperados,
        "VEH_KM": ultimo.VEH_KM.to_numpy(),
        "N_ACC_ANTERIOR": ultimo.N_ACC.to_numpy(),
        "indice_anterior": ultimo.indice.to_numpy(),
        # La prevision usa el trafico del ultimo anio, asi que hereda su cobertura
        "COBERTURA_VEH_KM": ultimo.COBERTURA_VEH_KM.to_numpy(),
    })
    df["tasa"] = df.N_ACC_ESPERADO / df.VEH_KM * 1e8
    df["tasa_nacional"] = df.N_ACC_ESPERADO.sum() / df.VEH_KM.sum() * 1e8
    df["indice"] = df.tasa / df.tasa_nacional * 100
    df["cambio_acc"] = df.N_ACC_ESPERADO / df.N_ACC_ANTERIOR - 1
    df["cautela"] = df.cambio_acc.abs() > UMBRAL_CAUTELA
    df["poca_cobertura"] = df.COBERTURA_VEH_KM < UMBRAL_COBERTURA
    return df


@st.cache_data(show_spinner=False)
def predicciones_provincias() -> pd.DataFrame:
    """Las 44 provincias de 2024 con la prediccion de cada variante de Miki."""
    return pd.read_csv(DATOS / "predicciones_2024_4modelos.csv", sep=";", encoding="utf-8-sig")


@st.cache_data(show_spinner=False)
def metricas_provincias() -> pd.DataFrame:
    """Error en 2024 de las cuatro variantes de Miki, recalculado desde sus
    predicciones. La primera fila es la regla ingenua."""
    pred = predicciones_provincias()
    filas = []
    for clave, (nombre, descripcion) in VARIANTES_PROVINCIAS.items():
        error = pred.N_ACC - pred[clave]
        filas.append({"clave": clave, "Versión": nombre, "Qué usa": descripcion,
                      "mae": error.abs().mean(), "rmse": float(np.sqrt((error ** 2).mean()))})
    df = pd.DataFrame(filas)
    df["mejora_mae"] = 1 - df.mae / df.mae.iloc[0]
    df["mejora_rmse"] = 1 - df.rmse / df.rmse.iloc[0]
    return df.set_index("clave", drop=False)


@st.cache_data(show_spinner=False)
def corredores() -> dict:
    """Corredores de Jose, ampliados con los nuestros.

    Las vias discontinuas (AP-7, A-7) traen el campo `provincia` y la ruta se
    recorta a ella: sin eso, un corredor de Malaga se comeria tramos de
    Tarragona. Lo vigila pruebas/auditar_corredores.py.

    `corredores.json` no se toca, que es fichero del equipo. Lo que falta vive
    en `corredores_extra.json`, deducido del propio fichero de tramos, y se
    funde aqui. Cuando una ciudad esta en los dos, manda el punto kilometrico
    de Jose: lo nuestro solo rellena huecos.
    """
    base = json.loads((DATOS / "corredores.json").read_text(encoding="utf-8"))
    if not CORREDORES_EXTRA.exists():
        return base
    extra = json.loads(CORREDORES_EXTRA.read_text(encoding="utf-8"))
    for via, definicion in extra.items():
        if via.startswith("_"):
            continue
        actual = base.setdefault(via, {"nombre": via, "hitos": []})
        if definicion.get("nombre"):
            actual["nombre"] = definicion["nombre"]
        if definicion.get("provincia"):
            actual.setdefault("provincia", definicion["provincia"])
        conocidas = {hito["ciudad"] for hito in actual["hitos"]}
        actual["hitos"] = sorted(
            actual["hitos"] + [h for h in definicion.get("hitos", [])
                               if h["ciudad"] not in conocidas],
            key=lambda hito: hito["pk"])
    return base


@st.cache_data(show_spinner=False)
def ficha_tramos() -> dict:
    return json.loads((DATOS / "ficha_modelo.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------- itinerarios

@st.cache_data(show_spinner=False)
def comparativas() -> list:
    """Trayectos con dos formas de ir, ya validadas. Solo entran pares cuyas dos
    rutas son del mismo tipo de via: el indice mide el tramo con todo su
    trafico, asi que comparar una autovia con una nacional vacia daria la
    vuelta al resultado."""
    if not COMPARATIVAS.exists():
        return []
    return json.loads(COMPARATIVAS.read_text(encoding="utf-8"))["trayectos"]


@st.cache_data(show_spinner=False)
def hitos_por_ciudad() -> dict:
    """Ciudad -> {carretera: punto kilometrico}. Es el grafo con el que se
    resuelve un origen y un destino escritos por el usuario."""
    indice = {}
    for via, definicion in corredores().items():
        for hito in definicion["hitos"]:
            indice.setdefault(hito["ciudad"], {})[via] = float(hito["pk"])
    return indice


@st.cache_data(show_spinner=False)
def ciudades_red() -> list:
    """Las ciudades que el usuario puede escribir, en orden alfabetico."""
    return sorted(hitos_por_ciudad())


def _normalizar(texto: str) -> str:
    """Para comparar lo que escribe el usuario: sin acentos, sin mayusculas y
    sin espacios de mas. 'sevila' no cuela, pero ' SEVILLA ' si."""
    import unicodedata
    plano = unicodedata.normalize("NFKD", str(texto).strip().lower())
    return "".join(c for c in plano if not unicodedata.combining(c))


def buscar_ciudad(texto: str) -> tuple:
    """Devuelve (ciudad, sugerencia). Si la encuentra, sugerencia es None; si no,
    propone la mas parecida para que el aviso sea util y no un simple 'no existe'."""
    from difflib import get_close_matches

    ciudades = ciudades_red()
    plano = {_normalizar(c): c for c in ciudades}
    clave = _normalizar(texto)
    if clave in plano:
        return plano[clave], None
    parecidas = get_close_matches(clave, list(plano), n=1, cutoff=0.75)
    return None, plano[parecidas[0]] if parecidas else None


def tramos_de_itinerario(etapas) -> pd.DataFrame:
    """Los tramos que recorre un itinerario, con los kilometros que se hacen en
    cada uno. Una etapa es (carretera, pk inicial, pk final); un itinerario son
    una o varias encadenadas."""
    tramos = tramos_puntuados()
    piezas = []
    for carretera, pk_salida, pk_llegada in etapas:
        pk_salida, pk_llegada = float(pk_salida), float(pk_llegada)
        pk0, pk1 = sorted([pk_salida, pk_llegada])
        trozo = tramos[tramos.carretera == carretera]
        provincia = corredores().get(carretera, {}).get("provincia")
        if provincia:
            trozo = trozo[trozo.provincia == provincia]
        trozo = trozo[(trozo.pk_fin_km > pk0) & (trozo.pk_inicio_km < pk1)].copy()
        trozo["km_en_ruta"] = (trozo.pk_fin_km.clip(upper=pk1)
                               - trozo.pk_inicio_km.clip(lower=pk0))
        # En orden de marcha: por la A-4 de Sevilla a Madrid los PK van hacia atras
        piezas.append(trozo.sort_values("pk_inicio_km",
                                        ascending=pk_llegada >= pk_salida))
    if not piezas:
        return tramos.iloc[:0].assign(km_en_ruta=0.0, km_desde_salida=0.0,
                                      km_hasta_ahi=0.0)
    ruta = pd.concat(piezas).reset_index(drop=True)
    # Kilometro del viaje en el que se entra y se sale de cada tramo. Es el eje
    # del perfil: dos rutas distintas no comparten puntos kilometricos, pero si
    # comparten "cuanto llevas recorrido".
    ruta["km_hasta_ahi"] = ruta.km_en_ruta.cumsum()
    ruta["km_desde_salida"] = ruta.km_hasta_ahi - ruta.km_en_ruta
    return ruta


def indice_ruta(tramos: pd.DataFrame) -> float:
    """El KPI de Baliza: la probabilidad anual de cada tramo, ponderada por los
    kilometros que se recorren en el, con la media nacional en 100. Misma
    formula en Tu ruta y en Comparar rutas, para que no puedan divergir."""
    validos = tramos[tramos.PROB_ACCIDENTE_TRAMO_ANIO.notna()]
    if not len(validos) or validos.km_en_ruta.sum() <= 0:
        return float("nan")
    media = tramos_puntuados().PROB_ACCIDENTE_TRAMO_ANIO.mean()
    return float(np.average(validos.PROB_ACCIDENTE_TRAMO_ANIO,
                            weights=validos.km_en_ruta) / media * 100)


def evaluar_itinerario(etapas) -> dict:
    """Resumen de un itinerario: indice, kilometros, cobertura de aforo y por
    donde pasa. `km_declarados` son los que separan origen y destino segun los
    hitos; `km_medidos`, los que tienen aforo en 2024. La diferencia es lo que
    la pantalla avisa que no puede medir."""
    etapas = [tuple(e) for e in etapas]
    tramos = tramos_de_itinerario(etapas)
    declarados = sum(abs(float(pk1) - float(pk0)) for _, pk0, pk1 in etapas)
    medidos = float(tramos.km_en_ruta.sum())
    cobertura = medidos / declarados if declarados else 0.0
    validos = tramos[tramos.PROB_ACCIDENTE_TRAMO_ANIO.notna()]
    return {
        "etapas": etapas,
        "tramos": tramos,
        "n_tramos": int(len(tramos)),
        "indice": indice_ruta(tramos),
        "km_declarados": declarados,
        "km_medidos": medidos,
        "km_sin_medir": max(0.0, declarados - medidos),
        "cobertura": cobertura,
        "fiable": cobertura >= COBERTURA_MINIMA_RUTA,
        "provincias": list(dict.fromkeys(tramos.provincia)),
        "vias": list(dict.fromkeys(tramos.carretera)),
        "en_lo_peor": int(validos.banda.isin(["Alto", "Muy alto"]).sum()),
        "parte_autovia": (
            float(tramos[tramos.tipo_via == "Autopista_autovia"].km_en_ruta.sum() / medidos)
            if medidos else 0.0),
    }


@st.cache_data(show_spinner=False)
def _vecinas() -> dict:
    """Ciudad -> {ciudad alcanzable sin cambiar de carretera: [carreteras]}.

    Dentro de un corredor todos sus hitos se alcanzan entre si, asi que esto es
    el grafo de una sola etapa. Se calcula una vez y vale para todo el CSV."""
    hitos = hitos_por_ciudad()
    grafo = {}
    for via, definicion in corredores().items():
        ciudades = [h["ciudad"] for h in definicion["hitos"]]
        for a in ciudades:
            for b in ciudades:
                if a != b:
                    grafo.setdefault(a, {}).setdefault(b, []).append(via)
    return grafo


# Cuatro carreteras encadenadas: con tres, Valencia a Santander se iba por A Coruña
# porque la ruta buena (Madrid, Tordesillas, Palencia) necesita una etapa mas
MAX_ETAPAS_RUTA = 4
# Cuantos itinerarios se llegan a evaluar contra los datos por trayecto
MAX_CANDIDATOS = 8
# Dos rutas solo se comparan si son del mismo tipo de via. El indice mide el tramo
# con todo su trafico, asi que una nacional vacia puntua bajo aunque sea peor para
# quien pasa: sin este filtro, el CSV recomendaria la N-630 frente a la A-66.
DIFERENCIA_TIPO_VIA = 0.15


def _caminos(origen: str, destino: str) -> list:
    """Enumera itinerarios contando solo kilometros, sin tocar los tramos.

    Primero barato y luego caro: recorrer el grafo cuesta microsegundos y filtrar
    aqui los rodeos evita filtrar 7.250 tramos ocho mil veces. Con hasta tres
    etapas aparece la ruta buena de Madrid a Santander (por Palencia, 502 km) y
    tambien el disparate por A Coruña (1.086 km); el que los separa es el margen
    sobre el itinerario mas corto, no el numero de etapas.
    """
    hitos, grafo = hitos_por_ciudad(), _vecinas()
    salidas = []

    def avanzar(actual, visitadas, vias_usadas, etapas, kms):
        if len(etapas) >= MAX_ETAPAS_RUTA:
            return
        for siguiente, vias in grafo.get(actual, {}).items():
            if siguiente in visitadas:
                continue
            for via in vias:
                if via in vias_usadas:
                    continue
                pk0, pk1 = hitos[actual][via], hitos[siguiente][via]
                if pk0 == pk1:
                    continue
                paso = etapas + [(via, pk0, pk1)]
                total = kms + abs(pk1 - pk0)
                if siguiente == destino:
                    salidas.append({"etapas": paso, "km": total,
                                    "pasos": visitadas[1:] + [siguiente]})
                else:
                    avanzar(siguiente, visitadas + [siguiente],
                            vias_usadas | {via}, paso, total)

    avanzar(origen, [origen], set(), [], 0.0)
    return salidas


def _pasa_por(camino: dict, ciudad: str) -> bool:
    """Si el itinerario atraviesa esa ciudad.

    No basta con mirar los enlaces: por la A-4 de Madrid a Sevilla se pasa por
    Córdoba sin cambiar de carretera, asi que Cordoba no figura como paso. Lo que
    vale es si su punto kilometrico cae dentro de algun tramo recorrido."""
    hitos = hitos_por_ciudad().get(ciudad, {})
    if ciudad in camino["pasos"]:
        return True
    for via, pk0, pk1 in camino["etapas"]:
        if via in hitos and min(pk0, pk1) <= hitos[via] <= max(pk0, pk1):
            return True
    return False


def itinerarios_entre(origen: str, destino: str, margen: float = 1.30,
                      paso: str | None = None) -> list:
    """Las formas razonables de ir de una ciudad a otra encadenando corredores.

    Razonable quiere decir que no se aleje mas de `margen` del itinerario mas
    corto: con eso se caen los rodeos sin tener que prohibir el numero de etapas,
    que era lo que dejaba fuera la ruta buena de algunos trayectos.
    """
    hitos = hitos_por_ciudad()
    if origen not in hitos or destino not in hitos or origen == destino:
        return []
    caminos = _caminos(origen, destino)
    if paso and paso not in (origen, destino):
        caminos = [c for c in caminos if _pasa_por(c, paso)]
    if not caminos:
        return []
    corto = min(c["km"] for c in caminos)
    caminos = [c for c in caminos if c["km"] <= corto * margen]

    vistos, candidatos = set(), []
    for camino in sorted(caminos, key=lambda c: (c["km"], len(c["etapas"]))):
        clave = frozenset(via for via, _, _ in camino["etapas"])
        if clave in vistos:
            continue
        vistos.add(clave)
        candidatos.append(camino)
        if len(candidatos) >= MAX_CANDIDATOS:
            break

    resueltos = []
    for camino in candidatos:
        resumen = evaluar_itinerario(camino["etapas"])
        if resumen["n_tramos"] < 3 or resumen["indice"] != resumen["indice"]:
            continue
        resumen["paso"] = ", ".join(camino["pasos"][:-1]) or None
        resueltos.append(resumen)
    return sorted(resueltos, key=lambda r: r["km_declarados"])


def resolver_trayecto(origen: str, destino: str, paso=None, margen: float = 1.30) -> dict:
    """Lo que necesita una fila del CSV: la mejor ruta, la alternativa si la hay
    y, si no se puede, por que no. Nunca lanza una excepcion: la fila siempre
    vuelve con un estado que se pueda enseñar.

    `paso` es opcional y obliga a que la ruta atraviese esa ciudad, para cuando el
    usuario quiere comparar solo las formas de ir de Madrid a Sevilla por Cordoba.
    """
    ciudad_o, sugerencia_o = buscar_ciudad(origen)
    ciudad_d, sugerencia_d = buscar_ciudad(destino)
    for escrito, encontrada, sugerencia in ((origen, ciudad_o, sugerencia_o),
                                            (destino, ciudad_d, sugerencia_d)):
        if encontrada is None:
            pista = f" ¿Querías decir {sugerencia}?" if sugerencia else ""
            return {"estado": "Ciudad no reconocida", "origen": origen, "destino": destino,
                    "aviso": f"«{escrito}» no está en la red que cubre Baliza.{pista}"}
    if ciudad_o == ciudad_d:
        return {"estado": "Sin ruta", "origen": ciudad_o, "destino": ciudad_d,
                "aviso": "El origen y el destino son la misma ciudad."}

    ciudad_paso = None
    if paso is not None and str(paso).strip() and str(paso).strip().lower() != "nan":
        ciudad_paso, sugerencia_p = buscar_ciudad(paso)
        if ciudad_paso is None:
            pista = f" ¿Querías decir {sugerencia_p}?" if sugerencia_p else ""
            return {"estado": "Ciudad no reconocida", "origen": ciudad_o,
                    "destino": ciudad_d,
                    "aviso": f"El paso «{paso}» no está en la red que cubre Baliza.{pista}"}

    opciones = itinerarios_entre(ciudad_o, ciudad_d, margen=margen, paso=ciudad_paso)
    if not opciones:
        por = f" pasando por {ciudad_paso}" if ciudad_paso else ""
        return {"estado": "Sin ruta", "origen": ciudad_o, "destino": ciudad_d,
                "paso": ciudad_paso,
                "aviso": (f"No hay ruta entre {ciudad_o} y {ciudad_d}{por} dentro de la Red "
                          "de Carreteras del Estado que cubre Baliza.")}

    # Misma regla que el catalogo: solo se comparan rutas del mismo tipo de via.
    # Se toma como referencia la que mas autovia lleva, que es la que el conductor
    # da por defecto, y se descartan las que se alejen demasiado de ella.
    referencia = max(o["parte_autovia"] for o in opciones)
    comparables = [o for o in opciones
                   if referencia - o["parte_autovia"] <= DIFERENCIA_TIPO_VIA]
    descartadas = len(opciones) - len(comparables)
    opciones = sorted(comparables, key=lambda o: o["indice"])
    mejor = opciones[0]
    if not mejor["fiable"]:
        estado, aviso = "Cobertura insuficiente", (
            f"Solo tienen aforo {pct_simple(mejor['cobertura'])} de los kilómetros de esta "
            "ruta, así que el índice es orientativo y no se declara ganadora.")
    else:
        estado, aviso = "Resuelta", ""
    return {"estado": estado, "origen": ciudad_o, "destino": ciudad_d,
            "paso": ciudad_paso, "aviso": aviso, "opciones": opciones, "mejor": mejor,
            "alternativa": opciones[1] if len(opciones) > 1 else None,
            "descartadas_por_tipo": descartadas}


def pct_simple(fraccion) -> str:
    """Porcentaje sin depender de baliza.estilo, que es capa de presentacion."""
    return f"{fraccion * 100:.0f} %".replace(".", ",")


# ------------------------------------------------------------- lectura de CSV

def texto_csv(tabla: pd.DataFrame) -> bytes:
    """Todo lo que la app descarga sale por aqui: coma, punto decimal y BOM.

    El BOM es lo que hace que Excel abra los acentos bien. Al volver a subir el
    fichero hay que quitarlo, y eso es justo lo que se olvidaba antes: el nombre
    de la primera columna llegaba como '\\ufefforigen' y la pantalla no reconocia
    el formato ni con la plantilla intacta."""
    return tabla.to_csv(sep=SEPARADOR_CSV, decimal=DECIMAL_CSV,
                        index=False).encode("utf-8-sig")


def _a_numero(serie: pd.Series) -> pd.Series:
    """Numeros vengan como vengan: 1234.5, 1234,5 o 1.234,5.

    Excel en español reescribe los decimales con coma en cuanto el usuario toca
    una celda y guarda. Si eso no se deshace, la columna entra como texto y el
    modelo revienta con un error que no dice nada."""
    texto = serie.astype(str).str.strip().str.replace(" ", "", regex=False)
    con_coma = texto.str.contains(",", regex=False)
    texto = texto.where(~con_coma,
                        texto.str.replace(".", "", regex=False)
                             .str.replace(",", ".", regex=False))
    return pd.to_numeric(texto.replace({"": None, "nan": None, "None": None}),
                         errors="coerce")


def _separador(cabecera: str) -> str:
    """El que mas veces aparece en la primera linea. Mas fiable que el olfateador
    de pandas, que se atraganta con una sola columna o con comas dentro del texto."""
    cuentas = {sep: cabecera.count(sep) for sep in SEPARADORES_ACEPTADOS}
    mejor = max(cuentas, key=cuentas.get)
    return mejor if cuentas[mejor] else SEPARADOR_CSV


def leer_tabla_csv(archivo) -> tuple:
    """Lee el CSV que sube el usuario y lo deja utilizable. Devuelve (tabla, error).

    Tolera: BOM, coma o punto y coma o tabulador, acentos en utf-8 o en Windows-1252,
    mayusculas y espacios en los encabezados, columnas en otro orden, columnas de
    mas, filas vacias y decimales con coma. Nunca lanza una excepcion.
    """
    crudo = archivo.read() if hasattr(archivo, "read") else archivo
    if isinstance(crudo, str):
        crudo = crudo.encode("utf-8")
    for codificacion in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            texto = crudo.decode(codificacion)
            break
        except UnicodeDecodeError:
            continue
    else:
        return None, "No se ha podido leer el archivo: guárdalo como CSV en UTF-8."

    texto = texto.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    lineas = [l for l in texto.split("\n") if l.strip()]
    if len(lineas) < 2:
        return None, "El archivo no tiene filas debajo de los encabezados."

    import csv as _csv
    import io
    try:
        tabla = pd.read_csv(io.StringIO("\n".join(lineas)),
                            sep=_separador(lineas[0]), dtype=str,
                            skipinitialspace=True, quoting=_csv.QUOTE_MINIMAL)
    except Exception:
        return None, ("No se ha podido interpretar el archivo. Descarga una plantilla y "
                      "conserva sus encabezados.")

    tabla.columns = [str(c).lstrip("﻿").strip().lower().replace(" ", "_")
                     for c in tabla.columns]
    tabla = tabla.loc[:, [c for c in tabla.columns if c and not c.startswith("unnamed")]]
    renombres = {}
    for canonico, alias in ALIAS_COLUMNAS.items():
        for columna in tabla.columns:
            if columna in alias and columna != canonico:
                renombres[columna] = canonico
    tabla = tabla.rename(columns=renombres)
    tabla = tabla.dropna(how="all")
    tabla = tabla[~tabla.apply(lambda f: f.astype(str).str.strip().eq("").all(), axis=1)]
    if tabla.empty:
        return None, "El archivo no tiene ninguna fila con datos."
    return tabla.reset_index(drop=True), None


COLUMNAS_NUMERICAS = ("pk_inicio", "pk_fin", "imd_total", "imd_pesados", "viajes_semana",
                      "pk_inicio_km", "pk_fin_km", "proporcion_pesados")


def numerizar(tabla: pd.DataFrame) -> pd.DataFrame:
    """Pasa a numero las columnas que el modelo o la pantalla necesitan como tal."""
    tabla = tabla.copy()
    for columna in COLUMNAS_NUMERICAS:
        if columna in tabla.columns:
            tabla[columna] = _a_numero(tabla[columna])
    return tabla


# Universo con el que se compara un escenario de gravedad. El test completo es en
# dos tercios urbano y puntua mas bajo, asi que colocar ahi una salida por
# carretera la subiria de puesto sin merecerlo. Baliza solo cubre la Red del
# Estado peninsular, y ese es el subconjunto con el que se compara.
UNIVERSO_GRAVEDAD = "interurbano_peninsular"

# La entrega de gravedad cambio de formato el 17/09: antes un bloque plano con
# estos nombres, ahora uno por universo y con la matriz de confusion entera. Se
# traduce aqui para que ninguna pagina dependa de la version del fichero.
NOMBRES_METRICAS = {
    "total_accidentes": "n", "leves_reales": "leves", "severos_reales": "severos",
    "leves_correctamente_clasificados": "TN", "falsas_alertas": "FP",
    "severos_no_detectados": "FN", "severos_detectados": "TP",
    "alertas_totales": "alertas", "precision_severo": "precision",
    "recall_severo": "recall",
}

# Caso de referencia de la pantalla de gravedad, por orden de preferencia. El de
# Lourdes es la mediana del test completo y es urbano; si llega el mediano
# interurbano, basta con dejarlo en datos/ para que se use.
CASOS_REFERENCIA_CARRETERA = ("caso_default_2024_interurbano.json",
                              "caso_default_2024_carretera.json")


@st.cache_data(show_spinner=False)
def metadata_gravedad() -> dict:
    return json.loads((DATOS / "metadata_gravedad.json").read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def metricas_gravedad(universo: str = "global") -> dict:
    """Acierto del modelo de gravedad en el test 2024, al umbral de la entrega.

    Lourdes lo recalculo desde el mismo vector de scores que lee esta web, en una
    sola ejecucion: la entrega anterior mezclaba dos y las alertas no cuadraban.
    `global` son los 101.996 accidentes del test y es la cifra oficial;
    `interurbano_peninsular`, los 32.562 de la red que cubre Baliza.
    """
    bruto = json.loads((DATOS / "metricas_test_2024.json").read_text(encoding="utf-8"))
    if isinstance(bruto.get(universo), dict):
        bloque = bruto[universo]
    elif universo == "global":
        bloque = bruto  # formato viejo: un unico bloque plano, sin universos
    else:
        raise KeyError(f"metricas_test_2024.json no trae el bloque {universo!r}")
    metricas = {NOMBRES_METRICAS.get(k, k): v for k, v in bloque.items() if k != "conjunto"}
    metricas["universo"] = universo
    metricas["tasa_base"] = metricas["severos"] / metricas["n"]
    return metricas


@st.cache_data(show_spinner=False)
def referencias_tramos() -> dict:
    """Acierto del modelo de tramos frente a dos reglas sencillas (solo trafico e
    historico) sobre el test comun de 2024, en total y por tipo de via. Entrega de
    Anna, sin modificar: las paginas leen las cifras de aqui, nunca a mano."""
    ref = json.loads((DATOS / "referencias_test_2024.json").read_text(encoding="utf-8"))
    por_tipo = pd.DataFrame([
        {"tipo_via": fila["tipo_via"], "n": fila["n"],
         "modelo": fila["modelo_final"]["roc_auc"],
         "trafico": fila["solo_trafico"]["roc_auc"]}
        for fila in ref["por_tipo_via"]])
    por_tipo["ventaja"] = por_tipo.modelo - por_tipo.trafico
    return {"n": ref["conjunto"]["n"],
            "version_modelo": ref["conjunto"]["version_modelo"],
            **{fila["id"]: fila for fila in ref["referencias"]},
            "por_tipo_via": por_tipo}


@st.cache_data(show_spinner=False)
def geometria_provincias() -> dict:
    """Limites provinciales para el coropletico, incluidos en el repositorio
    para que la presentacion no dependa de una conexion a Internet."""
    return json.loads((DATOS / "provincias_espana.geojson").read_text(encoding="utf-8"))


@st.cache_resource(show_spinner="Cargando el modelo de tramos...")
def modelo_tramos():
    """Paquete de Anna. Solo se carga en las pantallas que predicen casos nuevos;
    el ranking y la ruta leen la tabla ya puntuada."""
    from validador_entrada import cargar_paquete_modelo
    paquete, errores = cargar_paquete_modelo(MODELOS / "modelo_final.joblib")
    return paquete, errores


@st.cache_resource(show_spinner="Cargando el modelo de gravedad...")
def modelo_gravedad():
    from catboost import CatBoostClassifier
    modelo = CatBoostClassifier()
    modelo.load_model(str(MODELOS / "modelo_gravedad.cbm"))
    return modelo


# ------------------------------------------------------ gravedad (Lourdes)

# Lo que elige el usuario, traducido a los codigos del modelo. Cada opcion fija
# a la vez todas las variables que dependen entre si: una hora de madrugada con
# luz de dia o una autovia en zona urbana son escenarios que no existen, y el
# modelo trabaja con combinaciones. Las horas y los meses se eligen dentro de
# cualquier definicion razonable de franja y estacion.
BLOQUES_GRAVEDAD = {
    "Momento del día": {
        "Por la mañana (10:00)": {"FRANJA_HORARIA": "Mañana", "HORA": "10",
                                  "CONDICION_ILUMINACION": "1"},
        "Por la tarde (17:00)": {"FRANJA_HORARIA": "Tarde", "HORA": "17",
                                 "CONDICION_ILUMINACION": "1"},
        "De noche (23:00)": {"FRANJA_HORARIA": "Noche", "HORA": "23",
                             "CONDICION_ILUMINACION": "6"},
        "De madrugada (4:00)": {"FRANJA_HORARIA": "Madrugada", "HORA": "4",
                                "CONDICION_ILUMINACION": "6"},
    },
    "Día": {
        "Entre semana": {"DIA_SEMANA": "2", "FIN_DE_SEMANA": "No"},
        "Sábado": {"DIA_SEMANA": "6", "FIN_DE_SEMANA": "Sí"},
        "Domingo": {"DIA_SEMANA": "7", "FIN_DE_SEMANA": "Sí"},
    },
    "Época del año": {
        "Invierno": {"MES": "1", "ESTACION": "Invierno"},
        "Primavera": {"MES": "4", "ESTACION": "Primavera"},
        "Verano": {"MES": "7", "ESTACION": "Verano"},
        "Otoño": {"MES": "11", "ESTACION": "Otoño"},
    },
    "Tiempo": {
        "Despejado": {"CONDICION_METEO": "1", "CONDICION_FIRME": "1"},
        "Nublado": {"CONDICION_METEO": "2", "CONDICION_FIRME": "1"},
        "Lluvia débil": {"CONDICION_METEO": "3", "CONDICION_FIRME": "3"},
        "Lluvia fuerte": {"CONDICION_METEO": "4", "CONDICION_FIRME": "3"},
        "Nieve": {"CONDICION_METEO": "6", "CONDICION_FIRME": "6"},
    },
    "Carretera": {
        "Autovía": {"ZONA": "1", "TIPO_VIA": "3.0",
                    "TIPO_VIA_AGRUPADO": "Autopista_Autovia", "TRAZADO_PLANTA": "1"},
        "Autovía, en curva": {"ZONA": "1", "TIPO_VIA": "3.0",
                              "TIPO_VIA_AGRUPADO": "Autopista_Autovia", "TRAZADO_PLANTA": "2"},
        "Autopista de peaje": {"ZONA": "1", "TIPO_VIA": "1.0",
                               "TIPO_VIA_AGRUPADO": "Autopista_Autovia", "TRAZADO_PLANTA": "1"},
        "Convencional": {"ZONA": "1", "TIPO_VIA": "6.0",
                         "TIPO_VIA_AGRUPADO": "Carretera", "TRAZADO_PLANTA": "1"},
        "Convencional, en curva": {"ZONA": "1", "TIPO_VIA": "6.0",
                                   "TIPO_VIA_AGRUPADO": "Carretera", "TRAZADO_PLANTA": "2"},
    },
}

# Algunas etiquetas del diccionario de la DGT llegan cortadas a 50 caracteres
ETIQUETAS_CORREGIDAS = {
    "CONDICION_ILUMINACION": {
        "4": "Sin luz natural, con alumbrado encendido",
        "5": "Sin luz natural, con alumbrado apagado",
    },
}


@st.cache_data(show_spinner=False)
def caso_referencia_gravedad() -> tuple[dict, bool]:
    """Caso real del test 2024 con el score mas cercano a la mediana.

    Devuelve (caso, es_de_carretera). El de Lourdes es la mediana del test
    completo y es urbano, asi que se traslada a autovia cambiando solo el bloque
    de carretera. Si llega el mediano interurbano se usa tal cual.
    """
    carretera = next((DATOS / n for n in CASOS_REFERENCIA_CARRETERA
                      if (DATOS / n).exists()), None)
    es_de_carretera = carretera is not None
    origen = carretera if es_de_carretera else DATOS / "caso_default_2024.json"
    caso = json.loads(origen.read_text(encoding="utf-8"))
    caso.pop("score_severo", None)
    if not es_de_carretera:
        caso.update(BLOQUES_GRAVEDAD["Carretera"]["Autovía"])
    return caso, es_de_carretera


@st.cache_data(show_spinner=False)
def etiquetas_gravedad() -> dict:
    etiquetas = json.loads((DATOS / "labels_categorias.json").read_text(encoding="utf-8"))
    etiquetas["DIA_SEMANA"] = {k: v.capitalize() for k, v in etiquetas["DIA_SEMANA"].items()}
    for variable, cambios in ETIQUETAS_CORREGIDAS.items():
        etiquetas[variable].update(cambios)
    return etiquetas


@st.cache_data(show_spinner=False)
def importancia_gravedad() -> pd.Series:
    """Importancia nativa de CatBoost. Dice cuanto usa el modelo cada variable,
    no cuanto cambia la gravedad al moverla."""
    valores = json.loads((DATOS / "feature_importance.json").read_text(encoding="utf-8"))
    return pd.Series(valores, dtype=float).sort_values(ascending=False)


@st.cache_data(show_spinner=False)
def scores_gravedad() -> pd.DataFrame:
    """Los accidentes del test 2024 con su score, su gravedad real y si son
    interurbanos peninsulares. El orden de las filas es el de la entrega."""
    df = pd.read_csv(DATOS / "scores_test_2024.csv")
    if "interurbano_peninsular" not in df.columns:
        df["interurbano_peninsular"] = True
    if "severo_real" not in df.columns:
        df["severo_real"] = np.nan
    return df


@st.cache_data(show_spinner=False)
def referencia_gravedad(universo: str = UNIVERSO_GRAVEDAD) -> np.ndarray:
    """Scores del test 2024 ordenados, contra los que se coloca un escenario.

    Por defecto solo los interurbanos peninsulares. `global` devuelve los 101.996.
    """
    scores = scores_gravedad()
    if universo != "global":
        scores = scores[scores.interurbano_peninsular]
    return np.sort(scores.score_severo.to_numpy(dtype=float))


def puntuar_gravedad(escenarios: list[dict]) -> np.ndarray:
    """Score Severo de varios escenarios completos en una sola llamada."""
    entrada = metadata_gravedad()["entrada"]
    tabla = pd.DataFrame(escenarios)[entrada["columnas"]]
    for columna in entrada["categoricas"]:
        tabla[columna] = tabla[columna].astype(str)
    return modelo_gravedad().predict_proba(tabla)[:, 1]


def percentil_gravedad(scores, universo: str = UNIVERSO_GRAVEDAD) -> np.ndarray:
    """Puesto de cada escenario frente a los accidentes reales de 2024, de 0 a 100.
    El score no esta calibrado: el orden es lo unico que se puede defender."""
    return _rango_percentil(referencia_gravedad(universo), scores)


def banda_gravedad(percentiles) -> list:
    """Mismas bandas que los tramos: 'Muy alto' es el 5% mas grave del universo
    de referencia."""
    cortes = [-0.01] + [c * 100 for c in CUANTILES] + [100.01]
    return list(pd.cut(np.asarray(percentiles, dtype=float), bins=cortes,
                       labels=BANDAS, right=False))


def predecir_tramos_usuario(tabla: pd.DataFrame, anio: int = ANIO):
    """Valida y predice una tabla introducida por el usuario.

    Devuelve (resultado_validacion, predicciones o None, mensaje de error o None).
    predecir_tramos lanza excepciones; aqui se convierten en texto para que la
    pantalla nunca muestre una traza.
    """
    from validador_entrada import preparar_para_modelo, validar_tramos
    from preparacion_tramos import predecir_tramos

    paquete, errores = modelo_tramos()
    if errores:
        return None, None, errores[0]
    validacion = validar_tramos(tabla, paquete)
    if not validacion.valido:
        return validacion, None, None

    entrada = preparar_para_modelo(validacion.datos, anio=anio)
    # Una flota con dos rutas que comparten un trozo de via manda ese tramo dos
    # veces. predecir_tramos rechaza el intervalo repetido, asi que se predice
    # sobre los distintos y el resultado se reparte a las filas originales.
    clave = _clave(entrada.provincia, entrada.carretera,
                   entrada.pk_inicio_km, entrada.pk_fin_km) + "|" + str(anio)
    distintos = entrada[~clave.duplicated()]
    try:
        predichos = predecir_tramos(distintos, paquete)
    except Exception:
        return validacion, None, ("No se ha podido calcular la prediccion con estos datos. "
                                  "Revisa los kilometros y el trafico de cada fila.")

    salida = (predichos.set_index(clave[~clave.duplicated()].to_numpy())
              .reindex(clave.to_numpy()).reset_index(drop=True))
    salida["TRAMO_ID"] = entrada.TRAMO_ID.to_numpy()
    salida["banda"] = banda_riesgo(salida.PROB_ACCIDENTE_TRAMO_ANIO)
    salida["percentil"] = percentil_2024(salida.PROB_ACCIDENTE_TRAMO_ANIO)
    return validacion, salida, None


# --------------------------------------------------------------- utilidades

BANDAS = ["Bajo", "Medio", "Alto", "Muy alto"]
# Cuantiles nacionales, no cortes fijos. Con cortes en 0,25 / 0,50 / 0,75 casi
# todos los tramos salian "muy alto": la probabilidad de que un tramo tenga algun
# accidente en todo un anio es alta por construccion. "Muy alto" tiene que
# significar el 5% peor de Espana, no un numero redondo.
CUANTILES = [0.50, 0.80, 0.95]


@st.cache_data(show_spinner=False)
def referencia_2024() -> np.ndarray:
    """Las 7.250 probabilidades de 2024, ordenadas. Es la misma
    distribucion que usa la API de Anna para su campo percentil_2024."""
    prob = pd.read_csv(DATOS / "predicciones_tramos_2024.csv", sep=";",
                       encoding="utf-8-sig").PROB_ACCIDENTE_TRAMO_ANIO
    return np.sort(prob.dropna().to_numpy(dtype=float))


@st.cache_data(show_spinner=False)
def cortes_riesgo() -> list:
    prob = pd.read_csv(DATOS / "predicciones_tramos_2024.csv", sep=";",
                       encoding="utf-8-sig").PROB_ACCIDENTE_TRAMO_ANIO
    return [-0.01] + list(prob.quantile(CUANTILES)) + [1.01]


def percentil_2024(prob) -> pd.Series:
    """Posicion del tramo dentro de la red de 2024, de 0 a 100.

    Rango percentil con posicion media en los empates: el mismo criterio que la
    API, para que los dos devuelvan el mismo numero hasta el segundo decimal.
    """
    serie = pd.Series(prob)
    return pd.Series(_rango_percentil(referencia_2024(), serie),
                     index=serie.index).round(2)


def _rango_percentil(referencia: np.ndarray, valores) -> np.ndarray:
    """Rango percentil con posicion media en los empates, sobre una referencia
    ya ordenada. Un valor nulo sigue siendo nulo: sin dato no es riesgo cero."""
    valores = np.asarray(valores, dtype=float)
    izquierda = np.searchsorted(referencia, valores, side="left")
    derecha = np.searchsorted(referencia, valores, side="right")
    rango = 100.0 * (izquierda + derecha) / 2.0 / referencia.size
    return np.where(np.isnan(valores), np.nan, rango)


def banda_riesgo(prob: pd.Series) -> pd.Series:
    """Cuatro categorias con etiqueta de texto. El color nunca va solo: uno de
    cada doce hombres no distingue el verde del rojo."""
    return pd.cut(prob, bins=cortes_riesgo(), labels=BANDAS, right=False)


def _clave(provincia, via, pk0, pk1) -> pd.Series:
    """Clave de contenido tramo-anio. El TRAMO_ID de la maestra es un indice de
    fila y no identifica el mismo tramo entre anios."""
    return (provincia.astype(str) + "|" + via.astype(str) + "|"
            + pd.to_numeric(pk0).map(lambda n: format(n, ".12g")) + "|"
            + pd.to_numeric(pk1).map(lambda n: format(n, ".12g")))
