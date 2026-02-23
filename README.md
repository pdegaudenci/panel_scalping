# 🧠 BTC Scalping Quantitative Trade Evaluator

Sistema de evaluación cuantitativa para operaciones de **scalping intradía en BTC/USDC** utilizando datos de Binance, análisis técnico multi-temporal (MTF) y gestión dinámica de riesgo.

⚠️ **Este sistema NO predice el precio del Bitcoin.**
Evalúa si las condiciones actuales del mercado ofrecen **ventaja estadística** para ejecutar un trade corto (≈0.5%).

El objetivo es responder:

> “¿Si entro ahora, es más probable que el precio alcance el Take Profit antes que el Stop Loss?”

---

# Arquitectura General

El sistema se divide en dos capas operativas dentro de la interfaz:

## 1) Evaluación del Mercado (Market Condition Engine)

## 2) Evaluación del Trade (Entry + Risk Engine)

El motor final combina ambas evaluaciones para aprobar o rechazar la operación.

---

# Fuente de Datos

### API utilizada

`Binance REST API`

```
GET /api/v3/klines
```

### Datos obtenidos

Velas OHLCV:

| Campo  | Descripción        |
| ------ | ------------------ |
| open   | Precio de apertura |
| high   | Máximo             |
| low    | Mínimo             |
| close  | Cierre             |
| volume | Volumen            |

### Temporalidades usadas

| Temporalidad | Función                |
| ------------ | ---------------------- |
| 1 minuto     | Timing de entrada      |
| 5 minutos    | Estructura del mercado |

Los datos JSON se transforman en `pandas.DataFrame` y se convierten a tipo `float` para procesamiento cuantitativo.

---

# Transformaciones en Python

1. Conversión JSON → DataFrame
2. Series temporales indexadas
3. Cálculo de indicadores técnicos
4. Cálculo de métricas estadísticas
5. Clasificación del régimen de mercado
6. Evaluación probabilística heurística

---

# Indicadores Utilizados (`pandas_ta`)

## ADX — Average Directional Index

`ta.adx(high, low, close, length=14)`

Mide la **fuerza de la tendencia**, no la dirección.

Salidas:

* ADX → intensidad del movimiento
* DI+ → presión compradora
* DI− → presión vendedora

Uso en el sistema:

* Detectar mercado operable
* Activar trailing dinámico
* Clasificar fase del mercado

---

## RSI — Relative Strength Index

`ta.rsi(close, length=14)` (5m)
`ta.rsi(close, length=9)` (1m)

En este sistema NO se usa como sobrecompra/sobreventa.

Función:

* 5m → equilibrio oferta/demanda
* 1m → detector de impulso inmediato (timing de entrada)

---

## Supertrend

`ta.supertrend(high, low, close, length=10, multiplier=3)`

Basado en ATR (volatilidad).

Salida:

* +1 tendencia alcista
* −1 tendencia bajista

Se utiliza para determinar la dirección estructural.

---

# Transformaciones Estadísticas Propias

## Canal de Liquidez

```
upper = max(high últimos 100 velas 5m)
lower = min(low últimos 100 velas 5m)
```

Representa ≈8 horas de mercado.

Detecta zonas de:

* liquidez
* acumulación
* posibles rebotes

---

## Detección de Clímax

```
vela_extendida = tamaño_actual > 1.5 × media_20_velas
```

Detecta movimientos anómalos (posibles trampas).

---

## Pérdida de Fuerza

```
adx_cayendo = ADX decreciente 3 velas consecutivas
```

Indica debilitamiento de tendencia.

---

# SECCIÓN 1 — Evaluación del Mercado

## Objetivo

Determinar si el mercado es **operable para scalping**.

No genera señal de compra/venta.
Determina si existe continuidad de movimiento a corto plazo.

### Métricas evaluadas

* ADX 5m
* Fase estructural
* Vela extendida
* ADX cayendo

## Clasificación de fase

