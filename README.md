# Análisis de Datos aplicado a Ventas de retail — Equipo 1 - Entrega 3

## INTEGRANTES
- HAROL STIVEN RESTREPO RESTREPO
- JALVI HUMBERTO VILLEGAS TABORDA
- LEONEL ANTONIO MARTINEZ SILGADO
- YULIETH MARCELA URREGO RESTREPO

## 1. Objetivo

**Objetivo general.** Transformar el histórico de transacciones de la operación
de retail en información accionable para la toma de decisiones, mediante un
dashboard interactivo, un sistema de indicadores y la validación estadística de
hipótesis de negocio.


**Decision que habilita el proyecto.** Priorizar la asignación de esfuerzo comercial y
logístico para el siguiente ejercicio con evidencia estadística: dónde invertir en
adquisición, qué territorios intervenir, qué categorías sostener y cómo dimensionar el
pico de fin de año.

---

## 2. Dataset y fuente

| Atributo | Valor |
|---|---|
| Archivo | `train.csv` (2,0 MB) |
| Origen | Dataset público *Superstore* |
| Grano | Una línea de pedido (un producto dentro de un pedido) |
| Registros | 9.800 líneas · 4.922 pedidos |
| Clientes | 793 · Productos: 1.861 |
| Periodo | 2015-01-03 a 2018-12-30 |
| Cobertura | 1 país (Estados Unidos) · 49 estados · 529 ciudades |
| Medida | `Sales` (ingreso de la línea, USD). Total: **2.261.537** |


## 3. Metodología

6 fases alineadas:

| Fase | Actividad | Técnicas y herramientas |
|---|---|---|
| 1 · Comprensión del problema | Contexto, problema de análisis y de negocio, 5 preguntas clave | Análisis documental del dataset |
| 2 · Formulación de hipótesis | 5 hipótesis con H0/H1, justificación y prueba asignada | Contraste de hipótesis |
| 3 · Preparación de datos | Auditoría, limpieza, variables derivadas, dos granos de análisis | `pandas`, auditoría por comprobaciones |
| 4 · Definición de KPIs | 10 KPIs con fórmula, meta, tendencia e hipótesis asociada | Diseño de indicadores |
| 5 · Dashboard | 25 visualizaciones de 17 tipos distintos y especificación Power BI | Gráficos SVG propios, modelo en estrella |
| 6 · Análisis y storytelling | Validación estadística, proyección, narrativa y decisiones | t de Welch, ANOVA, Games-Howell, chi-cuadrado, Mann-Kendall, OLS |

**Enfoque analítico.** El proyecto trabaja en **dos granos** porque las preguntas
operan en niveles distintos: el grano **línea de pedido** (9.800
registros) para mezcla de producto, geografía y logística; y el grano **pedido**
(4.922 registros) para ticket, frecuencia y valor de cliente.

**Herramientas.** Python (`pandas`, `numpy`) para el pipeline reproducible; una
librería propia de gráficos SVG (`src/graficos_svg.py`) y de estadística
(`src/analisis_retail.py`) que reproduce las distribuciones t, chi-cuadrado y F sin
depender de `scipy`.

---

## 4. Preparación y calidad de los datos

**Hallazgos de la auditoría**

| Comprobación | Resultado | Tratamiento |
|---|---|---|
| Filas y columnas | 9.800 × 18 | — |
| Nulos | 11 en `Postal Code` (0,11 %) | Imputación con 0; la variable no participa en ningún KPI |
| Duplicados exactos / por `Row ID` | 0 / 0 | No se elimina ningún registro |
| Duplicados `(Order ID, Product ID)` | 8 | Legítimos: un producto puede repetirse en líneas distintas |
| Ventas nulas, cero o negativas | 0 | Sin tratamiento |
| Fechas | Formato `dd/mm/aaaa` | Conversión explícita con `dayfirst=True` |
| Días de envío negativos | 0 | Validación cruzada de `Ship Date` ≥ `Order Date` |
| Categorías constantes | `Country` = United States | Descartada del análisis |

