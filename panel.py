import streamlit as st
import pandas as pd
import pandas_ta as ta
import requests
import numpy as np
from datetime import datetime
import pytz
from scipy.signal import argrelextrema
import numpy as np

# ==============================
# CONFIG
# ==============================
SYMBOL = "BTCUSDC"
TP_BASE = 0.5      # % bruto
SL_BASE = 0.28     # % bruto
RISK_REWARD_WEIGHT = 0.4




def detectar_pivots(df, order=12):
    highs = df["high"].values
    lows = df["low"].values

    pivot_highs = argrelextrema(highs, np.greater, order=order)[0]
    pivot_lows  = argrelextrema(lows, np.less, order=order)[0]
    return pivot_highs, pivot_lows
def contar_toques(df, nivel, atr, factor=0.15):
    tolerancia = atr * factor
    toques = 0

    for _, row in df.iterrows():
        if abs(row["high"] - nivel) <= tolerancia or abs(row["low"] - nivel) <= tolerancia:
            toques += 1

    return toques
def liquidity_risk_explained(
    direction,
    price,
    atr,
    nearest_resistance,
    nearest_support,
    liquidity_attraction,
    strong_resistances,
    strong_supports
):

    report = []

    if nearest_resistance is None or nearest_support is None or atr == 0:
        return {
            "score": 40,
            "label": "NEUTRO",
            "favorable": False,
            "debug": ["Datos insuficientes de liquidez"]
        }

    risk = 0

    dist_up_atr = (nearest_resistance - price) / atr
    dist_down_atr = (price - nearest_support) / atr

    # ---------- DISTANCIA A LIQUIDEZ ----------
    if direction == "LONG":

        if dist_down_atr < 0.7:
            risk += 35
            report.append("Stops de LONGS muy cercanos → probable sweep bajista")
        elif dist_down_atr < 1.2:
            risk += 20
            report.append("Liquidez inferior cercana")

        if dist_up_atr < 1.5:
            risk -= 10
            report.append("Objetivo alcista cercano (favorece TP)")

    if direction == "SHORT":

        if dist_up_atr < 0.7:
            risk += 35
            report.append("Stops de SHORTS muy cercanos → probable sweep alcista")
        elif dist_up_atr < 1.2:
            risk += 20
            report.append("Liquidez superior cercana")

        if dist_down_atr < 1.5:
            risk -= 10
            report.append("Objetivo bajista cercano (favorece TP)")

    # ---------- ATRACCIÓN ----------
    if direction == "LONG" and liquidity_attraction == "DOWN":
        risk += 25
        report.append("El mercado quiere barrer LONGS primero")

    if direction == "SHORT" and liquidity_attraction == "UP":
        risk += 25
        report.append("El mercado quiere barrer SHORTS primero")

    # ---------- ZONAS INSTITUCIONALES ----------
    if direction == "LONG" and len(strong_resistances) >= 2:
        risk += 20
        report.append("Resistencias institucionales arriba")

    if direction == "SHORT" and len(strong_supports) >= 2:
        risk += 20
        report.append("Soportes institucionales abajo")

    risk = max(0, min(risk, 80))

    # ---------- CLASIFICACIÓN CUALITATIVA ----------
    if risk <= 15:
        label = "EXCELENTE"
        favorable = True
    elif risk <= 30:
        label = "FAVORABLE"
        favorable = True
    elif risk <= 45:
        label = "NEUTRO PELIGROSO"
        favorable = False
    elif risk <= 60:
        label = "DESFAVORABLE"
        favorable = False
    else:
        label = "MUY PELIGROSO (SWEEP PROBABLE)"
        favorable = False

    return {
        "score": risk,
        "label": label,
        "favorable": favorable,
        "debug": report
    }
# ============================================================
# MARKET LIQUIDITY RISK (sin dirección de trade)
# ============================================================
def market_liquidity_risk(
    price,
    atr,
    nearest_resistance,
    nearest_support,
    strong_resistances,
    strong_supports,
    liquidity_attraction
):

    if atr == 0:
        return 50

    # price discovery alcista
    if nearest_resistance is None:
        return 10

    # price discovery bajista
    if nearest_support is None:
        return 10

    risk = 0

    dist_up_atr = (nearest_resistance - price) / atr
    dist_down_atr = (price - nearest_support) / atr

    if dist_up_atr < 0.7:
        risk += 30
    elif dist_up_atr < 1.2:
        risk += 15

    if dist_down_atr < 0.7:
        risk += 30
    elif dist_down_atr < 1.2:
        risk += 15

    if len(strong_resistances) >= 2:
        risk += 15

    if len(strong_supports) >= 2:
        risk += 15

    if liquidity_attraction in ["UP","DOWN"]:
        risk += 10

    return max(0, min(risk, 80))
def madrid_to_utc_timestamp(fecha_str):
    madrid = pytz.timezone("Europe/Madrid")
    dt_local = madrid.localize(datetime.strptime(fecha_str, "%Y-%m-%d %H:%M"))
    dt_utc = dt_local.astimezone(pytz.utc)
    return int(dt_utc.timestamp() * 1000)
# ==============================
# BINANCE DATA
# ==============================
def get_klines(symbol, interval, limit=500):

    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    data = requests.get(url, params=params).json()

    df = pd.DataFrame(data, columns=[
        "time","open","high","low","close","volume",
        "close_time","qav","num_trades","taker_base_vol","taker_quote_vol","ignore"
    ])

    # 🔹 convertir tiempo correctamente
    df["time"] = pd.to_datetime(df["time"], unit="ms", utc=True)

    # 🔹 establecer índice temporal
    df.set_index("time", inplace=True)

    # 🔹 mantener solo OHLCV
    df = df[["open","high","low","close","volume"]].astype(float)

    # ordenar por seguridad
    df.sort_index(inplace=True)

    return df
@st.cache_data(ttl=10)  # evita bloquear Binance
def cargar_datos():
    df_1m = get_klines(SYMBOL, "1m")
    df_5m = get_klines(SYMBOL, "5m")
    return df_1m, df_5m
df_1m, df_5m = cargar_datos()
# ======================================================
# CARGA DE DATOS SOLO PARA VALIDACIÓN MULTITIMEFRAME
# ======================================================

@st.cache_data(ttl=60)
def cargar_datos_mtf():

    mtf_1m  = get_klines(SYMBOL, "1m", 500)
    mtf_5m  = get_klines(SYMBOL, "5m", 500)
    mtf_15m = get_klines(SYMBOL, "15m", 500)
    mtf_1h  = get_klines(SYMBOL, "1h", 500)

    return mtf_1m, mtf_5m, mtf_15m, mtf_1h
mtf_1m, mtf_5m, mtf_15m, mtf_1h = cargar_datos_mtf()
def preparar_tf(df):

    # -------- ADX + DI --------
    if "adx" not in df.columns:
        adx = ta.adx(df["high"], df["low"], df["close"], length=14)
        df["adx"] = adx["ADX_14"]
        df["di_plus"] = adx["DMP_14"]
        df["di_minus"] = adx["DMN_14"]

    # -------- RSI --------
    if "rsi" not in df.columns:
        df["rsi"] = ta.rsi(df["close"], length=14)

    # -------- EMAs --------
    if "ema9" not in df.columns:
        df["ema9"] = ta.ema(df["close"], length=9)

    if "ema20" not in df.columns:
        df["ema20"] = ta.ema(df["close"], length=20)

    if "ema50" not in df.columns:
        df["ema50"] = ta.ema(df["close"], length=50)

    if "ema200" not in df.columns:
        df["ema200"] = ta.ema(df["close"], length=200)

    # -------- ATR --------
    if "atr" not in df.columns:
        df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)

    return df
mtf_1m  = preparar_tf(mtf_1m)
mtf_5m  = preparar_tf(mtf_5m)
mtf_15m = preparar_tf(mtf_15m)
mtf_1h  = preparar_tf(mtf_1h)

# ===== EMAs 5m =====
mtf_5m["ema9"]  = ta.ema(mtf_5m["close"], length=9)
mtf_5m["ema20"] = ta.ema(mtf_5m["close"], length=20)
mtf_5m["ema50"] = ta.ema(mtf_5m["close"], length=50)
last5_m = mtf_5m.iloc[-1]

ema9_5m  = last5_m["ema9"]
ema20_5m = last5_m["ema20"]
ema50_5m = last5_m["ema50"]

price5m  = last5_m["close"]
def emas_abiertas_5m(direccion, ema9, ema20, ema50, price):

    # orden direccional
    if direccion == "LONG":
        orden_correcto = ema9 > ema20 > ema50
    else:
        orden_correcto = ema9 < ema20 < ema50

    # distancias (lo realmente importante)
    dist_1 = abs(ema9 - ema20) / price
    dist_2 = abs(ema20 - ema50) / price

    # umbral empírico (probado en BTC 1m/5m)
    abiertas = (dist_1 > 0.00035) and (dist_2 > 0.00035)

    return orden_correcto and abiertas, dist_1, dist_2
