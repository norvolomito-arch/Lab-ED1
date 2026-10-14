# /// script
# dependencies = [
#     "pygame-ce",
# ]
# ======================================================================
# ARCHIVO: main.py (raiz) - el boton de encendido del juego
# ======================================================================
# QUE ES: el archivo que se ejecuta para arrancar el juego.
# PARA QUE SIRVE: casi no tiene logica; solo llama a la funcion main() que vive
# en game/main.py. Existe en la raiz porque pygbag (la herramienta que convierte
# el juego a pagina web) busca un 'main.py' aqui.
# COMO SE USA: python main.py   (desde dentro de la carpeta zombcircle_apocalypse)
# ======================================================================

# ///
"""Punto de entrada de Zombcircle Apocalypse (local y pygbag).

- Local:    python main.py        (o  python -m game.main)
- Navegador: pygbag .

Se importa pygame aqui, de forma explicita, para que pygbag detecte la
dependencia desde el archivo principal. La llamada asyncio.run(main()) debe
ir al final de este archivo: pygbag la necesita para arrancar el bucle.
"""
# 'asyncio' permite que el juego ceda el control al navegador en cada
# fotograma (necesario para la version web). Aqui solo se usa para arrancar.
import asyncio

# Importamos pygame (la libreria de videojuegos) para que pygbag sepa
# que el proyecto lo necesita.
import pygame  # noqa: F401  (pygbag detecta pygame-ce por este import)

# Traemos la funcion principal del juego desde la carpeta 'game'.
from game.main import main

# ARRANCA EL JUEGO: ejecuta main() y no termina hasta que cierres la ventana.
asyncio.run(main())