**Variables derivadas creadas:** `DiasEnvio`, `Anio`, `Trimestre`, `Mes`, `MesNombre`,
`AnioMes`, `AnioTrimestre`, `DiaSemana`, `EsQ4` y tres tramos de valor (de línea, de
pedido y de cliente). Las decisiones de limpieza se documentan en el registro de
intervenciones de la Fase 3 del notebook.

**Perfil de la variable de ingreso.** El valor por línea tiene mediana de
151,88 y el valor por pedido una
mediana de 151,88 y una media de
459,48: la distribución es **fuertemente asimétrica a la
derecha**, lo que justifica el uso de logaritmos, pruebas de Welch y medidas de efecto
en lugar de comparaciones simples de promedios.

---

## 5. Indicadores (KPIs)

Diez indicadores cubren las cinco preguntas clave y los seis ángulos del negocio
(crecimiento, valor de cliente, territorio, catálogo, estacionalidad y operación).

| # | KPI | Fórmula | Meta | Valor observado | Hipótesis |
|---|---|---|---|---|---|
| K1 | Ingresos totales | `SUM(Sales)` | Crecimiento ≥ 25 % anual | **2.261.537** | H1 |
| K2 | Pedidos | `DISTINCTCOUNT(Order ID)` | +60 % acumulado 2016-2018 | **4.922** (+63,0 %) | H1 |
| K3 | Ticket medio | `SUM(Sales) / DISTINCTCOUNT(Order ID)` | ≥ 450 USD | **459,48** (estable) | H1 |
| K4 | Crecimiento anual de ingresos (CAGR) | `(V2018/V2016)^(1/2) − 1` | ≥ 20 % | **25,4 %** | H1 |
| K5 | Cuota de la región líder | `Ventas región / Ventas totales` | Mantener ≥ 30 % | **31,4 %** (West) | H2 |
| K6 | Concentración (HHI por estado) | `Σ (cuota estado)²` | < 0,10 | **0,0791** · top-5 = 51,9 % | H3 |
| K7 | Tasa de recompra | `Clientes con > 1 pedido / Clientes` | ≥ 90 % | **98,4 %** | H1 |
| K8 | Índice de estacionalidad Q4 | `(venta diaria oct-dic) / (venta diaria ene-sep)` | Planificar ≥ 1,8× | **1,86×** | H4 |
| K9 | Cumplimiento logístico (≤ 4 días) | `Líneas con DiasEnvio ≤ 4 / Total` | ≥ 80 % | **59,9 %** | H5 |
| K10 | Ticket del segmento de mayor valor | `SUM(Sales) / Pedidos del segmento` | Ampliar el mix | **475,37** (Home Office) | H1 |


## 6. Hipótesis y validación estadística

Nivel de significancia α = 0,05. Se reporta el tamaño del efecto porque el volumen de
datos (4.922 pedidos) permite detectar como "significativas"
diferencias comercialmente irrelevantes.

| Hipótesis | Enunciado | Prueba | Estadístico | p-valor | Decisión | Tamaño del efecto |
|---|---|---|---|---|---|---|
| **H1** | El crecimiento lo explica el volumen, no el ticket | t de Welch sobre ln(valor de pedido) 2018 vs 2016 | t = -0,854 | 0,393 | **No se rechaza H0** | d = 0,034 (despreciable) |
| **H2** | Brecha regional significativa | ANOVA de una vía (16 trimestres por región) | F = 4,146 | 0,0098 | **Se rechaza H0** | η² = 0,172 (grande) |
| **H3** | Ingresos concentrados (Pareto) | Contraste de proporción sobre el top-3 de subcategorías | z = 2,252 | 0,0122 | **Se rechaza H0** | cuota 38,5 % vs 17,6 % |
| **H4** | Estacionalidad con pico en el cuarto trimestre | ANOVA de una vía sobre la venta diaria por mes | F = 8,563 | ≈ 1,6 × 10⁻¹⁴ | **Se rechaza H0** | η² = 0,093 (grande) |
| **H5** | El modo de envío es independiente del tamaño del pedido | Chi-cuadrado de independencia | χ² = 3,440 | 0,992 | **No se rechaza H0** | V = 0,011 (nulo) |

