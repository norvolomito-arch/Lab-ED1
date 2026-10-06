# Lab-ED1
grupo #2

Los videojuegos modernos no solo guardan el progreso del jugador: registran todo lo que ocurre
durante la partida. Cada enemigo eliminado, cada golpe recibido, cada muerte y cada nivel superado
se escribe en un archivo llamado bitácora de eventos (event log o telemetría).
Esa bitácora crece rápido, y nadie la carga completa en memoria: se procesa recorriéndola de principio
a fin, acumulando resultados a medida que se lee.
Con esos archivos, los estudios de videojuegos responden preguntas reales:
• ¿En qué nivel abandona la mayoría de los jugadores?
• ¿Está el juego demasiado difícil o demasiado fácil?
• ¿Los jugadores que sobreviven más tiempo son los que más puntaje logran?
• ¿Ese puntaje altísimo es real o es trampa?
En este laboratorio construirán ese sistema: la escritura de la bitácora mientras se juega, su lectura
robusta desde archivos, y un motor estadístico implementado desde cero que analiza los datos y los
muestra en gráficas dentro del propio videojuego.