def evaluar_mtf(direccion):

    def check(cond, texto, valor):
        return {"ok": cond, "texto": texto, "valor": valor}

    resultado = {}
    valido_global = True

    # ===== 1H =====
    last = mtf_1h.iloc[-1]
    prev = mtf_1h.iloc[-2]
    checks = []

    if direccion == "LONG":
        checks.append(check(last.ema50 > last.ema200, "EMA50 > EMA200", f"{last.ema50:.1f} vs {last.ema200:.1f}"))
        checks.append(check(last.di_plus > last.di_minus, "DI+ domina", f"{last.di_plus:.1f} vs {last.di_minus:.1f}"))
        checks.append(check(last.adx >= 18, "ADX ≥ 18", f"{last.adx:.1f}"))
        checks.append(check(last.rsi > 50, "RSI > 50", f"{last.rsi:.1f}"))
        checks.append(check(last.atr >= prev.atr, "ATR no decreciente", f"{last.atr:.1f} vs {prev.atr:.1f}"))
    else:
        checks.append(check(last.ema50 < last.ema200, "EMA50 < EMA200", f"{last.ema50:.1f} vs {last.ema200:.1f}"))
        checks.append(check(last.di_minus > last.di_plus, "DI- domina", f"{last.di_minus:.1f} vs {last.di_plus:.1f}"))
        checks.append(check(last.adx >= 18, "ADX ≥ 18", f"{last.adx:.1f}"))
        checks.append(check(last.rsi < 50, "RSI < 50", f"{last.rsi:.1f}"))
        checks.append(check(last.atr >= prev.atr, "ATR no decreciente", f"{last.atr:.1f} vs {prev.atr:.1f}"))

    valido_1h = all(c["ok"] for c in checks)
    resultado["1H"] = (valido_1h, checks)
    if not valido_1h:
        valido_global = False

    # ===== 15M =====
    last = mtf_15m.iloc[-1]
    prev = mtf_15m.iloc[-2]
    checks = []

    if direccion == "LONG":
        checks.append(check(last.close > last.ema20, "Precio > EMA20", f"{last.close:.1f}"))
        checks.append(check(last.adx > prev.adx, "ADX subiendo", f"{last.adx:.1f} vs {prev.adx:.1f}"))
        checks.append(check(last.rsi > 50, "RSI > 50", f"{last.rsi:.1f}"))
        checks.append(check(last.di_plus > last.di_minus, "DI+ domina", f"{last.di_plus:.1f} vs {last.di_minus:.1f}"))
    else:
        checks.append(check(last.close < last.ema20, "Precio < EMA20", f"{last.close:.1f}"))
        checks.append(check(last.adx > prev.adx, "ADX subiendo", f"{last.adx:.1f} vs {prev.adx:.1f}"))
        checks.append(check(last.rsi < 50, "RSI < 50", f"{last.rsi:.1f}"))
        checks.append(check(last.di_minus > last.di_plus, "DI- domina", f"{last.di_minus:.1f} vs {last.di_plus:.1f}"))

    valido_15m = all(c["ok"] for c in checks)
    resultado["15M"] = (valido_15m, checks)
    if not valido_15m:
        valido_global = False

    # ===== 5M =====
    last = mtf_5m.iloc[-1]
    ema9 = ta.ema(mtf_5m["close"], length=9).iloc[-1]

    checks = []

    if direccion == "LONG":
        checks.append(check(ema9 > last.ema20 > last.ema50, "Abanico alcista", f"{ema9:.1f}>{last.ema20:.1f}>{last.ema50:.1f}"))
        checks.append(check(last.adx > 20, "ADX > 20", f"{last.adx:.1f}"))
        checks.append(check(last.di_plus > last.di_minus, "DI+ domina", f"{last.di_plus:.1f} vs {last.di_minus:.1f}"))
    else:
        checks.append(check(ema9 < last.ema20 < last.ema50, "Abanico bajista", f"{ema9:.1f}<{last.ema20:.1f}<{last.ema50:.1f}"))
        checks.append(check(last.adx > 20, "ADX > 20", f"{last.adx:.1f}"))
        checks.append(check(last.di_minus > last.di_plus, "DI- domina", f"{last.di_minus:.1f} vs {last.di_plus:.1f}"))

    valido_5m = all(c["ok"] for c in checks)
    resultado["5M"] = (valido_5m, checks)
    if not valido_5m:
        valido_global = False

    return valido_global, resultado
def agrupar_zonas(niveles, tolerancia_pct=0.0008):
    """
    Agrupa niveles cercanos en zonas de liquidez institucional
    """
    if len(niveles) == 0:
        return []

    niveles = sorted(niveles)
    zonas = []
    zona_actual = [niveles[0]]

    for lvl in niveles[1:]:
        ref = np.mean(zona_actual)

        # si el nivel está cerca → pertenece a la misma zona
        if abs(lvl - ref) / ref < tolerancia_pct:
            zona_actual.append(lvl)
        else:
            zonas.append((min(zona_actual), max(zona_actual)))
            zona_actual = [lvl]

    zonas.append((min(zona_actual), max(zona_actual)))
    return zonas
# ==============================
# INDICADORES 5M vb
# ==============================
df_1m["roc"] = ta.roc(df_1m["close"], length=5)
adx = ta.adx(df_5m["high"], df_5m["low"], df_5m["close"], length=14)
df_5m["adx"] = adx["ADX_14"]
df_5m["di_plus"] = adx["DMP_14"]
df_5m["di_minus"] = adx["DMN_14"]
df_1m["vol_ma"] = df_1m["volume"].rolling(20).mean()
df_1m["vol_strength"] = df_1m["volume"] / df_1m["vol_ma"]
df_5m["rsi"] = ta.rsi(df_5m["close"], length=14)

supertrend = ta.supertrend(df_5m["high"], df_5m["low"], df_5m["close"], length=10, multiplier=3)
df_5m["st_dir"] = supertrend["SUPERTd_10_3.0"]

df_5m["upper"] = df_5m["high"].rolling(100).max()
df_5m["lower"] = df_5m["low"].rolling(100).min()
df_5m["mid"] = (df_5m["upper"] + df_5m["lower"]) / 2

# ==============================
# INDICADORES 1M
# ==============================
df_1m["rsi"] = ta.rsi(df_1m["close"], length=9)
# ============================================================
# NUEVOS INDICADORES DE CONTEXTO DE MERCADO
# ============================================================

# -------- EMAs 1m (microestructura) --------
df_1m["ema20"] = ta.ema(df_1m["close"], length=20)
df_1m["ema50"] = ta.ema(df_1m["close"], length=50)

# -------- EMA 200 en 5m (dirección dominante) --------
df_5m["ema200"] = ta.ema(df_5m["close"], length=200)

# -------- VWAP (control institucional) --------
df_1m["vwap"] = ta.vwap(
    high=df_1m["high"],
    low=df_1m["low"],
    close=df_1m["close"],
    volume=df_1m["volume"]
)

# -------- ATR (energía del mercado) --------
df_1m["atr"] = ta.atr(df_1m["high"], df_1m["low"], df_1m["close"], length=14)

# -------- Volatilidad relativa --------
df_1m["volatility"] = df_1m["atr"] / df_1m["close"]
# ============================================================
# DETECTOR DE RÉGIMEN DE MERCADO
# ============================================================

# pendiente EMA200 5m (dirección real del mercado)
ema200_slope = df_5m["ema200"].iloc[-1] - df_5m["ema200"].iloc[-6]

atr_mean = df_1m["atr"].rolling(50).mean().iloc[-1]
atr_now = df_1m["atr"].iloc[-1]


# -------- Zonas de liquidez (swing highs/lows) --------
df_1m["swing_high"] = df_1m["high"].rolling(20).max()
df_1m["swing_low"] = df_1m["low"].rolling(20).min()
# -------- Compresión de volatilidad --------
bb = ta.bbands(df_1m["close"], length=20, std=2)
df_1m["bb_width"] = (bb["BBU_20_2.0"] - bb["BBL_20_2.0"]) / df_1m["close"]
# ==============================
# ÚLTIMOS VALORES
# ==============================
last5 = df_5m.iloc[-1]
last1 = df_1m.iloc[-1]
roc = last1["roc"]
bb_width = last1["bb_width"]
adx_5m = last5["adx"]
di_plus = last5["di_plus"]
di_minus = last5["di_minus"]
rsi_5m = last5["rsi"]
st_dir = last5["st_dir"]
price_5m = last5["close"]

upper = last5["upper"]
lower = last5["lower"]
mid = last5["mid"]

rsi_1m = last1["rsi"]
price_1m = last1["close"]
# ==============================
# CONTEXTO ACTUAL
# ==============================
ema20 = last1["ema20"]
ema50 = last1["ema50"]
vwap = last1["vwap"]
atr = last1["atr"]
volatility = last1["volatility"]
swing_high = last1["swing_high"]
swing_low = last1["swing_low"]
ema200_5m = last5["ema200"]

# relación del precio
above_vwap = price_1m > vwap
above_ema200 = price_5m > ema200_5m

# compresión de EMAs
ema_bullish_stack = ema20 > ema50
ema_bearish_stack = ema20 < ema50
# Clasificación de régimen
if adx_5m < 18 and atr_now < atr_mean*0.9:
    market_regime = "RANGO"