| Fase       | Significado         |
| ---------- | ------------------- |
| ALCISTA    | compradores dominan |
| BAJISTA    | vendedores dominan  |
| TRANSICIÓN | inicio de tendencia |
| RANGO      | mercado lateral     |

## Resultado

`prob_mercado`

Interpretación:

| Probabilidad | Lectura             |
| ------------ | ------------------- |
| <55%         | mercado no operable |
| 55-65%       | débil               |
| 65-75%       | operable            |

> 75% | condiciones ideales |

Esto mide **persistencia direccional**, no predicción del precio.

---

# SECCIÓN 2 — Evaluación del Trade

Evalúa la **entrada concreta seleccionada por el usuario**.

## Timing

RSI 1m:

* LONG → RSI > 52
* SHORT → RSI < 48

## Dominancia

Comparación:

* DI+ > DI− → compradores
* DI− > DI+ → vendedores

## Stop Loss estructural

Basado en estructura real:

| Tipo  | Cálculo                    |
| ----- | -------------------------- |
| LONG  | mínimo últimas 10 velas 5m |
| SHORT | máximo últimas 10 velas 5m |

## Break Even

Protección del capital tras ≈0.3% a favor.

## Trailing dinámico

| ADX | Acción |
| --- | ------ |

> 30 | trailing corto |
> 25–30 | trailing moderado |
> <25 | sin trailing |

## Resultado

`prob_entry` → calidad de la entrada.

---

# Motor de Decisión Final

```
final_score = (prob_mercado + prob_entry) / 2
```

| Score | Acción     |
| ----- | ---------- |
| <55   | NO OPERAR  |
| 55-65 | Precaución |
| 65-75 | Buen setup |

> 75 | Alta probabilidad |

---

# Métrica Principal del Sistema

El sistema calcula:

**Probabilidad de que el precio alcance el Take Profit antes que el Stop Loss.**

No calcula:

* dirección futura
* precio objetivo
* tendencia a largo plazo

Calcula:
**ventaja estadística operativa de corto plazo.**

---

# Qué es realmente este proyecto

No es un indicador técnico.

Es un:

## Motor cuantitativo de validación de trades

Combina:

* análisis de régimen de mercado
* momentum
* estructura
* gestión de riesgo

Su función principal es **filtrar operaciones con expectativa matemática positiva** y reducir el overtrading.

---

# Uso Correcto

1. Evaluar mercado
2. Si operable → buscar entrada
3. Validar trade
4. Ejecutar solo si aprobado

---

# Conclusión

El sistema implementa un modelo heurístico de trading cuantitativo basado en confluencia multi-temporal para detectar oportunidades de scalping con continuidad estadística a corto plazo.

No intenta adivinar el mercado.

Intenta operar solo cuando el mercado ofrece ventaja.
# ⚠ Limitaciones del Sistema

Aunque el sistema implementa un modelo cuantitativo de validación de trades, presenta limitaciones inherentes al análisis técnico y al scalping intradía.

---

## 1. No es un modelo predictivo

El sistema NO:

* predice el precio futuro
* estima objetivos extendidos
* anticipa eventos macroeconómicos

Evalúa únicamente la **probabilidad condicional de continuidad de corto plazo**.

---

## 2. No incorpora datos de Order Book

El sistema no utiliza:

* profundidad de mercado (Level 2)
* flujo de órdenes (Order Flow)
* delta de volumen real
* CVD (Cumulative Volume Delta)

Por tanto, no detecta:

* absorciones institucionales
* spoofing
* desequilibrios reales de liquidez

Se basa exclusivamente en datos OHLCV históricos.

---

## 3. Dependencia de Parámetros Fijos

Parámetros actuales:

* TP fijo ≈ 0.5%
* RSI umbrales 52 / 48
* ADX umbral 22 / 25
* Ventana rolling 100 velas
* Stop estructural últimas 10 velas

Estos valores pueden no ser óptimos en todos los regímenes de mercado.

No existe optimización automática adaptativa.

---

## 4. Modelo Heurístico (No ML)

El sistema utiliza un modelo de scoring manual:

```id="z9twnc"
score = suma ponderada de condiciones
```

No está entrenado con:

* regresión logística
* modelos bayesianos
* redes neuronales
* backtesting masivo multi-año

Por lo tanto:

* la probabilidad estimada no es estadística real calibrada
* es una aproximación heurística

---

## 5. Sensibilidad a Volatilidad Extrema

En eventos como:

* noticias macro
* liquidaciones masivas
* movimientos >2% en minutos

Los indicadores técnicos tradicionales pueden reaccionar tarde.

El sistema no incluye filtros de:

* volatilidad explosiva
* spreads anómalos
* latencia API

---

## 6. No incluye Gestión de Capital

El sistema no implementa:

* position sizing dinámico
* Kelly Criterion
* gestión de drawdown
* control de exposición diaria

Evalúa la calidad del trade, no la gestión de cartera.

---

## 7. Dependencia de Calidad de Datos

La precisión depende de:

* latencia API Binance
* integridad de datos OHLCV
* continuidad temporal de velas

No incluye validación robusta de datos corruptos o incompletos.

---

# Posibles Mejoras Futuras

* Integración de Order Book y volumen delta
* Calibración estadística real con backtesting histórico
* Modelo probabilístico bayesiano
* Optimización adaptativa de parámetros
* Gestión automática de riesgo por capital
* Machine Learning supervisado

---

# Conclusión Técnica

Este sistema debe entenderse como:

> Un motor cuantitativo de filtrado de oportunidades de scalping basado en confluencia multi-temporal.

No elimina el riesgo de mercado.
Reduce la probabilidad de operar en condiciones desfavorables.

La rentabilidad dependerá de:

* disciplina operativa
* ejecución
* gestión del riesgo
* control emocional

---# ============================================================
# CONDICIONES DE EVALUACIÓN DE SETUP LONG / SHORT
# ------------------------------------------------------------
# El sistema NO genera señales por un único indicador.
# Implementa un modelo de confluencia multi-temporal (MTF)
# que valida si existe ventaja estadística suficiente para
# ejecutar un trade de scalping (TP ≈ 0.5% antes que SL).
#
# Para que una operación sea válida deben cumplirse TODAS
# las capas de evaluación simultáneamente.
#
# --------------------------
# CAPA 1 — RÉGIMEN DE MERCADO (5m)
# --------------------------
# Métricas:
#   • Supertrend (dirección)
#   • ADX(14) → fuerza de tendencia
#   • DI+ / DI- → dominancia compradores vs vendedores
#
# Objetivo:
# Determinar si el mercado está en tendencia, transición o rango.
#
# Reglas:
#   LONG permitido  → Fase ALCISTA o TRANSICIÓN
#   SHORT permitido → Fase BAJISTA o TRANSICIÓN
#
# La fase NO genera la señal.
# Solo habilita qué dirección puede tener probabilidad positiva.
#
# --------------------------
# CAPA 2 — ESPACIO OPERATIVO (5m)
# --------------------------
# Métricas:
#   • Máximo 100 velas (upper)
#   • Mínimo 100 velas (lower)
#
# Objetivo:
# Verificar que el precio tenga recorrido libre sin chocar
# zonas de liquidez recientes (máximos/mínimos de ~8h).
#
# Interpretación:
# El sistema solo opera si el precio puede desplazarse
# ~0.5% sin encontrar resistencias/soportes cercanos.
#
# --------------------------
# CAPA 3 — FILTRO DE AGOTAMIENTO (1m + 5m)
# --------------------------
# Métricas:
#   • Tamaño de vela actual vs media 20 velas (1m)
#   • Pendiente del ADX (5m)
#
# Objetivo:
# Evitar entrar al final del movimiento.
#
# Condiciones inválidas:
#   • Vela 1m extendida (>1.5x promedio) → clímax
#   • ADX cayendo en 5m → pérdida de fuerza
#
# Si ocurre cualquiera → NO OPERAR.
#
# --------------------------
# CAPA 4 — TIMING DE EJECUCIÓN (1m)
# --------------------------
# Métrica:
#   • RSI(9) en 1 minuto
#
# Objetivo:
# Detectar impulso inmediato (micro-momentum).
#
# Reglas:
#   LONG  → RSI 1m > 52
#   SHORT → RSI 1m < 48
#
# Esto actúa como gatillo de entrada.
#
# ============================================================
# DEFINICIÓN DE SETUPS
# ------------------------------------------------------------
# SETUP LONG (continuidad alcista)
# Requiere:
#   • Contexto estructural favorable (5m)
#   • Dominancia compradora
#   • Espacio operativo suficiente
#   • Sin agotamiento
#   • Impulso inmediato alcista (RSI 1m)
#
# SETUP SHORT (continuidad bajista)
# Requiere:
#   • Contexto estructural favorable (5m)
#   • Dominancia vendedora
#   • Espacio operativo suficiente
#   • Sin agotamiento
#   • Impulso inmediato bajista (RSI 1m)
#
# ------------------------------------------------------------
# IMPORTANTE:
# Este bloque NO intenta predecir el precio futuro del BTC.
# Evalúa si las condiciones actuales del mercado presentan
# persistencia direccional de corto plazo suficiente para que
# un trade alcance su Take Profit antes que su Stop Loss.
# ============================================================

