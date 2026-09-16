"""Arranca cada pagina en seco y falla si alguna lanza una excepcion."""
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

PAGINAS = ["inicio", "ruta", "mapa", "provincia", "noche", "fiabilidad",
           "como_funciona", "flotas"]
MAPA = {"inicio": "inicio", "ruta": "ruta", "mapa": "mapa", "provincia": "provincia",
        "noche": "noche", "fiabilidad": "fiabilidad", "como": "como_funciona",
        "flotas": "flotas"}

fallos = 0
for nombre in PAGINAS:
    prueba = AppTest.from_file(str(RAIZ / "paginas" / f"{nombre}.py"), default_timeout=180)
    prueba.session_state["paginas"] = MAPA
    prueba.run()
    if prueba.exception:
        fallos += 1
        print(f"[FALLO] {nombre}: {prueba.exception[0].message}")
    else:
        avisos = len(prueba.warning) + len(prueba.error)
        print(f"[OK   ] {nombre} | {len(prueba.markdown)} bloques, {avisos} avisos en pantalla")
print(f"\n{'Todas las paginas arrancan.' if not fallos else str(fallos) + ' paginas con error.'}")
sys.exit(1 if fallos else 0)