elif adx_5m < 22 and abs(ema200_slope) < 5:
    market_regime = "TRANSICIÓN"
elif adx_5m >= 22 and atr_now >= atr_mean:
    market_regime = "EXPANSIÓN"
elif adx_5m > 25 and abs(ema200_slope) > 8:
    market_regime = "TENDENCIA"
else:
    market_regime = "NEUTRO"


# ==============================
# FASE
# ==============================
if st_dir == 1 and adx_5m > 22 and di_plus > di_minus:
    fase = "ALCISTA"
elif st_dir == -1 and adx_5m > 22 and di_minus > di_plus:
    fase = "BAJISTA"
elif 15 <= adx_5m <= 22:
    fase = "TRANSICIÓN"
else:
    fase = "RANGO"

# ==============================
# VALIDACIÓN ESPACIO
# ==============================
espacio_long = price_5m <= lower or price_5m > upper
espacio_short = price_5m >= upper or price_5m < lower

# ==============================
# AGOTAMIENTO
# ==============================
candle_size = df_1m["high"].iloc[-1] - df_1m["low"].iloc[-1]
avg_size = (df_1m["high"] - df_1m["low"]).rolling(20).mean().iloc[-1]

vela_extendida = candle_size > 1.5 * avg_size
adx_cayendo = df_5m["adx"].iloc[-1] < df_5m["adx"].iloc[-2] < df_5m["adx"].iloc[-3]

no_agotamiento = not vela_extendida and not adx_cayendo

# ==============================
# TIMING
# ==============================
long_timing = rsi_1m > 52
short_timing = rsi_1m < 48

# ============================================================
# VALIDACIÓN FINAL DE SETUP CON CONTEXTO
# ============================================================

estructura_long = above_ema200 and above_vwap and ema_bullish_stack
estructura_short = (not above_ema200) and (not above_vwap) and ema_bearish_stack

long_valido = (
    fase in ["ALCISTA","TRANSICIÓN"]
    and espacio_long
    and no_agotamiento
    and long_timing
    and estructura_long
)

short_valido = (
    fase in ["BAJISTA","TRANSICIÓN"]
    and espacio_short
    and no_agotamiento
    and short_timing
    and estructura_short
)
# ==============================
# TP / SL AUTOMÁTICO
# ==============================
def calcular_trailing(adx, price):
    if adx > 30:
        return 0.18
    elif adx > 25:
        return 0.20
    else:
        return None

trailing = calcular_trailing(adx_5m, price_1m)
st.write("Trailing activo:", trailing if trailing else "No")

# ============================================================
# PROBABILIDAD AVANZADA (MODELO DE CONTEXTO)
# ============================================================

score = 50

# -------- Fuerza de tendencia --------
if adx_5m > 25:
    score += 15
elif adx_5m < 18:
    score -= 15

# -------- Estructura mayor --------
if above_ema200:
    score += 10
else:
    score -= 10

# -------- Control institucional --------
if (long_valido and above_vwap) or (short_valido and not above_vwap):
    score += 10
else:
    score -= 10

# -------- Microestructura --------
if ema_bullish_stack and long_valido:
    score += 8
elif ema_bearish_stack and short_valido:
    score += 8
else:
    score -= 8

# -------- Energía del mercado (ATR vs TP) --------
tp_distance = price_1m * (TP_BASE/100)
atr_ratio = atr / tp_distance

if 0.5 <= atr_ratio <= 1.2:
    score += 12
elif atr_ratio < 0.35:
    score -= 15

# -------- Liquidez cercana --------
dist_to_high = abs(swing_high - price_1m)/price_1m
dist_to_low = abs(price_1m - swing_low)/price_1m

if long_valido and dist_to_high < 0.003:
    score -= 12
if short_valido and dist_to_low < 0.003:
    score -= 12
## ==========================================================
# LIQUIDITY ENGINE (UNIFICADO)
# ==========================================================

price = price_1m

# -------- 1) Detectar pivots relevantes --------
pivot_highs, pivot_lows = detectar_pivots(df_1m)

liquidity_above = []
liquidity_below = []

for i in pivot_highs:
    if df_1m.iloc[i]["vol_strength"] > 1.5:
        liquidity_above.append(df_1m.iloc[i]["high"])

for i in pivot_lows:
    if df_1m.iloc[i]["vol_strength"] > 1.5:
        liquidity_below.append(df_1m.iloc[i]["low"])


# -------- 2) Nearest liquidity levels --------
resistances = [lvl for lvl in liquidity_above if lvl > price]
supports = [lvl for lvl in liquidity_below if lvl < price]

nearest_resistance = min(resistances) if len(resistances) > 0 else None
nearest_support = max(supports) if len(supports) > 0 else None


# -------- 3) Distancias --------
if nearest_resistance is not None:
    dist_up = nearest_resistance - price
    dist_up_pct = dist_up / price
else:
    dist_up = None
    dist_up_pct = None

if nearest_support is not None:
    dist_down = price - nearest_support
    dist_down_pct = dist_down / price
else:
    dist_down = None
    dist_down_pct = None


# -------- 4) Fuerza estructural (LuxAlgo swings) --------
strong_resistances = []
strong_supports = []

for lvl in liquidity_above:
    touches = contar_toques(df_1m.tail(300), lvl, atr)
    if touches >= 3:
        strong_resistances.append(lvl)

for lvl in liquidity_below:
    touches = contar_toques(df_1m.tail(300), lvl, atr)
    if touches >= 3:
        strong_supports.append(lvl)


# -------- 5) Liquidity Attraction --------
if nearest_resistance is None and nearest_support is None:
    liquidity_attraction = "NONE"

elif nearest_support is None:
    liquidity_attraction = "UP"

elif nearest_resistance is None:
    liquidity_attraction = "DOWN"

else:
    up_score = 1 / dist_up_pct if dist_up_pct else 0
    down_score = 1 / dist_down_pct if dist_down_pct else 0

    if nearest_resistance in strong_resistances:
        up_score *= 1.4

    if nearest_support in strong_supports:
        down_score *= 1.4

    liquidity_attraction = "UP" if up_score > down_score else "DOWN"


# -------- 6) Market Clean --------
market_clean = True

if dist_up_pct is not None and dist_up_pct < 0.0015:
    market_clean = False

if dist_down_pct is not None and dist_down_pct < 0.0015:
    market_clean = False
market_lrs = market_liquidity_risk(
    price_1m,
    atr,
    nearest_resistance,
    nearest_support,
    strong_resistances,
    strong_supports,
    liquidity_attraction
)

score = 50

# Fuerza
if adx_5m > 25:
    score += 15
elif adx_5m < 18:
    score -= 15

# Estructura mayor
if above_ema200:
    score += 10
else:
    score -= 10

# VWAP institucional
if (price_1m > vwap and fase == "ALCISTA") or (price_1m < vwap and fase == "BAJISTA"):
    score += 10
else:
    score -= 10

# Microestructura
if ema_bullish_stack or ema_bearish_stack:
    score += 8

# Energía
tp_distance = price_1m * (TP_BASE/100)
atr_ratio = atr / tp_distance

if 0.5 <= atr_ratio <= 1.2:
    score += 12
elif atr_ratio < 0.35:
    score -= 15

# Liquidez cercana
if nearest_resistance and (nearest_resistance-price_1m)/price_1m < 0.003:
    score -= 12
if nearest_support and (price_1m-nearest_support)/price_1m < 0.003:
    score -= 12

probabilidad = max(20, min(score, 95))
# ============================================================
# VALOR ESPERADO (EXPECTED VALUE)
# ============================================================
tp_gain = TP_BASE
sl_loss = SL_BASE

p = probabilidad / 100

EV = (p * tp_gain) - ((1 - p) * sl_loss)
# ==============================
# STREAMLIT UI
# ==============================
st.title("📊 DASHBOARD OPERATIVO BTC")

col1, col2, col3 = st.columns(3)

col1.metric("FASE 5M", fase)
col2.metric("ADX 5M", round(adx_5m,2))
col3.metric("RSI 1M", round(rsi_1m,2))

st.subheader("Validación")
st.write("Espacio LONG (5m):", espacio_long)
st.write("Espacio SHORT (5m):", espacio_short)
st.write("No agotamiento (1m + 5m):", no_agotamiento)
st.subheader("🌍 Régimen de Mercado")
st.write("Estado actual:", market_regime)

if market_regime == "RANGO":
    st.error("Mercado lateral — alto riesgo de stops")
elif market_regime == "TRANSICIÓN":
    st.warning("Mercado inestable")
elif market_regime == "EXPANSIÓN":
    st.success("Movimiento limpio probable")
elif market_regime == "TENDENCIA":
    st.success("Alta continuidad direccional")
st.subheader("🧱 Compresión de Volatilidad")

st.write("Bollinger Width:", round(bb_width,4))

if bb_width < 0.002:
    st.error("Alta compresión — NO OPERAR")
elif bb_width < 0.004:
    st.warning("Mercado apretado")
else:
    st.success("Volatilidad suficiente")
st.subheader("⚡ Momentum del Precio")