# ==============================
# DECISIÓN FINAL
# ==============================
# ============================================================
# SETUP OPERATIVO DEL SISTEMA
# ------------------------------------------------------------
# El sistema opera mediante detección de "setup de continuidad".
#
# Un setup es una condición de mercado donde existe suficiente
# probabilidad estadística de que el precio continúe un movimiento
# corto (≈0.5%) sin retroceder primero hasta el Stop Loss.
#
# Existen dos setups:
#
# SETUP ALCISTA (LONG)
# Requiere:
#   1) Contexto favorable en 5m (fase ALCISTA o TRANSICIÓN)
#   2) Dominio comprador (DI+ > DI-)
#   3) Precio con espacio operativo (no en resistencia/liquidez)
#   4) Ausencia de agotamiento (no vela extendida, ADX no cayendo)
#   5) Timing en 1m (RSI 1m > 52 → impulso inmediato)
#
# SETUP BAJISTA (SHORT)
# Requiere:
#   1) Contexto favorable en 5m (fase BAJISTA o TRANSICIÓN)
#   2) Dominio vendedor (DI- > DI+)
#   3) Precio con espacio operativo (no en soporte/liquidez)
#   4) Ausencia de agotamiento
#   5) Timing en 1m (RSI 1m < 48 → impulso inmediato)
#
# IMPORTANTE:
# La FASE NO genera la señal.
# La fase solo habilita qué tipo de setup está permitido.
#
# La señal aparece únicamente cuando:
# fase + espacio + no agotamiento + timing coinciden.
#
# Es un modelo de confluencia estadística, no un indicador único.
# ============================================================

