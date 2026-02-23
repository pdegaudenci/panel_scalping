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