import streamlit as st
import pandas as pd
import pandas_ta as ta
import requests
import numpy as np

# ==============================
# CONFIG
# ==============================
SYMBOL = "BTCUSDC"
TP_BASE = 0.5      # % bruto
SL_BASE = 0.28     # % bruto
RISK_REWARD_WEIGHT = 0.4

# ==============================
# BINANCE DATA
# ==============================
def get_klines(symbol, interval, limit=200):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    data = requests.get(url, params=params).json()

    df = pd.DataFrame(data, columns=[
        "time","open","high","low","close","volume",
        "_","_","_","_","_","_"
    ])

    df = df[["open","high","low","close","volume"]].astype(float)
    return df

df_1m = get_klines(SYMBOL, "1m")
df_5m = get_klines(SYMBOL, "5m")

# ==============================
# INDICADORES 5M
# ==============================
adx = ta.adx(df_5m["high"], df_5m["low"], df_5m["close"], length=14)
df_5m["adx"] = adx["ADX_14"]
df_5m["di_plus"] = adx["DMP_14"]
df_5m["di_minus"] = adx["DMN_14"]

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

# ==============================
# ÚLTIMOS VALORES
# ==============================
last5 = df_5m.iloc[-1]
last1 = df_1m.iloc[-1]

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

# ==============================
# DECISIÓN FINAL
# ==============================
long_valido = fase in ["ALCISTA","TRANSICIÓN"] and espacio_long and no_agotamiento and long_timing
short_valido = fase in ["BAJISTA","TRANSICIÓN"] and espacio_short and no_agotamiento and short_timing


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

# ==============================
# PROBABILIDAD ESTIMADA
# ==============================
score = 0

if adx_5m > 25:
    score += 30
elif adx_5m > 22:
    score += 20

if fase in ["ALCISTA","BAJISTA"]:
    score += 20

if not vela_extendida:
    score += 15

if (long_valido or short_valido):
    score += 25

probabilidad = min(score, 95)

# ==============================
# STREAMLIT UI
# ==============================
st.title("📊 DASHBOARD OPERATIVO BTC")

col1, col2, col3 = st.columns(3)

col1.metric("FASE 5M", fase)
col2.metric("ADX 5M", round(adx_5m,2))
col3.metric("RSI 1M", round(rsi_1m,2))

st.subheader("Validación")
st.write("Espacio LONG:", espacio_long)
st.write("Espacio SHORT:", espacio_short)
st.write("No agotamiento:", no_agotamiento)

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

st.subheader("Probabilidad estimada")
st.progress(probabilidad / 100)
st.write(f"{probabilidad}%")
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
# =====================================
# PANEL 2 – EVALUADOR DE TRADE MANUAL
# =====================================

st.markdown("---")
st.title("📈 Panel 2 – Evaluador de Trade")

entrada = st.number_input("Precio de entrada", value=float(price_1m))
direccion = st.selectbox("Dirección", ["SHORT", "LONG"])

evaluar = st.button("Evaluar")