**Pruebas complementarias aplicadas.** Mann-Kendall sobre la serie mensual de pedidos
(tau = 0,461;
p = 4,0 × 10⁻⁶) y de
ticket (tau = -0,067;
p = 5,1 × 10⁻¹);
post-hoc de Games-Howell para el ANOVA regional y el estacional; chi-cuadrado al grano
de pedido (χ² = 11,935; p = 0,451) y t de Welch entre
Same Day y Standard Class (p = 0,670); y contraste de Shapiro-Francia
para documentar el incumplimiento de normalidad.

---

## 7. Dashboard

El tablero se compone de **19 visualizaciones**,  Todas las imágenes son vectoriales y están en
[`graficos/`](graficos/).

**Tipos de visualización utilizados:** líneas, líneas multi-serie con banda, barras
agrupadas, barras horizontales, barras apiladas 100 %, Pareto, mapa de calor, mapa
coroplético en rejilla, treemap, dispersión con tendencia OLS, histograma, caja y
bigotes, *small multiples*, cascada, embudo, *lollipop*, tarjetas de KPI y barras
divergentes.

---

## 8. Resultados

### 8.1 El crecimiento es de volumen, no de valor

Los ingresos pasaron de **459.436** en 2016 a
**722.052** en 2018: **57,2 %**
(una tasa anual compuesta de 25,4 %). Sin
embargo, el número de pedidos creció de **1.019 a
1.661 (63,0 %)**,
mientras el ticket medio cayó de **450,87** a
**434,71** (−5,7 %),
un cambio **no significativo** (p = 0,393;
IC 95 % [-17,6 %;
7,9 %]).

La descomposición multiplicativa `Ventas = Pedidos × Ticket` del crecimiento
2016-2018 es concluyente:

| Componente | Valor | Aporte al crecimiento |
|---|---|---|
| Δ Ingresos totales | 262.616,01 | 100,0 % |
| Efecto volumen (pedidos) | 289.458,21 | **110,2 %** |
| Efecto ticket (valor medio) | -26.842,20 | **−10,2 %** |

En la varianza del ingreso mensual, el **volumen explica el 78,4 %**
y el ticket el 21,6 %.
Mann-Kendall confirma la tendencia creciente de los pedidos
(p = 4,0 × 10⁻⁶)
y la tendencia decreciente del ticket
(p = 5,1 × 10⁻¹).

**Lectura de negocio.** La estrategia actual —vender a más gente, más seguido, sin
subir el valor por pedido— funciona, pero tiene un techo: el padrón de
793 clientes ya recompra en el 98,4 %
de los casos y el 81,9 % de los ingresos proviene de
clientes que repiten.

### 8.2 Brecha territorial real y accionable

| Región | Ingresos 2015-2018 | Cuota | Crecimiento 2018 vs 2016 | Ingreso trimestral medio |
|---|---|---|---|---|
| **West** | 710.220 | 31,4 % | **85,6 %** | 44.389 |
| **East** | 669.519 | 29,6 % | **37,1 %** | 41.845 |
| **Central** | 492.647 | 21,8 % | 38,3 % | 30.790 |
| **South** | 389.151 | 17,2 % | 74,3 % | 24.322 |

Oeste y Este concentran el **61,0 %**
del ingreso y son las regiones de mayor volumen (ingreso trimestral medio de
44.389 y 41.845 frente a
30.790 y 24.322). El
ANOVA confirma que las diferencias no son atribuibles al azar
(F = 4,146; p = 0,0098;
η² = 0,172, efecto grande) y el post-hoc de
Games-Howell aísla el origen del contraste:
West vs South (Δ = 20.067; p = 0,0017); East vs South (Δ = 17.523; p = 0,0186); West vs Central (Δ = 13.598; p = 0,0370).