# ==============================
# PROBABILIDAD ESTIMADA
# ==============================
# ============================================================
# CONDICIONES DE EVALUACIÓN DE SETUP LONG / SHORT
# ------------------------------------------------------------
# El sistema NO genera señales por un único indicador.
# Implementa un modelo de confluencia multi-temporal (MTF)
# que valida si existe ventaja estadística suficiente para
# ejecutar un trade de scalping (TP ≈ 0.5% antes que SL).
#
# Para que una operación sea válida deben cumplirse TODAS
# las capas de evaluación simultáneamente.
#
# --------------------------
# CAPA 1 — RÉGIMEN DE MERCADO (5m)
# --------------------------
# Métricas:
#   • Supertrend (dirección)
#   • ADX(14) → fuerza de tendencia
#   • DI+ / DI- → dominancia compradores vs vendedores
#
# Objetivo:
# Determinar si el mercado está en tendencia, transición o rango.
#
# Reglas:
#   LONG permitido  → Fase ALCISTA o TRANSICIÓN
#   SHORT permitido → Fase BAJISTA o TRANSICIÓN
#
# La fase NO genera la señal.
# Solo habilita qué dirección puede tener probabilidad positiva.
#
# --------------------------
# CAPA 2 — ESPACIO OPERATIVO (5m)
# --------------------------
# Métricas:
#   • Máximo 100 velas (upper)
#   • Mínimo 100 velas (lower)
#
# Objetivo:
# Verificar que el precio tenga recorrido libre sin chocar
# zonas de liquidez recientes (máximos/mínimos de ~8h).
#
# Interpretación:
# El sistema solo opera si el precio puede desplazarse
# ~0.5% sin encontrar resistencias/soportes cercanos.
#
# --------------------------
# CAPA 3 — FILTRO DE AGOTAMIENTO (1m + 5m)
# --------------------------
# Métricas:
#   • Tamaño de vela actual vs media 20 velas (1m)
#   • Pendiente del ADX (5m)
#
# Objetivo:
# Evitar entrar al final del movimiento.
#
# Condiciones inválidas:
#   • Vela 1m extendida (>1.5x promedio) → clímax
#   • ADX cayendo en 5m → pérdida de fuerza
#
# Si ocurre cualquiera → NO OPERAR.
#
# --------------------------
# CAPA 4 — TIMING DE EJECUCIÓN (1m)
# --------------------------
# Métrica:
#   • RSI(9) en 1 minuto
#
# Objetivo:
# Detectar impulso inmediato (micro-momentum).
#
# Reglas:
#   LONG  → RSI 1m > 52
#   SHORT → RSI 1m < 48
#
# Esto actúa como gatillo de entrada.
#
# ============================================================
# DEFINICIÓN DE SETUPS
# ------------------------------------------------------------
# SETUP LONG (continuidad alcista)
# Requiere:
#   • Contexto estructural favorable (5m)
#   • Dominancia compradora
#   • Espacio operativo suficiente
#   • Sin agotamiento
#   • Impulso inmediato alcista (RSI 1m)
#
# SETUP SHORT (continuidad bajista)
# Requiere:
#   • Contexto estructural favorable (5m)
#   • Dominancia vendedora
#   • Espacio operativo suficiente
#   • Sin agotamiento
#   • Impulso inmediato bajista (RSI 1m)
#
# ------------------------------------------------------------
# IMPORTANTE:
# Este bloque NO intenta predecir el precio futuro del BTC.
# Evalúa si las condiciones actuales del mercado presentan
# persistencia direccional de corto plazo suficiente para que
# un trade alcance su Take Profit antes que su Stop Loss.
# ============================================================
# ============================================================
# PROBABILIDAD ESTIMADA (MTF 5m + 1m)
# ------------------------------------------------------------

# Representa la probabilidad de éxito OPERATIVO del setup de scalping:
# es decir, la probabilidad de que una operación abierta en este momento
# alcance el Take Profit (~0.5%) ANTES que el Stop Loss (~0.28%).
#
# La probabilidad se basa en confluencia multi-temporal (MTF):
#   • Temporalidad 5m → contexto estructural del mercado (tendencia, fuerza, régimen)
#   • Temporalidad 1m → timing de ejecución (impulso inmediato)
#
# En términos cuantitativos:
# mide la persistencia direccional de corto plazo (continuidad del movimiento)
# y la existencia de ventaja estadística para un trade de scalping.
#
# IMPORTANTE:
# No indica la dirección futura del precio.
# Indica si el mercado actual es explotable para un movimiento corto.
#
# Interpretación:
# <50%  → entorno peligroso / ruido
# 50-60% → baja ventaja estadística
# 60-70% → operable
# 70-80% → buena oportunidad
# 80-95% → setup de alta calidad
# ============================================================

COMPRESION DA EXPANSION FUERTE Y TRANSICION ES AGOTAMIENTO DE TENDENCIA
RUTOTURA DE ESTRUCTURA, ES RUPTURA DE EMA 
LINEAS DE TENDENCIA DIAGONALES, DINAMICAS SIRVEN Y EN QUE TEMPORALIDAD DEBO USARLAS TENEIENDO EJ 1 MIN

