"""Inferencia portable: no depende de Colab ni de celdas del notebook."""
import numpy as np
import pandas as pd

def validar_columnas(df, columnas):
    """Comprueba que todas las columnas indicadas estén presentes."""
    ausentes = sorted(set(columnas) - set(df.columns))
    if ausentes:
        raise ValueError(f"Las siguientes columnas no existen: {ausentes}")

def completar_predictores(datos, parametros=None):
    """Completa v2 con parámetros ya ajustados; v1 ya contiene los logaritmos."""
    salida = datos.copy()
    if parametros is not None:
        for variable, valores in parametros.items():
            relleno = salida.tipo_via_modelo.map(valores['grupos']).fillna(valores['global'])
            salida[variable] = salida[variable].fillna(relleno)
        salida['log_imd_total'] = np.log1p(salida.imd_total)
    return salida

def predecir_tramos(entrada, paquete):
    """Predice ocurrencia anual condicionada a tráfico; conserva la identificación."""
    datos = entrada.copy()
    requeridas = ['TRAMO_ID', 'anio', 'provincia', 'carretera', 'pk_inicio_km',
                  'pk_fin_km', 'tipo_via', 'imd_total', 'proporcion_pesados']
    validar_columnas(datos, requeridas)
    if datos.empty or datos[requeridas[:7]].isna().any().any():
        raise ValueError('Faltan observaciones o datos de identificación del tramo.')
    if not datos.TRAMO_ID.is_unique:
        raise ValueError('TRAMO_ID debe identificar una observación única.')
    for columna in ['anio', 'pk_inicio_km', 'pk_fin_km', 'imd_total', 'proporcion_pesados']:
        datos[columna] = pd.to_numeric(datos[columna], errors='raise')
    if not np.isfinite(datos[['anio', 'pk_inicio_km', 'pk_fin_km']]).all().all() or datos.anio.mod(1).ne(0).any():
        raise ValueError('Año o puntos kilométricos inválidos.')
    datos['longitud_km'] = datos.pk_fin_km - datos.pk_inicio_km
    if datos.longitud_km.le(0).any():
        raise ValueError('El PK final debe ser mayor que el inicial.')
    for campo, categorias in paquete['categorias'].items():
        if not datos[campo].isin(categorias).all():
            raise ValueError(f'Categoría no aprendida o sin normalizar en {campo}.')
    x = datos.rename(columns={'provincia':'provincia_norm', 'tipo_via':'tipo_via_modelo'}).copy()
    if paquete['imputacion'] is not None:
        for variable, parametros in paquete['imputacion'].items():
            relleno = x.tipo_via_modelo.map(parametros['grupos']).fillna(parametros['global'])
            x[variable] = x[variable].fillna(relleno)
    if not np.isfinite(x[['imd_total','proporcion_pesados']]).all().all():
        raise ValueError('Falta tráfico utilizable para la versión elegida.')
    if x.imd_total.le(0).any() or not x.proporcion_pesados.between(0,1).all():
        raise ValueError('IMD debe ser positiva y proporción de pesados estar entre 0 y 1.')
    x['log_imd_total'] = np.log1p(x.imd_total)
    x['log_longitud_pk'] = np.log(x.longitud_km)
    datos['INTERVALO_ID'] = (datos.provincia.astype(str) + '|' + datos.carretera.astype(str)
        + '|' + datos.pk_inicio_km.map(lambda n: format(n,'.12g'))
        + '|' + datos.pk_fin_km.map(lambda n: format(n,'.12g')))
    datos['CLAVE_TRAMO_ANIO'] = datos.INTERVALO_ID + '|' + datos.anio.astype(int).astype(str)
    if datos.CLAVE_TRAMO_ANIO.duplicated().any():
        raise ValueError('Hay más de una fila para el mismo intervalo y año.')
    datos['PROB_ACCIDENTE_TRAMO_ANIO'] = paquete['modelo'].predict_proba(x[paquete['predictores']])[:,1]
    datos['FUERA_RANGO_TRAIN'] = False
    for variable, limites in paquete['rangos_train'].items():
        datos['FUERA_RANGO_TRAIN'] |= ~x[variable].between(limites[0], limites[1])
    return datos