st.write("ROC 1m:", round(roc,3))

if roc > 0.08:
    st.success("Momentum alcista fuerte")
elif roc < -0.08:
    st.success("Momentum bajista fuerte")
else:
    st.warning("Momentum débil")
st.subheader("🧠 Contexto de Mercado")
st.write("Precio vs VWAP:", "Encima (alcista)" if above_vwap else "Debajo (bajista)")
st.write("Precio vs EMA200 5m:", "Encima (tendencia alcista)" if above_ema200 else "Debajo (tendencia bajista)")
st.write("Stack EMAs 1m:", "Alcista" if ema_bullish_stack else "Bajista")

st.subheader("📊 Volatilidad (ATR)")

st.write("ATR actual:", round(atr,2))

if atr < 25:
    st.error("Volatilidad baja — difícil alcanzar TP")
elif atr < 40:
    st.warning("Volatilidad moderada")
elif atr < 70:
    st.success("Volatilidad saludable para scalping")
else:
    st.info("Alta volatilidad — movimientos agresivos")

st.write("Relación ATR / TP:", round(atr_ratio,2))
if atr_ratio < 0.4:
    st.error("Mercado demasiado lento para TP 0.5%")
elif atr_ratio <= 1.2:
    st.success("Energía suficiente para alcanzar TP")
elif atr_ratio <= 2:
    st.warning("TP exigente para la volatilidad actual")
else:
    st.error("TP poco probable sin expansión fuerte")
# ============================================================
# 🪤 LIQUIDEZ CERCANA
# ============================================================

st.subheader("🪤 Liquidez cercana")

# --------- Superior ----------
if dist_to_high is None or np.isnan(dist_to_high):
    st.success("Liquidez superior: No existe (price discovery alcista)")
    dist_high_pct = None
else:
    dist_high_pct = dist_to_high * 100
    st.write("Distancia a liquidez superior:", round(dist_high_pct,3), "%")

    if dist_high_pct < 0.30:
        st.error("Resistencia demasiado cercana")
    elif dist_high_pct < 0.60:
        st.warning("Resistencia relativamente próxima")
    else:
        st.success("Espacio limpio al alza")

# --------- Inferior ----------
if dist_to_low is None or np.isnan(dist_to_low):
    st.success("Liquidez inferior: No existe (price discovery bajista)")
    dist_low_pct = None
else:
    dist_low_pct = dist_to_low * 100
    st.write("Distancia a liquidez inferior:", round(dist_low_pct,3), "%")

    if dist_low_pct < 0.30:
        st.error("Soporte demasiado cercano")
    elif dist_low_pct < 0.60:
        st.warning("Soporte relativamente próximo")
    else:
        st.success("Espacio limpio a la baja")

st.markdown("---")

# ============================================================
# 💧 CONTEXTO DE LIQUIDEZ
# ============================================================

st.subheader("💧 Contexto de Liquidez")

st.write("Atracción actual:", liquidity_attraction)

# Stops arriba
if dist_up_pct is None:
    st.success("Stops arriba: no hay liquidez (continuación alcista probable)")
else:
    st.write("Distancia stops arriba:", round(dist_up_pct*100,3), "%")

# Stops abajo
if dist_down_pct is None:
    st.success("Stops abajo: no hay liquidez (continuación bajista probable)")
else:
    st.write("Distancia stops abajo:", round(dist_down_pct*100,3), "%")

# Estado mercado
if market_clean:
    st.success("Mercado limpio → continuidad probable")
else:
    st.error("Mercado sucio → probable barrida antes del movimiento")

st.markdown("---")
# ============================================================
# 💧 PONDERACIÓN DE LIQUIDEZ (micro-riesgo inmediato)
# ============================================================

st.subheader("💧 Ponderación de Liquidez")

micro_risk = False

if dist_up_pct is not None and dist_up_pct < 0.0025:
    st.warning("Stops muy cerca arriba → posible sweep alcista inmediato")
    micro_risk = True

if dist_down_pct is not None and dist_down_pct < 0.0025:
    st.warning("Stops muy cerca abajo → posible sweep bajista inmediato")
    micro_risk = True

if not micro_risk:
    st.success("No hay liquidez inmediata peligrosa")

st.markdown("---")
# ============================================================
# 💧 PANEL 1 — CONTEXTO DE LIQUIDEZ (Microestructura)
# ============================================================

st.markdown("---")
st.subheader("💧 Contexto de Liquidez (Microestructura)")

# ---- Protección ante NaN ----
# ---- Protección inteligente ----
if atr is None or atr == 0:
    st.warning("ATR no disponible.")
else:

    col1, col2 = st.columns(2)

    # =============================
    # Liquidez Superior
    # =============================
    with col1:

        if nearest_resistance is None:
            st.metric("Liquidez arriba (ATR)", "∞")
            st.success("No existe liquidez por encima → expansión alcista (price discovery)")
            dist_up_atr = None
        else:
            dist_up_atr = (nearest_resistance - price_1m) / atr
            st.metric("Liquidez arriba (ATR)", round(dist_up_atr, 2))

            if dist_up_atr < 0.7:
                st.error("Liquidez MUY cercana arriba → probable sweep alcista")
            elif dist_up_atr < 1.2:
                st.warning("Zona de riesgo arriba")
            else:
                st.success("Espacio limpio arriba")

    # =============================
    # Liquidez Inferior
    # =============================
    with col2:

        if nearest_support is None:
            st.metric("Liquidez abajo (ATR)", "∞")
            st.success("No existe liquidez por debajo → expansión bajista (price discovery)")
            dist_down_atr = None
        else:
            dist_down_atr = (price_1m - nearest_support) / atr
            st.metric("Liquidez abajo (ATR)", round(dist_down_atr, 2))

            if dist_down_atr < 0.7:
                st.error("Liquidez MUY cercana abajo → probable sweep bajista")
            elif dist_down_atr < 1.2:
                st.warning("Zona de riesgo abajo")
            else:
                st.success("Espacio limpio abajo")

    # ========================================================
    # 🧲 ATRACCIÓN INMEDIATA DE LIQUIDEZ
    # ========================================================

    st.markdown("### 🧲 Intención Probable del Mercado")

    if liquidity_attraction == "UP":
        st.info("El mercado probablemente buscará stops de SHORTS primero (barrida alcista)")
    elif liquidity_attraction == "DOWN":
        st.info("El mercado probablemente buscará stops de LONGS primero (barrida bajista)")
    else:
        st.write("No hay sesgo claro de liquidez")

    # ========================================================
    # 🧱 FUERZA ESTRUCTURAL (Swings tipo LuxAlgo)
    # ========================================================

 # ========================================================
    # 🧱 FUERZA ESTRUCTURAL (Swings tipo LuxAlgo)
    # ========================================================

    st.markdown("### 🧱 Fuerza Estructural")

    resistance_zones = agrupar_zonas(strong_resistances)
    support_zones = agrupar_zonas(strong_supports)

    st.write("Zonas institucionales detectadas:")

    # ---------------- RESISTENCIAS ----------------
    if len(resistance_zones) > 0:
        st.write("🔴 Resistencias institucionales:")
        for zmin, zmax in resistance_zones:
            distancia = ((zmin - price_1m) / price_1m) * 100
            st.error(f"Zona: {round(zmin,2)} → {round(zmax,2)}  |  Distancia: {round(distancia,3)}%")

            # alerta operativa
            if 0 < distancia < 0.40:
                st.warning("⚠ Muy cercana al precio → probable rechazo o barrida")

    else:
        st.success("No hay resistencias institucionales cercanas")


    # ---------------- SOPORTES ----------------
    if len(support_zones) > 0:
        st.write("🟢 Soportes institucionales:")
        for zmin, zmax in support_zones:
            distancia = ((price_1m - zmax) / price_1m) * 100
            st.success(f"Zona: {round(zmin,2)} → {round(zmax,2)}  |  Distancia: {round(distancia,3)}%")

            if 0 < distancia < 0.40:
                st.warning("⚠ Muy cercano al precio → posible sweep antes de subir")

    else:
        st.success("No hay soportes institucionales cercanos")
    # ========================================================
    # ⚠ LIQUIDITY RISK SCORE
    # ========================================================

    st.markdown("### ⚠ Riesgo de Liquidez")

    st.metric("Liquidity Risk Score", f"{market_lrs}/80")

    if market_lrs < 20:
        st.success("Bajo riesgo de barrida → entorno favorable para continuidad")
    elif market_lrs < 40:
        st.info("Riesgo moderado → mercado operable con precaución")
    elif market_lrs < 60:
        st.warning("Alto riesgo → posible fake move antes del TP")
    else:
        st.error("Muy alto riesgo → probable sweep antes del movimiento real")

    # ========================================================
    # 🧠 MARKET CLEAN / DIRTY (Decisión rápida)
    # ========================================================

    st.markdown("### 🧠 Estado Operativo del Mercado")

    market_clean = market_lrs < 35

    if market_clean:
        st.success("Mercado relativamente limpio → continuidad posible")
    else:
        st.error("Mercado sucio → alta probabilidad de barrida antes de continuar")