EL ACTUAL STRATEGIA SOLO DA UNA SEÑAL .
VER SI ES POSIBLE ESTIMAR PUNTOS DE RENTABILIDFAD DE UN TRADE

ANALISIS MUTITIME FRAME. EL RESULTADO DE ESTA SECCION SERA LONG O SHORT VALIDO O INVALIDO. PERO DEBAJO HABRA UNA LISTA DE CADA TIMEFRAME CON LA TEMPORALIDAD Y ENTRE PARENETESIS VALIDO O INVALIDO SEGUN EL ANALISIS DE ESA TEMPROALIDAD HAYA RESULTADO VALIDO O INVALIDO Y ADEMAS DENTRO DE CADA SECCION DE TEMPORALIDAD ESTARAN LAS CONDICIONES EVALUAQDAS CON SU VALOR Y ENTRE PARENTESIS OK EN COLOR VERDE Y KO EN ROJO. LAS REGLAS SON:
Estructura mental (muy importante)

La señal del script en 1m significa:

“Puede empezar un impulso”

Tu trabajo es comprobar si ese impulso tiene combustible institucional.

Cada timeframe responde una pregunta distinta:

TF	Pregunta
1H	¿Estoy del lado correcto del mercado?
15m	¿Los grandes están moviendo el precio?
5m	¿Va a arrancar ahora?
1m	¿Dónde ejecuto exactamente?
🔵 VALIDACIÓN COMPLETA PARA LONG

(La señal LONG del Supertrend 1m aparece)

1️⃣ Temporalidad 1 HORA — PERMISO DE MERCADO

(Si falla aquí → ignoras el trade directamente)

Debes cumplir TODAS:

EMAs

EMA50 > EMA200 ✔

ADX + DI

DI+ por encima de DI- ✔

ADX ≥ 18 ✔

RSI

RSI mayor que 50 ✔
(Mejor: 55+)

ATR

ATR plano o subiendo ✔
(si cae → mercado dormido)

👉 Si una falla → NO LONG aunque el indicador lo marque.

2️⃣ Temporalidad 15 MIN — MOVIMIENTO REAL

(Aquí detectas trampas)

Debe cumplirse:

Precio y EMAs

Precio por encima de EMA20 ✔

Mejor si también > EMA50 ✔

ADX

ADX subiendo en las últimas velas ✔
(esto es CLAVE)

RSI

RSI subiendo o >50 ✔
(si cae → distribución)

DI

DI+ dominando ✔

👉 Si ADX baja → 80% de probabilidad de falsa señal.

3️⃣ Temporalidad 5 MIN — PRE-IMPULSO

(Este timeframe decide si ganarás dinero o no)

Debe existir:

Apertura en abanico

EMA9 > EMA20 > EMA50 ✔

y separándose ✔

DI

DI+ cruzando o ya sobre DI- ✔

ADX

ADX > 20 ✔

👉 Si las EMAs están mezcladas → es rango → perderás.

4️⃣ Temporalidad 1 MIN — EJECUCIÓN

(Ahora sí miras tu señal)

Cuando aparezca LONG del script:

NO entres aún.

Espera:

pequeño retroceso

vela roja pequeña

luego vela verde que rompa el máximo previo ✔

Ahí es la entrada correcta.

🔴 VALIDACIÓN COMPLETA PARA SHORT

(es exactamente el espejo)

1️⃣ 1 HORA

EMA50 < EMA200 ✔

DI- sobre DI+ ✔

ADX ≥ 18 ✔

RSI < 50 ✔

ATR no cayendo ✔

2️⃣ 15 MIN

Precio bajo EMA20 ✔

ADX subiendo ✔

RSI cayendo ✔

DI- dominando ✔

3️⃣ 5 MIN

EMA9 < EMA20 < EMA50 ✔

separándose ✔

DI- cruzando arriba ✔

