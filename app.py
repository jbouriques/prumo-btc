import streamlit as st, requests, pandas as pd, numpy as np, plotly.graph_objects as go, time

st.set_page_config(page_title="Prumo BTC V1.4", layout="wide")
st.title("🔵 Prumo BTC V1.4 - Com Alvos")

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
                df = pd.DataFrame(j, columns=["a","b","c","d","close","e","f","g","h","i","j","k"])
                df["close"] = pd.to_numeric(df["close"], errors='coerce')
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

future_x = np.arange(len(y), len(y)+12)
proj = slope * future_x + intercept
prob_alta = max(5, min(95, 50 + slope*8000))
preco_atual = float(close.iloc[-1])

# CALCULO DE ALVOS
if prob_alta >= 50: # ALTA
    sl = preco_atual * 0.992  # -0.8%
    tp1 = preco_atual * 1.005 # +0.5%
    tp2 = preco_atual * 1.01  # +1.0%
    tp3 = preco_atual * 1.018 # +1.8%
    direcao = "LONG (Compra)"
else: # BAIXA
    sl = preco_atual * 1.008  # +0.8% (se cair e voltar sobe, para)
    tp1 = preco_atual * 0.995 # -0.5%
    tp2 = preco_atual * 0.99  # -1.0%
    tp3 = preco_atual * 0.982 # -1.8%
    direcao = "SHORT (Venda)"

c1,c2,c3 = st.columns(3)
c1.metric("BTC Agora", f"${preco_atual:,.2f}")
c2.metric("Prob Alta", f"{prob_alta:.0f}%")
c3.metric("Direção", direcao)

fig = go.Figure()
fig.add_trace(go.Scatter(y=y, name="Real", line=dict(color="#0a66ff", width=3)))
fig.add_trace(go.Scatter(x=list(future_x), y=proj, name="Prumo 1h", line=dict(color="#ff9f0a", dash="dash", width=3)))
# Linhas de alvos
fig.add_hline(y=sl, line_dash="dot", line_color="red", annotation_text=f"SL {sl:,.0f}")
fig.add_hline(y=tp1, line_dash="dot", line_color="green", annotation_text=f"TP1 {tp1:,.0f}")
fig.add_hline(y=tp2, line_dash="dot", line_color="green", annotation_text=f"TP2 {tp2:,.0f}")
st.plotly_chart(fig, use_container_width=True)

st.subheader(f"🎯 Plano de Trade - {direcao}")
col_sl, col_tp = st.columns(2)
with col_sl:
    st.error(f"🛑 **STOP LOSS: ${sl:,.2f}**\n\nSe bater aqui, sai com -0.8% de preju pequeno")
with col_tp:
    st.success(f"✅ **TAKE PROFIT:**\n\nTP1: ${tp1:,.2f} (+0.5%) - vende 50%\n\nTP2: ${tp2:,.2f} (+1.0%) - vende 30%\n\nTP3: ${tp3:,.2f} (+1.8%) - vende 20%")

if ENABLE:
    if prob_alta >= 70:
        msg = f"🚀 *ALTA {prob_alta:.0f}%* - {direcao}\n\n💰 Entrada: ${preco_atual:,.2f}\n🛑 STOP LOSS: ${sl:,.2f} (-0.8%)\n✅ TP1: ${tp1:,.2f} (+0.5%)\n✅ TP2: ${tp2:,.2f} (+1.0%)\n✅ TP3: ${tp3:,.2f} (+1.8%)\n\n⚠️ Use 2% da banca | Alavancagem max 5x"
        send_telegram(msg)
        st.success(f"ALTA {prob_alta:.0f}% enviada com alvos!")
    elif prob_alta <= 30:
        msg = f"🔻 *BAIXA {100-prob_alta:.0f}%* - {direcao}\n\n💰 Entrada: ${preco_atual:,.2f}\n🛑 STOP LOSS: ${sl:,.2f} (+0.8%)\n✅ TP1: ${tp1:,.2f} (-0.5%)\n✅ TP2: ${tp2:,.2f} (-1.0%)\n✅ TP3: ${tp3:,.2f} (-1.8%)\n\n⚠️ Use 2% da banca | Alavancagem max 5x"
        send_telegram(msg)
        st.error(f"BAIXA {100-prob_alta:.0f}% enviada com alvos!")

if IS_CLOUD:
    st.caption("☁️ V1.4 com SL/TP - atualiza a cada 60s")
    time.sleep(60)
    st.rerun()