st.subheader("Señal Final")

if long_valido:
    st.success("🚀 LONG VÁLIDO")
    st.write("TP:", round(tp_long,2))
    st.write("SL:", round(sl_long,2))

elif short_valido:
    st.error("🔻 SHORT VÁLIDO")
    st.write("TP:", round(tp_short,2))
    st.write("SL:", round(sl_short,2))

else:
    st.warning("⏳ ESPERAR")

st.subheader("Probabilidad estimada (MTF 5m + 1m)")
st.progress(probabilidad / 100)

st.write(f"{probabilidad}%")
st.markdown("---")
st.subheader("📐 Valor Esperado del Trade (EV)")

st.write("EV:", round(EV,4), "%")

if EV > 0.12:
    st.success("Ventaja matemática clara")
elif EV > 0:
    st.info("Trade ligeramente favorable")
else:
    st.error("Trade con esperanza negativa — evitar")
st.subheader("🔄 Actualización de mercado")

colA, colB = st.columns([2,1])

with colA:
    st.write("Pulsa para recargar datos actuales de Binance y recalcular la señal.")

with colB:
    if st.button("Actualizar mercado ahora"):
        st.cache_data.clear()   # borra cache
        st.rerun()              # reinicia script
import os
from datetime import datetime

def log_signal(tipo, prob):
    file = "signals_log.csv"
    row = {
        "time": datetime.now(),
        "tipo": tipo,
        "fase": fase,
        "adx": adx_5m,
        "rsi_1m": rsi_1m,
        "probabilidad": prob
    }
    df = pd.DataFrame([row])
    if os.path.exists(file):
        df.to_csv(file, mode="a", header=False, index=False)
    else:
        df.to_csv(file, index=False)
import os
from datetime import datetime

def log_signal(tipo, prob):
    file = "signals_log.csv"
    row = {
        "time": datetime.now(),
        "tipo": tipo,
        "fase": fase,
        "adx": adx_5m,
        "rsi_1m": rsi_1m,
        "probabilidad": prob
    }
    df = pd.DataFrame([row])
    if os.path.exists(file):
        df.to_csv(file, mode="a", header=False, index=False)
    else:
        df.to_csv(file, index=False)

if long_valido:
    log_signal("LONG", probabilidad)

elif short_valido:
    log_signal("SHORT", probabilidad)
def filtrar_horario(df, start=13, end=17):
    df = df.copy()
    df["time"] = pd.to_datetime(df.index, unit="ms", errors="ignore")
    df["hour"] = df["time"].dt.hour
    return df[(df["hour"] >= start) & (df["hour"] <= end)]

def condiciones_similares(df, direction):
    condiciones = []

    for i in range(50, len(df)-15):
        row = df.iloc[i]

        if direction == "SHORT":
            cond = (
                20 <= row["adx"] <= 30 and
                row["di_minus"] > row["di_plus"] and
                row["rsi"] < 50
            )
        else:
            cond = (
                20 <= row["adx"] <= 30 and
                row["di_plus"] > row["di_minus"] and
                row["rsi"] > 50
            )

        if cond:
            condiciones.append(i)

    return condiciones
def probabilidad_historica(df, direction):
    indices = condiciones_similares(df, direction)

    wins = 0
    total = 0

    for i in indices:
        entry = df["close"].iloc[i]

        if direction == "SHORT":
            tp = entry * 0.995
            sl = entry * 1.0035
        else:
            tp = entry * 1.005
            sl = entry * 0.9965

        future = df.iloc[i+1:i+15]

        hit_tp = False
        hit_sl = False

        for _, row in future.iterrows():
            if direction == "SHORT":
                if row["low"] <= tp:
                    hit_tp = True
                    break
                if row["high"] >= sl:
                    hit_sl = True
                    break
            else:
                if row["high"] >= tp:
                    hit_tp = True
                    break
                if row["low"] <= sl:
                    hit_sl = True
                    break

        if hit_tp:
            wins += 1
        if hit_tp or hit_sl:
            total += 1

    return (wins / total * 100) if total > 0 else 0

def backtest(df, direction="long"):
    wins = 0
    losses = 0
    capital = 100

    for i in range(50, len(df)-10):
        entry = df["close"].iloc[i]
        tp = entry * (1 + TP_BASE/100) if direction=="long" else entry * (1 - TP_BASE/100)
        sl = entry * (1 - SL_BASE/100) if direction=="long" else entry * (1 + SL_BASE/100)

        future = df.iloc[i+1:i+10]

        hit_tp = False
        hit_sl = False

        for _, row in future.iterrows():
            if direction=="long":
                if row["high"] >= tp:
                    hit_tp = True
                    break
                if row["low"] <= sl:
                    hit_sl = True
                    break
            else:
                if row["low"] <= tp:
                    hit_tp = True
                    break
                if row["high"] >= sl:
                    hit_sl = True
                    break

        if hit_tp:
            wins += 1
            capital *= 1.005
        elif hit_sl:
            losses += 1
            capital *= 0.997

    total = wins + losses
    winrate = wins / total * 100 if total > 0 else 0

    return wins, losses, winrate, capital
st.subheader("Backtest rápido 1M (últimos datos)")

wins, losses, winrate, final_capital = backtest(df_1m, "long")

st.write("Wins:", wins)
st.write("Losses:", losses)
st.write("Winrate:", round(winrate,2), "%")
st.write("Capital final simulado:", round(final_capital,2))


# ============================================================
# PANEL 2
# ============================================================
df_15m = get_klines(SYMBOL, "15m")
df_1h = get_klines(SYMBOL, "1h")
def validar_mtf(direccion):

    debug = []
    score = 0

    last1h = df_1h.iloc[-1]
    last15 = df_15m.iloc[-1]
    last5  = df_5m.iloc[-1]
    last1  = df_1m.iloc[-1]

    # =========================================================
    # 1H — PERMISO
    # =========================================================
    permiso_1h = True

    if direccion == "LONG":

        if last1h["ema50"] > last1h["ema200"]:
            score += 10
            debug.append("1H EMA alineadas ✔")
        else:
            permiso_1h = False
            debug.append("1H EMA no alineadas ✖")

        if last1h["di_plus"] > last1h["di_minus"]:
            score += 10
            debug.append("1H DI+ domina ✔")
        else:
            permiso_1h = False

        if last1h["adx"] >= 18:
            score += 8
        else:
            permiso_1h = False

        if last1h["rsi"] > 50:
            score += 6
        else:
            permiso_1h = False

    else:

        if last1h["ema50"] < last1h["ema200"]:
            score += 10
        else:
            permiso_1h = False

        if last1h["di_minus"] > last1h["di_plus"]:
            score += 10
        else:
            permiso_1h = False

        if last1h["adx"] >= 18:
            score += 8
        else:
            permiso_1h = False

        if last1h["rsi"] < 50:
            score += 6
        else:
            permiso_1h = False


    # =========================================================
    # 15M — MOVIMIENTO REAL
    # =========================================================

    if direccion == "LONG":

        if last15["close"] > last15["ema20"]:
            score += 8

        if last15["adx"] > df_15m["adx"].iloc[-2]:
            score += 10
            debug.append("15m ADX subiendo ✔")

        if last15["di_plus"] > last15["di_minus"]:
            score += 8

    else:

        if last15["close"] < last15["ema20"]:
            score += 8

        if last15["adx"] > df_15m["adx"].iloc[-2]:
            score += 10

        if last15["di_minus"] > last15["di_plus"]:
            score += 8


    # =========================================================
    # 5M — PRE IMPULSO
    # =========================================================

    ema9 = ta.ema(df_5m["close"], 9).iloc[-1]
    ema20 = ta.ema(df_5m["close"], 20).iloc[-1]
    ema50 = ta.ema(df_5m["close"], 50).iloc[-1]

    if direccion == "LONG":
        if ema9 > ema20 > ema50:
            score += 12
    else:
        if ema9 < ema20 < ema50:
            score += 12

    # =========================================================
    # 1M — EJECUCIÓN
    # =========================================================

    if direccion == "LONG":
        if last1["close"] > df_1m["high"].iloc[-2]:
            score += 8
    else:
        if last1["close"] < df_1m["low"].iloc[-2]:
            score += 8


    score = max(0, min(score, 100))

    valido = score >= 65 and permiso_1h

    return score, valido, debug
# ======================
# INDICADORES 1H
# ======================

df_1h["ema50"] = ta.ema(df_1h["close"], 50)
df_1h["ema200"] = ta.ema(df_1h["close"], 200)

adx_1h = ta.adx(df_1h["high"], df_1h["low"], df_1h["close"], 14)
df_1h["adx"] = adx_1h["ADX_14"]
df_1h["di_plus"] = adx_1h["DMP_14"]
df_1h["di_minus"] = adx_1h["DMN_14"]
df_1h["rsi"] = ta.rsi(df_1h["close"], 14)
df_1h["atr"] = ta.atr(df_1h["high"], df_1h["low"], df_1h["close"], 14)

# ======================
# INDICADORES 15M
# ======================

df_15m["ema20"] = ta.ema(df_15m["close"], 20)
df_15m["ema50"] = ta.ema(df_15m["close"], 50)