ADX > 20 ✔

4️⃣ 1 MIN

Aparece SHORT del script:

Esperas:

pequeño pullback alcista

vela verde débil

vela roja rompiendo mínimo previo ✔

Entrada.

Regla de Oro (muy importante)

Si 1H y 15m están alineados
→ el trade suele dar 200-600 puntos.

Si solo 1m está alineado
→ es casi aleatorio.

Esto es exactamente por qué a veces el mismo indicador funciona y otras te saca el SL.

No es el indicador.
Es el contexto.








COMPRESION DA EXPANSION FUERTE Y TRANSICION ES AGOTAMIENTO DE TENDENCIA
RUTOTURA DE ESTRUCTURA, ES RUPTURA DE EMA 
LINEAS DE TENDENCIA DIAGONALES, DINAMICAS SIRVEN Y EN QUE TEMPORALIDAD DEBO USARLAS TENEIENDO EJ 1 MIN

EL ACTUAL STRATEGIA SOLO DA UNA SEÑAL .
VER SI ES POSIBLE ESTIMAR PUNTOS DE RENTABILIDFAD DE UN TRADE
emas mas estructura y validación de señal supertrend

Sí — y de hecho este es el mejor filtro que puedes añadirle al Supertrend para BTC 1 minuto.

Te explico por qué:

El Supertrend detecta
👉 cambio de dirección

Pero NO sabe distinguir si el mercado:

va a iniciar una tendencia

o está dentro de un rango (que es donde te salta el SL)

Las EMAs en abanico sí lo saben.

Porque las EMAs no miden precio…
miden comportamiento colectivo de órdenes.

Cuando las EMAs se abren:
→ significa que el mercado ya está desplazándose, no solo girando.

Por eso:
Supertrend = “posible movimiento”
EMAs abanico = “movimiento real”

Y juntas funcionan MUY bien en scalping BTC.

Qué significa exactamente “abanico”

Vas a usar:

EMA 9
EMA 20
EMA 50
EMA 200

Abanico alcista REAL

Debe cumplirse:

EMA9 > EMA20 > EMA50 > EMA200
Y además:

la distancia entre ellas debe crecer (separándose).

Esto es MUY importante.

Si solo están ordenadas pero pegadas → es rango.

Abanico bajista REAL

EMA9 < EMA20 < EMA50 < EMA200

y separándose.

Cómo lo usas con tu indicador

El Supertrend te da la alerta.

Las EMAs te dan el permiso.

Entonces la nueva regla será:

NO opero ninguna señal del Supertrend si no hay abanico en 1m o 5m.

Este solo filtro suele eliminar más de la mitad de las operaciones perdedoras.

Cómo leerlo correctamente (muy importante)

Cuando aparezca:

COMPRAR (label verde)

Miras inmediatamente las EMAs:

Caso 1

Están entrelazadas
→ ignoras la señal
(esto es un rango institucional)

Caso 2

Ordenadas pero planas
→ probablemente fake breakout

Caso 3 (el bueno)

Alineadas Y separándose
→ este suele ser el movimiento de +200 a +600 puntos

Regla profesional clave

El mejor trade en BTC 1m es:

Pullback a EMA20 dentro de abanico.

No el cruce.
No la ruptura.

El retroceso.

Ahí es donde están entrando los algoritmos.

En qué timeframe debes mirar el abanico

Esto es CLAVE:

5 minutos → el bueno (tendencia real)

1 minuto → el timing

Si 5m tiene abanico y 1m te da señal
→ ese es el trade de alta probabilidad.

Si solo 1m lo tiene
→ suele ser trampa.

Conclusión

Sí, debes filtrar el Supertrend con EMAs en abanico.

De hecho, el uso correcto del indicador pasa a ser:

Supertrend
= detector de giro

EMAs abanico
= confirmación de tendencia

ADX
= confirmación de fuerza

Y juntos convierten un indicador normal en una estrategia de scalping estructurada.+


SEALES DE REVERSION D EIMPULSO