**La brecha es de escala, no de crecimiento reciente.** Sur, la región más pequeña
(ingreso trimestral medio de 24.322), es también la de
mayor aceleración relativa (74,3 % frente a 2016) porque parte
de una base muy baja (70.076 en 2016).
**Centro** es la plaza que combina el menor volumen relativo con una tracción intermedia
sobre una base ya considerable (102.425 en 2016): por eso concentra la
mayor oportunidad absoluta y es la región prioritaria de intervención comercial.

### 8.3 Estacionalidad: la operación se define en el cuarto trimestre

- Venta diaria de octubre a diciembre: **2.730,75 USD/día**
  frente a **1.614,35 USD/día** del resto del año
  (t = 5,889; p ≈ 9,3 × 10⁻⁹;
  d = 0,52, efecto medio).
- El factor Q4 es estable en los cuatro años:
  2015: 1,74×, 2016: 1,93×, 2017: 1,90×, 2018: 1,86×.
- En 2018 el cuarto trimestre generó **278.417 en 92 días** frente a
  **443.635 en 273 días**.
- Índices mensuales extremos: **noviembre 1,65×**,
  **diciembre 1,55×** y
  **febrero 0,44×**.

### 8.4 Concentración: el catálogo se gestiona por excepción, el padrón no

| Medida de concentración | Valor |
|---|---|
| Subcategorías que explican el 80 % del ingreso | 9 de 17 (52,9 %) |
| Productos que explican el 80 % del ingreso | 418 de 1.849 (22,6 %) |
| Clientes que explican el 80 % del ingreso | 393 de 793 (49,6 %) |
| Cuota del 10 % de clientes de mayor valor | 30,9 % |
| Gini de productos / clientes / estados | 0,7306 / 0,4455 / 0,6488 |

La concentración es **alta en el catálogo y moderada entre clientes**: se puede
priorizar producto, pero no abandonar clientes.

### 8.5 Una creencia comercial descartada

El modo de envío es **independiente** del tamaño del pedido, tanto al grano de línea
(χ² = 3,440; gl = 12;
p = 0,992; V = 0,011)
como al grano de pedido (χ² = 11,935; p = 0,451). La
diferencia de ticket entre Same Day y Standard Class es de
24,48 con un intervalo que cruza el cero
([-88,34; 137,29];
p = 0,670).

### 8.6 Proyección 2019

Modelo log-lineal con índice estacional ajustado sobre 2016-2018
(R² = 0,3694; crecimiento mensual estimado
3,12 %, IC 95 %
[1,73 %;
4,52 %]):

| Escenario | Ingresos 2019 | Variación vs 2018 |
|---|---|---|
| Real 2018 | 722.052 | — |
| Conservador: anualiza el 2.º semestre de 2018 | 1.007.982 | 39,6 % |
| Base: anualiza el cierre de 2018 (Q4) | 1.168.070 | 61,8 % |
| **Modelo log-lineal + estacionalidad** | **1.128.320** | **56,3 %** |

Rango de planificación defendible: **1.007.982 a
1.168.070**.

---

## 9. Decisiones propuestas