adx_15m = ta.adx(df_15m["high"], df_15m["low"], df_15m["close"], 14)
df_15m["adx"] = adx_15m["ADX_14"]
df_15m["di_plus"] = adx_15m["DMP_14"]
df_15m["di_minus"] = adx_15m["DMN_14"]
df_15m["rsi"] = ta.rsi(df_15m["close"], 14)

def probabilidad_tp_real(
    direccion,
    prob_mercado,
    prob_entry,
    rr,
    atr_ratio,
    adx,
    rsi,
    lrs,
    market_regime,
    liquidity_attraction,
    ema_stack,
    above_vwap
):

    debug = []
    p = (prob_mercado * 0.55 + prob_entry * 0.45)

    debug.append(("Base entorno+entrada", f"{p:.1f}", "Neutro"))

    # -------------------------
    # R:R
    # -------------------------
    if rr >= 1.6:
        p += 8
        debug.append(("R:R óptimo", rr, "+8"))
    elif rr >= 1.3:
        p += 4
        debug.append(("R:R bueno", rr, "+4"))
    elif rr < 1.0:
        p -= 12
        debug.append(("R:R malo", rr, "-12"))

    # -------------------------
    # ATR energía
    # -------------------------
    if 0.5 <= atr_ratio <= 1.3:
        p += 10
        debug.append(("ATR suficiente", atr_ratio, "+10"))
    elif atr_ratio < 0.35:
        p -= 18
        debug.append(("ATR insuficiente", atr_ratio, "-18"))
    elif atr_ratio > 2.2:
        p -= 8
        debug.append(("ATR demasiado volátil", atr_ratio, "-8"))

    # -------------------------
    # ADX tendencia
    # -------------------------
    if adx > 28:
        p += 8
        debug.append(("ADX fuerte", adx, "+8"))
    elif adx < 18:
        p -= 12
        debug.append(("ADX débil", adx, "-12"))

    # -------------------------
    # RSI timing
    # -------------------------
    if direccion == "LONG":
        if rsi > 56:
            p += 6
            debug.append(("Timing RSI alcista", rsi, "+6"))
        elif rsi < 50:
            p -= 8
            debug.append(("RSI contra tendencia", rsi, "-8"))
    else:
        if rsi < 44:
            p += 6
            debug.append(("Timing RSI bajista", rsi, "+6"))
        elif rsi > 50:
            p -= 8
            debug.append(("RSI contra tendencia", rsi, "-8"))

    # -------------------------
    # Liquidez
    # -------------------------
    penalty = lrs * 0.35
    p -= penalty
    debug.append(("Liquidity Risk", lrs, f"-{round(penalty,1)}"))

    if direccion == "LONG" and liquidity_attraction == "DOWN":
        p -= 6
        debug.append(("Atracción contraria (barrida)", liquidity_attraction, "-6"))

    if direccion == "SHORT" and liquidity_attraction == "UP":
        p -= 6
        debug.append(("Atracción contraria (barrida)", liquidity_attraction, "-6"))

    # -------------------------
    # Estructura institucional
    # -------------------------
    if ema_stack and above_vwap:
        p += 6
        debug.append(("Estructura institucional a favor", "EMA+VWAP", "+6"))

    # -------------------------
    # Régimen de mercado
    # -------------------------
    if market_regime == "TENDENCIA":
        p += 10
        debug.append(("Régimen tendencia", market_regime, "+10"))
    elif market_regime == "EXPANSIÓN":
        p += 6
        debug.append(("Régimen expansión", market_regime, "+6"))
    elif market_regime == "RANGO":
        p -= 20
        debug.append(("Mercado lateral", market_regime, "-20"))

    p = max(5, min(p, 95))

    return p, debug

def rating_score(score):
    if score < 55:
        return "MALO"
    elif score < 65:
        return "DÉBIL"
    elif score < 75:
        return "ACEPTABLE"
    elif score < 85:
        return "BUENO"
    else:
        return "EXCELENTE"


st.write("Mínimo recomendado para operar: 65%")

st.markdown("---")
st.title("🧠 Evaluador Integral de Trade")

with st.form("trade_eval"):

    entrada = st.number_input("Precio de entrada", value=float(price_1m))
    direccion = st.selectbox("Dirección", ["LONG", "SHORT"])

    evaluar = st.form_submit_button("Evaluar Trade")


if evaluar:
        # ============================================================
    # 0️⃣ VALIDACIÓN MULTI TIMEFRAME INSTITUCIONAL
    # ============================================================

    st.markdown("---")
    st.header("🧠 Análisis Multi-TimeFrame")

    mtf_valido, detalle = evaluar_mtf(direccion)

    if mtf_valido:
        st.success(f"{direccion} VÁLIDO")
    else:
        st.error(f"{direccion} INVÁLIDO")
    # =========================================================