if evaluar:

    comision = 0.2 / 100
    tp_percent = 0.5 / 100

    if direccion == "SHORT":
        tp = entrada * (1 - tp_percent)
        sl = entrada * (1 + 0.35 / 100)  # SL estructural simple 0.35%
    else:
        tp = entrada * (1 + tp_percent)
        sl = entrada * (1 - 0.35 / 100)

    # Comisión ida y vuelta
    impacto_comision = entrada * comision * 2

    beneficio_bruto = abs(tp - entrada)
    beneficio_neto = beneficio_bruto - impacto_comision

    # ========================
    # PROBABILIDAD ESTIMADA
    # ========================

    score = 0
    factores_favor = []
    factores_contra = []

    # ADX
    if adx_5m > 25:
        score += 30
        factores_favor.append("ADX fuerte (>25)")
    elif adx_5m > 22:
        score += 20
        factores_favor.append("ADX impulso moderado")
    else:
        factores_contra.append("ADX débil")

    # Fase
    if fase in ["ALCISTA", "BAJISTA"]:
        score += 20
        factores_favor.append("Fase estructural definida")
    else:
        factores_contra.append("Fase transición")

    # RSI 1M
    if direccion == "SHORT" and rsi_1m < 48:
        score += 15
        factores_favor.append("RSI 1M confirmando bajista")
    elif direccion == "LONG" and rsi_1m > 52:
        score += 15
        factores_favor.append("RSI 1M confirmando alcista")
    else:
        factores_contra.append("RSI 1M no confirma timing")

    # Vela extendida
    if vela_extendida:
        factores_contra.append("Vela 1M extendida >1.5x")
    else:
        score += 10
        factores_favor.append("No hay extensión 1M")

    probabilidad = min(score, 95)

    # ========================
    # TRAILING
    # ========================

    if adx_5m > 30:
        trailing = 0.18
    elif adx_5m > 25:
        trailing = 0.20
    else:
        trailing = None

    # ========================
    # OUTPUT UI
    # ========================

    st.subheader("📊 Resultados")

    col1, col2, col3 = st.columns(3)

    col1.metric("TP 0.5%", round(tp, 2))
    col2.metric("SL técnico", round(sl, 2))
    col3.metric("Probabilidad TP", f"{probabilidad}%")

    st.write("Beneficio bruto:", round(beneficio_bruto, 2))
    st.write("Impacto comisión (0.2% ida/vuelta):", round(impacto_comision, 2))
    st.write("Beneficio neto estimado:", round(beneficio_neto, 2))

    st.subheader("🎯 Factores a favor")
    for f in factores_favor:
        st.success(f)

    st.subheader("⚠ Factores en contra")
    for f in factores_contra:
        st.error(f)

    st.subheader("🔄 Trailing dinámico")
    if trailing:
        st.info(f"Trailing activo: {trailing}% (ADX actual: {round(adx_5m,2)})")
    else:
        st.warning("Trailing no activo (ADX ≤ 25)")
st.divider()
st.header("📌 PANEL 2 — Evaluador de Trade Manual")

with st.form("trade_form"):
    entry_price = st.number_input("Precio de entrada", value=float(price_1m))
    direction = st.selectbox("Dirección", ["SHORT", "LONG"])
    evaluar = st.form_submit_button("Evaluar")

if evaluar:

    commission = 0.2 / 100

    # ======================
    # TP NETO 0.5% OBJETIVO
    # ======================
    tp_target = 0.5 / 100
    
    if direction == "SHORT":
        tp_price = entry_price * (1 - tp_target)
        sl_structural = df_5m["high"].iloc[-10:].max()
    else:
        tp_price = entry_price * (1 + tp_target)
        sl_structural = df_5m["low"].iloc[-10:].min()

    # ======================
    # TRAILING DINÁMICO
    # ======================
    if adx_5m > 30:
        trailing = 0.18
    elif adx_5m > 25:
        trailing = 0.20
    else:
        trailing = None

    be_trigger = entry_price * (1 + 0.003) if direction == "LONG" else entry_price * (1 - 0.003)

    # ======================
    # PROBABILIDAD
    # ======================
    score = 50

    factores_contra = []

    if adx_5m > 22:
        score += 20
    else:
        score -= 10
        factores_contra.append("ADX < 22")

    if adx_5m > 25:
        score += 10

    if (direction == "SHORT" and di_minus > di_plus) or (direction == "LONG" and di_plus > di_minus):
        score += 15
    else:
        score -= 15
        factores_contra.append("DI no alineado")

    if fase != "RANGO":
        score += 15
    else:
        score -= 15
        factores_contra.append("Fase en rango")

    if direction == "SHORT" and rsi_1m < 48:
        score += 10
    elif direction == "LONG" and rsi_1m > 52:
        score += 10
    else:
        score -= 15
        factores_contra.append(f"RSI 1M no confirma (valor actual: {round(rsi_1m,2)})")

    if vela_extendida:
        score -= 10
        factores_contra.append("Vela 1M extendida")

    if adx_cayendo:
        score -= 15
        factores_contra.append("ADX cayendo")

    probabilidad = max(20, min(score, 90))

    # ======================
    # OUTPUT
    # ======================
    st.subheader("📊 Resultado del análisis")

    colA, colB, colC = st.columns(3)
    colA.metric("TP 0.5%", round(tp_price,2))
    colB.metric("SL estructural", round(sl_structural,2))
    colC.metric("Break Even trigger", round(be_trigger,2))

    st.write("Trailing activo:", trailing if trailing else "No activo (ADX <=25)")

    st.subheader("🎯 Probabilidad estimada TP")
    st.progress(probabilidad / 100)
    st.write(f"{probabilidad}%")

    if factores_contra:
        st.subheader("⚠ Factores en contra activos")
        for f in factores_contra:
            st.write("•", f)
    else:
        st.success("No hay factores en contra relevantes")