| # | Decisión | Evidencia | Acción | Valor esperado |
|---|---|---|---|---|
| D1 | Reorientar el esfuerzo hacia **captación de clientes nuevos** | H1: volumen = 110,2 % del crecimiento; recompra ya en 98,4 % | Programa de captación con meta explícita y seguimiento mensual de clientes nuevos | Cada punto de caída de frecuencia equivale a ~22.615 anuales |
| D2 | **Intervenir Centro** como mercado prioritario | H2: p = 0,0098; Centro crece 38,3 % vs 85,6 % de Oeste | Plan de surtido, cobertura y campañas locales con meta de crecimiento comparable | Llevar Centro de 38,3 % a 55 % implica del orden de 82.400 adicionales |
| D3 | **Dimensionar la operación para el pico de fin de año** | H4: Q4 1,86× el resto (p ≈ 1,6 × 10⁻¹⁴) | Plan de capacidad escalonado de septiembre a diciembre sobre las 9 subcategorías clave | Protege el ~40 % del ingreso anual concentrado en 92 días |
| D4 | **Gestión selectiva de catálogo** | H3: 9 de 17 subcategorías = 80 %; Gini 0,7306 | Priorizar disponibilidad y campañas en las 9 familias principales | Libera esfuerzo comercial y espacio de inventario sin sacrificar facturación |
| D5 | **No priorizar el envío express por tamaño de pedido** | H5: independencia no rechazada (p = 0,992 y 0,451) | Gestionar la prioridad por costo y SLA, no por valor esperado | Evita asignar capacidad premium sin retorno medible |
| D6 | **Fijar el objetivo 2019 con dos escenarios** | Rango de proyección 1.007.982 a 1.168.070 | Comprometer el plan en el escenario conservador y usar el modelo como techo | Rango de planificación acotado y defendible |

---

## 10. Limitaciones

1. **Ausencia de `Profit`, `Quantity` y `Discount`.** No es posible calcular margen,
   utilidad, punto de equilibrio por descuento ni elasticidad precio-demanda. Todas las
   conclusiones son de **ingreso**, no de rentabilidad.
2. **Sin costo logístico.** El KPI logístico mide días de entrega, no costo por envío;
   por eso D5 no propone cambios tarifarios.
3. **2015 es un año parcial y atípico** (ticket medio 506,71
   frente a 450,87 en 2016). Se excluyó de la proyección y
   de las comparaciones de crecimiento, ancladas en 2016.
4. **Padrón de clientes preexistente.** 74,3 % de los clientes registra su
   primera compra en 2015, lo que sugiere un corte del dataset; la lectura de "captación
   decreciente" debe matizarse.
5. **Datos observacionales.** Las asociaciones no implican causalidad; la relación entre
   región y desempeño puede estar confundida por mezcla de categorías o densidad de clientes.
6. **Normalidad no cumplida.** La venta diaria y el valor de pedido son fuertemente
   asimétricos; se mitiga con logaritmos, pruebas de Welch y medidas de efecto, y el ANOVA
   se interpreta con cautela por el tamaño muestral.
7. **Cobertura limitada a Estados Unidos** y sin información de canal de venta.
8. **Proyección univariante.** No incorpora inflación, contexto macroeconómico ni acciones
   comerciales planificadas: es un escenario, no un presupuesto.

---

## 11. Conclusiones

1. **El crecimiento es real y de origen volumétrico.** Ingresos
   459.436 → 722.052
   (57,2 %; CAGR
   25,4 %), con 110,2 % del
   aumento explicado por el número de pedidos y un ticket medio estadísticamente estable
   (p = 0,393).
2. **La concentración territorial es significativa.** Oeste y Este reúnen el
   61,0 % del ingreso
   (ANOVA p = 0,0098; η² =
   0,172); Centro es la plaza prioritaria.
3. **La estacionalidad estructura la operación.** Octubre-diciembre vende
   1,86 veces más por día que el resto del año, con
   patrón estable en los cuatro años del dataset.
4. **El catálogo admite gestión selectiva; el padrón no.** 9
   subcategorías y 22,6 % del catálogo explican el 80 % del
   ingreso (Gini 0,7306), mientras la concentración entre clientes
   es moderada (Gini 0,4455).
5. **Una creencia comercial queda descartada.** El modo de envío es independiente del
   tamaño del pedido (p = 0,992 y
   0,451).
6. **El horizonte es superar el millón de dólares.** El modelo proyecta
   1.128.320 (56,3 %) y el escenario
   conservador se ubica entre 1.007.982 y
   1.168.070.