# FILTRO PRINCIPAL — EMAs ABIERTAS 5m
# =========================================================

    emas_ok, d1, d2 = emas_abiertas_5m(
        direccion,
        ema9_5m,
        ema20_5m,
        ema50_5m,
        price5m
    )

    st.markdown("### 🔑 Filtro de Impulso Institucional (5m)")

    colA, colB, colC = st.columns(3)

    colA.metric("EMA9-EMA20 distancia", f"{d1*100:.3f}%")
    colB.metric("EMA20-EMA50 distancia", f"{d2*100:.3f}%")
    colC.metric("EMAs abiertas", "SI" if emas_ok else "NO")

    if emas_ok:
        st.success("✔ Estructura de impulso válida — compradores dominando")
    else:
        st.error("✖ Sin expansión de EMAs → alta probabilidad de stop loss")
    for tf, (valido_tf, checks) in detalle.items():

        st.subheader(f"{tf} ({'VÁLIDO' if valido_tf else 'INVÁLIDO'})")

        for c in checks:
            if c["ok"]:
                st.markdown(
                    f"<span style='color:lightgreen'>✔ {c['texto']} : {c['valor']} (OK)</span>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<span style='color:red'>✖ {c['texto']} : {c['valor']} (KO)</span>",
                    unsafe_allow_html=True
                )
        # ============================================================
        # 1) CONDICIÓN DEL MERCADO (Reemplaza Panel 1)
        # ============================================================

        st.subheader("📊 1) Condición del Mercado")

        score_market = 0
        mercado_ok = True
        motivos = []

    # ADX
    if adx_5m > 25:
        score_market += 30
        motivos.append("Mercado con fuerza (ADX>25)")
    elif adx_5m > 22:
        score_market += 20
        motivos.append("Impulso moderado")
    else:
        mercado_ok = False
        motivos.append("Mercado débil (ADX bajo)")

    # Fase estructural
    if fase == "RANGO":
        mercado_ok = False
        motivos.append("Mercado en rango")
    else:
        score_market += 20
        motivos.append(f"Fase {fase}")

    # Agotamiento
    if vela_extendida:
        mercado_ok = False
        motivos.append("Vela 1m extendida (posible clímax)")

    if adx_cayendo:
        mercado_ok = False
        motivos.append("ADX cayendo (pérdida de fuerza)")

    prob_mercado = min(score_market, 90)

    st.progress(prob_mercado/100)
    st.write(f"Probabilidad entorno favorable: {prob_mercado}%")

    for m in motivos:
        st.write("•", m)

    # ============================================================
    # 2) VALIDACIÓN DE LA ENTRADA 
    # ============================================================

    st.subheader("🎯 2) Validación de Entrada (Timing Microestructural)")

    score_entry = 50
    debug_entry = []

    # ======================================================
    # 1) MOMENTUM INMEDIATO (ROC)
    # ======================================================
    if direccion == "LONG":
        if roc > 0.04:
            score_entry += 12
            debug_entry.append(("Momentum inmediato alcista", roc, "+12"))
            st.success("Momentum alcista real")
        elif roc < 0:
            score_entry -= 12
            debug_entry.append(("Momentum contrario", roc, "-12"))
            st.error("Momentum en contra")

    else:
        if roc < -0.04:
            score_entry += 12
            debug_entry.append(("Momentum inmediato bajista", roc, "+12"))
            st.success("Momentum bajista real")
        elif roc > 0:
            score_entry -= 12
            debug_entry.append(("Momentum contrario", roc, "-12"))
            st.error("Momentum en contra")

    # ======================================================
    # 2) RSI (solo confirmación, no base)
    # ======================================================
    if direccion == "LONG":
        if 52 <= rsi_1m <= 68:
            score_entry += 8
            debug_entry.append(("RSI saludable", rsi_1m, "+8"))
        elif rsi_1m > 72:
            score_entry -= 10
            debug_entry.append(("RSI sobreextendido", rsi_1m, "-10"))
            st.warning("Posible entrada tardía")
    else:
        if 32 <= rsi_1m <= 48:
            score_entry += 8
            debug_entry.append(("RSI saludable", rsi_1m, "+8"))
        elif rsi_1m < 28:
            score_entry -= 10
            debug_entry.append(("RSI sobreextendido", rsi_1m, "-10"))
            st.warning("Posible entrada tardía")

    # ======================================================
    # 3) MICRO TENDENCIA (EMA STACK)
    # ======================================================
    if direccion == "LONG" and ema_bullish_stack:
        score_entry += 10
        debug_entry.append(("Microtendencia a favor", "EMA20>EMA50", "+10"))
    elif direccion == "SHORT" and ema_bearish_stack:
        score_entry += 10
        debug_entry.append(("Microtendencia a favor", "EMA20<EMA50", "+10"))
    else:
        score_entry -= 12
        debug_entry.append(("Microtendencia contraria", "EMA stack", "-12"))
        st.error("Microestructura en contra")

    # ======================================================
    # 4) POSICIÓN VS VWAP (institucional)
    # ======================================================
    if (direccion == "LONG" and above_vwap) or (direccion == "SHORT" and not above_vwap):
        score_entry += 10
        debug_entry.append(("Precio control institucional", "VWAP", "+10"))
    else:
        score_entry -= 14
        debug_entry.append(("Contra VWAP", "VWAP", "-14"))
        st.error("Operar contra VWAP")

    # ======================================================
    # 5) ENERGÍA DEL MOVIMIENTO (ATR vs TP)
    # ======================================================
    if 0.5 <= atr_ratio <= 1.3:
        score_entry += 10
        debug_entry.append(("Energía suficiente", atr_ratio, "+10"))
    elif atr_ratio < 0.35:
        score_entry -= 18
        debug_entry.append(("Movimiento sin energía", atr_ratio, "-18"))
        st.error("Mercado demasiado lento")

    # ======================================================
    # 6) BOLLINGER COMPRESSION (evitar fake moves)
    # ======================================================
    if bb_width < 0.002:
        score_entry -= 15
        debug_entry.append(("Compresión extrema", bb_width, "-15"))
        st.error("Probable fake breakout")

    # ======================================================
    # RESULTADO FINAL
    # ======================================================
    prob_entry = max(15, min(score_entry, 95))

    st.write(f"Calidad de la entrada: {prob_entry}%")

    st.markdown("### 🔬 Evaluación del timing")
    for nombre, valor, impacto in debug_entry:
        if "-" in impacto:
            st.error(f"✖ {nombre} | Valor: {valor} | Impacto: {impacto}")
        else:
            st.success(f"✔ {nombre} | Valor: {valor} | Impacto: {impacto}")

    # ============================================================
    # 3) GESTIÓN DEL TRADE (Risk Manager real)
    # ============================================================

    st.subheader("🛡 3) Gestión del Trade")

   # ============================================================
    # GESTIÓN PROFESIONAL DEL TRADE (Risk Engine)
    # ============================================================

    tp_percent = 0.5 / 100
    max_risk = 0.0035   # 0.35% riesgo máximo permitido

    # ===== LONG =====
    if direccion == "LONG":

        # Take Profit fijo del sistema
        tp = entrada * (1 + tp_percent)

        # Stop estructural (últimos swings 5m)
        structural_sl = df_5m["low"].iloc[-5:].min()

        # Stop máximo permitido por modelo estadístico
        max_sl = entrada * (1 - max_risk)

        # Usamos el más cercano a la entrada (control de riesgo)
        sl = max(structural_sl, max_sl)

        # Break Even
        be = entrada * 1.0025   # +0.25%


    # ===== SHORT =====
    else:

        tp = entrada * (1 - tp_percent)

        structural_sl = df_5m["high"].iloc[-5:].max()
        max_sl = entrada * (1 + max_risk)

        sl = min(structural_sl, max_sl)

        be = entrada * 0.9975   # -0.25%


    # ============================================================
    # TRAILING INTELIGENTE
    # ============================================================

    if adx_5m > 32:
        trailing = 0.15   # mercado fuerte → trailing agresivo
    elif adx_5m > 26:
        trailing = 0.18
    elif adx_5m > 22:
        trailing = 0.22
    else:
        trailing = None   # rango → no trailing


    # ============================================================
    # MOSTRAR EN UI
    # ============================================================

    col1, col2, col3 = st.columns(3)

    col1.metric("TP objetivo", round(tp, 2))
    col2.metric("SL controlado", round(sl, 2))
    col3.metric("Break Even", round(be, 2))

    if trailing:
        st.success(f"Trailing activo: {trailing}%")
    else:
        st.warning("Trailing desactivado (mercado sin tendencia)")
    risk_pct = abs((entrada - sl) / entrada) * 100
    reward_pct = abs((tp - entrada) / entrada) * 100
    rr = reward_pct / risk_pct if risk_pct > 0 else 0

    # ---- Clasificación riesgo ----
    if risk_pct < 0.22:
        risk_label = "Muy bajo (ideal)"
    elif risk_pct < 0.35:
        risk_label = "Controlado"
    elif risk_pct < 0.55:
        risk_label = "Alto"
    else:
        risk_label = "Peligroso"

    # ---- Clasificación reward ----
    if reward_pct < 0.35:
        reward_label = "Poco atractivo"
    elif reward_pct < 0.55:
        reward_label = "Normal"
    else:
        reward_label = "Excelente"

    # ---- Clasificación R:R ----
    if rr < 1.0:
        rr_label = "Malo"
    elif rr < 1.3:
        rr_label = "Justo"
    elif rr < 1.6:
        rr_label = "Bueno"
    else:
        rr_label = "Óptimo"

 
    lrs_info = liquidity_risk_explained(
    direccion,
    entrada,
    atr,
    nearest_resistance,
    nearest_support,
    liquidity_attraction,
    strong_resistances,
    strong_supports
    )

    lrs = lrs_info["score"]
    prob_tp, debug_info = probabilidad_tp_real(
        direccion,
        prob_mercado,
        prob_entry,
        rr,
        atr_ratio,
        adx_5m,
        rsi_1m,
        lrs,
        market_regime,
        liquidity_attraction,
        ema_bullish_stack if direccion=="LONG" else ema_bearish_stack,
        above_vwap
    )
    st.write(f"Riesgo real: {round(risk_pct,3)}%")
    st.write(f"Beneficio potencial: {round(reward_pct,3)}%")
    st.write(f"R:R real: {round(rr,2)}")
    st.subheader("🎯 Probabilidad real de alcanzar TP")

    st.progress(prob_tp/100)

    if prob_tp < 50:
        st.error(f"{prob_tp:.1f}% → Probabilidad BAJA (trade desfavorable)")
    elif prob_tp < 58:
        st.warning(f"{prob_tp:.1f}% → Probabilidad débil")
    elif prob_tp < 65:
        st.info(f"{prob_tp:.1f}% → Operable pero ajustado")
    elif prob_tp < 75:
        st.success(f"{prob_tp:.1f}% → Buen trade")
    else:
        st.success(f"{prob_tp:.1f}% → Alta probabilidad de TP")
       # ============================================================
    # 4) DECISIÓN FINAL (Motor de aprobación)
    # ============================================================

    st.subheader("🧾 Decisión Final")

    base_score = (prob_mercado*0.55 + prob_entry*0.45)

    p = base_score / 100
    p_adjusted = p * (1 - (lrs/120))   # penalización más realista
    final_score = p_adjusted * 100
    rating = rating_score(final_score)

    
    if final_score < 55:
        st.error("❌ NO OPERAR — Entorno o entrada desfavorable")
    elif final_score < 65:
        st.warning("⚠ OPERABLE CON PRECAUCIÓN")
    elif final_score < 75:
        st.info("✅ BUEN SETUP")
    else:
        st.success("🔥 SETUP DE ALTA PROBABILIDAD")

    st.write(f"Score total: {round(final_score,1)}% (Calidad del setup) — {rating}")
    st.markdown("### 🧠 Motor de decisión (debug)")

    for nombre, valor, impacto in debug_info:

        if "-" in impacto:
            st.error(f"✖ {nombre} | Valor: {valor} | Impacto: {impacto}")
        elif "+" in impacto:
            st.success(f"✔ {nombre} | Valor: {valor} | Impacto: {impacto}")
        else:
            st.info(f"• {nombre} | Valor: {valor}")
    st.subheader("💧 Liquidity Risk Analysis")

    st.metric("LRS", f"{lrs}/80  ({lrs_info['label']})")

    if lrs_info["favorable"]:
        st.success("La liquidez favorece el trade")
    else:
        st.error("La liquidez perjudica el trade")
 






# ============================================================
# PANEL 3 — EVALUADOR HISTÓRICO DE TRADE
# ============================================================
import requests
import pytz
from datetime import datetime, timedelta
import time
def get_historical_klines(symbol, interval, start_time, end_time):

    url = "https://api.binance.com/api/v3/klines"
    all_data = []

    while start_time < end_time:

        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_time,
            "endTime": end_time,
            "limit": 1000
        }

        data = requests.get(url, params=params).json()

        if not data:
            break

        all_data.extend(data)

        start_time = data[-1][0] + 1
        time.sleep(0.2)  # evitar rate limit

    df = pd.DataFrame(all_data, columns=[
        "time","open","high","low","close","volume",
        "_","_","_","_","_","_"
    ])

    df["time"] = pd.to_datetime(df["time"], unit="ms", utc=True)
    df.set_index("time", inplace=True)
    df.sort_index(inplace=True)
    df = df[["open","high","low","close","volume"]].astype(float)

    return df
