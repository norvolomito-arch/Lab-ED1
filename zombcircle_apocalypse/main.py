# /// script
# dependencies = [
#     "pygame-ce",
# ]
# ///
"""Punto de entrada de Zombcircle Apocalypse (local y pygbag).

- Local:    python main.py        (o  python -m game.main)
- Navegador: pygbag .

Se importa pygame aqui, de forma explicita, para que pygbag detecte la
dependencia desde el archivo principal. La llamada asyncio.run(main()) debe
ir al final de este archivo: pygbag la necesita para arrancar el bucle.
"""
import asyncio

import pygame  # noqa: F401  (pygbag detecta pygame-ce por este import)

from game.main import main

asyncio.run(main())
