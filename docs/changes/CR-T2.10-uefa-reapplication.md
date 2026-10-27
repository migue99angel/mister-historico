# CR-T2.10 · Reaplicación del desempate en grupos UEFA 2012-13

## Motivo

El artículo 7.06.e del [reglamento UEFA 2012-13](https://www.eurocups.ru/docs/cl-12_13-rules.pdf)
ordena reaplicar los criterios de enfrentamientos directos únicamente si,
después de los cuatro criterios iniciales, **dos clubes** siguen empatados.
El contrato anterior interpretaba `reapply_head_to_head: true` como una
reaplicación para cualquier subconjunto todavía empatado. Eso podía cambiar el
orden de tres clubes: al excluir al cuarto, sus enfrentamientos directos pasan
a tener otros totales.

## Cambio de contrato

`reapply_head_to_head: true` significa que, tras agotar el bloque consecutivo
de criterios directos, se vuelve a aplicar ese bloque solo a los subconjuntos
de **exactamente dos** clubes que sigan empatados. Un empate de tres o cuatro
continúa con el siguiente criterio general. La misma condición se usa al
comprobar la procedencia de las sedes para el criterio de goles como visitante.
No cambian los campos ni la serialización de las API publicadas; cambia la
semántica del booleano y, por eso, se tramita como CR.

La prueba sintética crea un empate de cuatro clubes en puntos: tres quedan
empatados tras todo el bloque directo al incluir al cuarto, aunque su miniliga
de tres daría otro orden. Conserva la ordenación por el siguiente criterio
general. Los datos son de Test FC y no afirman resultados históricos.

## Límite pendiente para T2.10

El artículo 7.06.h usa como último desempate los puntos de coeficiente del
club y su asociación durante cinco temporadas. Ese criterio aún no existe en
el esquema ni en el motor. Esta CR no declara completo el reglamento UEFA ni
autoriza integrar `season.yaml` del Real Madrid: hace falta otra CR que publique
el coeficiente, incorpore sus valores con fuente para los participantes y lo
aplique solo cuando los criterios anteriores sigan empatados. Hasta entonces,
la PR de T2.10 permanece como borrador.