from datetime import datetime, timedelta
import pytz

madrid = pytz.timezone("Europe/Madrid")

# momento actual
now_utc = datetime.utcnow()

# cuántos días históricos quieres analizar
days_back = 5

start_utc = now_utc - timedelta(days=days_back)

start_ms = int(start_utc.timestamp() * 1000)
end_ms = int(now_utc.timestamp() * 1000)

SYMBOL = "BTCUSDC"

df_1m_full = get_historical_klines(SYMBOL, "1m", start_ms, end_ms)
df_5m_full = get_historical_klines(SYMBOL, "5m", start_ms, end_ms)
import pandas_ta as ta

# ----- 5M -----
adx = ta.adx(df_5m_full["high"], df_5m_full["low"], df_5m_full["close"], length=14)
df_5m_full["adx"] = adx["ADX_14"]
df_5m_full["di_plus"] = adx["DMP_14"]
df_5m_full["di_minus"] = adx["DMN_14"]

df_5m_full["rsi"] = ta.rsi(df_5m_full["close"], length=14)

supertrend = ta.supertrend(df_5m_full["high"], df_5m_full["low"], df_5m_full["close"], length=10, multiplier=3)
df_5m_full["st_dir"] = supertrend["SUPERTd_10_3.0"]

df_5m_full["upper"] = df_5m_full["high"].rolling(100).max()
df_5m_full["lower"] = df_5m_full["low"].rolling(100).min()

# ----- 1M -----
df_1m_full["rsi"] = ta.rsi(df_1m_full["close"], length=9)

df_1m_full["candle_size"] = df_1m_full["high"] - df_1m_full["low"]
df_1m_full["avg_size"] = df_1m_full["candle_size"].rolling(20).mean()
st.markdown("---")
st.title("📜 Panel 3 — Evaluador Histórico de Trade")

st.write("Permite analizar qué habría indicado el sistema en un momento pasado.")

madrid = pytz.timezone("Europe/Madrid")

col1, col2 = st.columns(2)

fecha = col1.date_input("Fecha (Madrid)")
hora_txt = col2.text_input(
    "Hora exacta (Madrid)  HH:MM:SS",
    value="14:30:00"
)

direccion_hist = st.selectbox("Dirección del trade", ["LONG", "SHORT"])

evaluar_hist = st.button("Analizar momento histórico")

# ============================================================
# EJECUCIÓN
# ============================================================

if evaluar_hist:

    # ----- Convertir hora Madrid -> UTC -----
    from datetime import datetime
    import pytz

    try:
        hora_obj = datetime.strptime(hora_txt, "%H:%M:%S").time()
    except:
        st.error("Formato de hora incorrecto. Usa HH:MM:SS (ej: 14:37:25)")
        st.stop()

    dt_madrid = madrid.localize(datetime.combine(fecha, hora_obj))
    dt_utc = dt_madrid.astimezone(pytz.utc)
    st.write("Hora Madrid:", dt_madrid)
    st.write("Hora UTC buscada:", dt_utc)

    st.write("Primer dato disponible:", df_1m_full.index.min())
    st.write("Último dato disponible:", df_1m_full.index.max())
    st.info(f"Hora evaluada UTC: {dt_utc}")

    # Buscar la vela inmediatamente anterior
    try:
        vela_1m = df_1m_full.loc[:dt_utc].iloc[-1]
        vela_5m = df_5m_full.loc[:dt_utc].iloc[-1]
    except:
        st.error("No hay datos suficientes en ese momento histórico.")
        st.stop()

    # ============================================================
    # RECONSTRUIR MÉTRICAS
    # ============================================================

    adx_hist = vela_5m["adx"]
    di_plus_hist = vela_5m["di_plus"]
    di_minus_hist = vela_5m["di_minus"]
    rsi_1m_hist = vela_1m["rsi"]

    # Fase histórica
    if vela_5m["st_dir"] == 1 and adx_hist > 22 and di_plus_hist > di_minus_hist:
        fase_hist = "ALCISTA"
    elif vela_5m["st_dir"] == -1 and adx_hist > 22 and di_minus_hist > di_plus_hist:
        fase_hist = "BAJISTA"
    elif 15 <= adx_hist <= 22:
        fase_hist = "TRANSICIÓN"
    else:
        fase_hist = "RANGO"

    # Detectar agotamiento
    vela_extendida_hist = vela_1m["candle_size"] > 1.5 * vela_1m["avg_size"]

    # ADX cayendo
    ult_adx = df_5m_full.loc[:dt_utc]["adx"].tail(3)
    adx_cayendo_hist = ult_adx.iloc[-1] < ult_adx.iloc[-2] < ult_adx.iloc[-3]

    # ============================================================
    # SCORE MERCADO
    # ============================================================

    score_market = 0

    if adx_hist > 25:
        score_market += 30
    elif adx_hist > 22:
        score_market += 20

    if fase_hist != "RANGO":
        score_market += 20

    if not vela_extendida_hist:
        score_market += 15

    prob_mercado = min(score_market, 90)

    # ============================================================
    # SCORE ENTRADA
    # ============================================================

    score_entry = 50

    if direccion_hist == "LONG" and rsi_1m_hist > 52:
        score_entry += 15
    elif direccion_hist == "SHORT" and rsi_1m_hist < 48:
        score_entry += 15
    else:
        score_entry -= 15

    if (direccion_hist == "LONG" and di_plus_hist > di_minus_hist) or \
       (direccion_hist == "SHORT" and di_minus_hist > di_plus_hist):
        score_entry += 15
    else:
        score_entry -= 15

    if vela_extendida_hist:
        score_entry -= 10

    if adx_cayendo_hist:
        score_entry -= 15

    prob_entry = max(20, min(score_entry, 90))

    final_score = (prob_mercado + prob_entry) / 2

    # ============================================================
    # CALCULAR TP / SL HISTÓRICO
    # ============================================================

    entry_price = vela_1m["close"]
    tp_percent = 0.5 / 100

    if direccion_hist == "LONG":
        tp_price = entry_price * (1 + tp_percent)
        sl_price = df_5m_full.loc[:dt_utc]["low"].tail(10).min()
    else:
        tp_price = entry_price * (1 - tp_percent)
        sl_price = df_5m_full.loc[:dt_utc]["high"].tail(10).max()

    # ============================================================
    # VERIFICAR RESULTADO REAL
    # ============================================================
    # encontrar posición de la vela histórica
    pos = df_1m_full.index.get_indexer([dt_utc], method="pad")[0]

    # tomar las 60 velas siguientes reales
    future_1m = df_1m_full.iloc[pos+1:pos+61]
    # Inicializar resultados
    hit_tp = False
    hit_sl = False
# ============================================================
# MAXIMO MOVIMIENTO FAVORABLE (MFE)
# ============================================================

    if len(future_1m) < 5:
        st.warning("No hay suficientes datos posteriores para medir movimiento.")
        max_price = None
        max_tp_pct = None

    else:
        if direccion_hist == "LONG":
            max_price = future_1m["high"].max()
            max_tp_pct = ((max_price - entry_price) / entry_price) * 100
        else:
            max_price = future_1m["low"].min()
            max_tp_pct = ((entry_price - max_price) / entry_price) * 100

    for _, row in future_1m.iterrows():

        if direccion_hist == "LONG":
            if row["high"] >= tp_price:
                hit_tp = True
                break
            if row["low"] <= sl_price:
                hit_sl = True
                break
        else:
            if row["low"] <= tp_price:
                hit_tp = True
                break
            if row["high"] >= sl_price:
                hit_sl = True
                break

    # ============================================================
    # OUTPUT UI
    # ============================================================

    st.subheader("📊 Resultado del Sistema en ese Momento")

    colA, colB, colC = st.columns(3)
    colA.metric("Fase", fase_hist)
    colB.metric("ADX", round(adx_hist,2))
    colC.metric("RSI 1m", round(rsi_1m_hist,2))

    st.progress(final_score/100)
    st.write(f"Probabilidad estimada TP en ese momento: {round(final_score,1)}%")

    st.subheader("🎯 Resultado real posterior")

    if hit_tp:
        st.success("El Take Profit se habría alcanzado")
    elif hit_sl:
        st.error("El Stop Loss se habría alcanzado primero")
    else:
        st.warning("Ni TP ni SL alcanzados en la siguiente hora")

    st.write(f"Precio entrada: {round(entry_price,2)}")
    st.write(f"TP histórico: {round(tp_price,2)}")
    st.write(f"SL estructural histórico: {round(sl_price,2)}")
    st.subheader("📈 Movimiento máximo posterior")

    if max_price is not None:
        st.subheader("📈 Movimiento máximo posterior (MFE)")

        st.write(f"Precio máximo favorable alcanzado: {round(max_price,2)}")
        st.write(f"Movimiento máximo a favor: {round(max_tp_pct,3)} %")
    else:
        st.warning("No se puede calcular MFE por falta de velas posteriores.")
    st.write(f"Movimiento máximo: {round(max_tp_pct,3)} %")