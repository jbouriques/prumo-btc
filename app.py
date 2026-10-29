import streamlit as st, requests, pandas as pd, numpy as np, plotly.graph_objects as go, time

st.set_page_config(page_title="Prumo BTC V1.5 ATR", layout="wide")
st.title("🔵 Prumo BTC V1.5 - Anti-Pavio ATR")

try:
    TOKEN = st.secrets["TOKEN"]
    CHAT_ID = st.secrets["CHAT_ID"]
    IS_CLOUD = True
except:
    IS_CLOUD = False
    TOKEN = None
    CHAT_ID = None
    st.sidebar.warning("Configure Secrets na nuvem!")

ENABLE = st.sidebar.checkbox("Ativar alertas >70%", value=True)

def send_telegram(msg):
    if not TOKEN or not CHAT_ID: return False
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
        return True
    except: return False

@st.cache_data(ttl=30)
def get_data():
    urls = [
        "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=5m&limit=100",
        "https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=5m&limit=100",
        "https://api1.binance.com/api/v3/klines?symbol=BTCUSDT&interval=5m&limit=100"
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=10)
            j = r.json()
            if isinstance(j, list) and len(j) > 20:
                df = pd.DataFrame(j, columns=["open_time","open","high","low","close","vol","ct","qa","trades","tb","tq","ign"])
                df["close"] = pd.to_numeric(df["close"], errors='coerce')
                df["high"] = pd.to_numeric(df["high"], errors='coerce')
                df["low"] = pd.to_numeric(df["low"], errors='coerce')
                df = df.dropna()
                if len(df) > 20: return df
        except: continue
    return None

df = get_data()
if df is None:
    st.warning("⚠️ Binance ocupada, recarregando em 10s...")
    time.sleep(10)
    st.rerun()

close = df["close"]
y = close.values[-60:]
x = np.arange(len(y))
try:
    slope, intercept = np.polyfit(x, y, 1)
except:
    time.sleep(5)
    st.rerun()

# CALCULO ATR 14 (Anti-Pavio)
high = df["high"]
low = df["low"]
tr1 = high - low
tr2 = (high - close.shift()).abs()
tr3 = (low - close.shift()).abs()
tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
atr = tr.rolling(14).mean().iloc[-1]
if np.isnan(atr) or atr < 10: atr = float((high.iloc[-1] - low.iloc[-1]))

future_x = np.arange(len(y), len(y)+12)
proj = slope * future_x + intercept
prob_alta = max(5, min(95, 50 + slope*8000))
preco_atual = float(close.iloc[-1])

# STOP COM ATR - AQUI ESTÁ O SEGREDO ANTI-PAVIO
if prob_alta >= 50: # ALTA - LONG
    sl = preco_atual - (atr * 1.5)
    tp1 = preco_atual + (atr * 1.0)
    tp2 = preco_atual + (atr * 2.0)
    tp3 = preco_atual + (atr * 3.0)
    direcao = "LONG (Compra)"
    emoji = "🚀"
    prob_label = f"ALTA {prob_alta:.0f}%"
else: # BAIXA - SHORT
    sl = preco_atual + (atr * 1.5)
    tp1 = preco_atual - (atr * 1.0)
    tp2 = preco_atual - (atr * 2.0)
    tp3 = preco_atual - (atr * 3.0)
    direcao = "SHORT (Venda)"
    emoji = "🔻"
    prob_label = f"BAIXA {100-prob_alta:.0f}%"

# Mostra na tela
c1,c2,c3,c4 = st.columns(4)
c1.metric("BTC Agora", f"${preco_atual:,.2f}")
c2.metric("Prob", prob_label)
c3.metric("ATR 5m", f"${atr:.2f}")
c4.metric("Direção", direcao)

fig = go.Figure()
fig.add_trace(go.Scatter(y=y, name="Real", line=dict(color="#0a66ff", width=3)))
fig.add_trace(go.Scatter(x=list(future_x), y=proj, name="Prumo 1h", line=dict(color="#ff9f0a", dash="dash", width=3)))
fig.add_hline(y=sl, line_dash="dot", line_color="red", annotation_text=f"SL {sl:,.0f}")
fig.add_hline(y=tp1, line_dash="dot", line_color="#00c853", annotation_text=f"TP1 {tp1:,.0f}")
fig.add_hline(y=tp2, line_dash="dot", line_color="#00c853", annotation_text=f"TP2 {tp2:,.0f}")
st.plotly_chart(fig, use_container_width=True)

st.info(f"📊 **ATR atual: ${atr:.2f}** - Isso é o quanto o BTC balança a cada 5 min. Seu Stop está {atr*1.5:.0f} longe pra não cair em pavio.")

st.subheader(f"🎯 Plano Anti-Pavio - {direcao}")
col_sl, col_tp = st.columns(2)
with col_sl:
    st.error(f"🛑 **STOP LOSS: ${sl:,.2f}**\n\nDistância: ${abs(preco_atual-sl):.0f} (1.5x ATR)\n\nSó saia se um candle de 5m FECHAR abaixo/acima disso. Pavio não conta!")
with col_tp:
    st.success(f"✅ **TAKES:**\n\nTP1: ${tp1:,.2f} (1x ATR) - vende 50% e move Stop pro breakeven\n\nTP2: ${tp2:,.2f} (2x ATR) - vende 30%\n\nTP3: ${tp3:,.2f} (3x ATR) - vende 20%")

if ENABLE:
    if prob_alta >= 70 or prob_alta <= 30:
        dist_sl = abs(preco_atual - sl)
        dist_tp1 = abs(tp1 - preco_atual)
        msg = f"{emoji} *{prob_label}* - {direcao}\n\n💰 Entrada: ${preco_atual:,.2f}\n📊 ATR 5m: ${atr:.2f} (volatilidade)\n\n🛑 STOP: ${sl:,.2f} ({dist_sl:.0f} USD longe - 1.5x ATR)\n⚠️ DICA: Só saia se fechar candle 5m além do Stop. Pavio não conta!\n\n✅ TP1: ${tp1:,.2f} (+{dist_tp1:.0f}) -> Vende 50% e move Stop pro 0 a 0\n✅ TP2: ${tp2:,.2f}\n✅ TP3: ${tp3:,.2f}\n\n💡 Bateu TP1, seu trade já fica SEM RISCO!"
        send_telegram(msg)
        if prob_alta >= 70:
            st.success(f"ALTA {prob_alta:.0f}% com ATR enviada!")
        else:
            st.error(f"BAIXA {100-prob_alta:.0f}% com ATR enviada!")

if IS_CLOUD:
    st.caption("☁️ V1.5 ATR Anti-Pavio - atualiza a cada 60s | Stop por fechamento")
    time.sleep(60)
    st.rerun()
