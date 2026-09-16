"""Arranca la app y cada pagina en seco, y falla si alguna lanza una excepcion."""
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from baliza.estilo import PAGINAS  # noqa: E402

MAPA = {clave: clave for clave, *_ in PAGINAS}

fallos = 0
entrada = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=180)
entrada.run()
if entrada.exception:
    fallos += 1
    print(f"[FALLO] app.py: {entrada.exception[0].message}")
else:
    print(f"[OK   ] app.py | pagina inicial: {entrada.session_state['pagina_actual']}")

for clave, _, fichero, *_ in PAGINAS:
    prueba = AppTest.from_file(str(RAIZ / fichero), default_timeout=180)
    prueba.session_state["paginas"] = MAPA
    prueba.session_state["pagina_actual"] = clave
    prueba.run()
    nombre = Path(fichero).stem
    if prueba.exception:
        fallos += 1
        print(f"[FALLO] {nombre}: {prueba.exception[0].message}")
    else:
        avisos = len(prueba.warning) + len(prueba.error)
        print(f"[OK   ] {nombre} | {len(prueba.markdown)} bloques, {avisos} avisos en pantalla")
print(f"\n{'Todas las paginas arrancan.' if not fallos else str(fallos) + ' paginas con error.'}")
sys.exit(1 if fallos else 0)
