import streamlit as st, requests, pandas as pd, numpy as np, plotly.graph_objects as go, time

st.set_page_config(page_title="Prumo BTC V1.3", layout="wide")
st.title("🔵 Prumo BTC V1.3 - Alta e Baixa")

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

if not IS_CLOUD:
    if st.sidebar.button("🔔 TESTAR ALTA E BAIXA", type="primary", use_container_width=True):
        if send_telegram("✅ *PRUMO V1.3 CONECTADO!* \n🚀 ALTA >70%\n🔻 BAIXA >70%"):
            st.sidebar.success("Enviado!")
            st.balloons()

@st.cache_data(ttl=30)
def get_data():
    try:
        r = requests.get("https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=5m&limit=100", timeout=15)
        j = r.json()
        if not isinstance(j, list): return None
        df = pd.DataFrame(j, columns=["a","b","c","d","close","e","f","g","h","i","j","k"])
        df["close"] = pd.to_numeric(df["close"], errors='coerce')
        df = df.dropna()
        return df if len(df) > 20 else None
    except: return None

df = get_data()

if df is None:
    st.warning("⚠️ Binance ocupada, recarregando em 10s... é normal quando muita gente acessa")
    time.sleep(10)
    st.rerun()

close = df["close"]
y = close.values[-60:]
if len(y) < 5:
    st.warning("Poucos dados, recarregando...")
    time.sleep(5)
    st.rerun()

x = np.arange(len(y))
try:
    slope, intercept = np.polyfit(x, y, 1)
except:
    st.warning("Calculando tendência... recarregando")
    time.sleep(5)
    st.rerun()

future_x = np.arange(len(y), len(y)+12)
proj = slope * future_x + intercept
prob_alta = max(5, min(95, 50 + slope*8000))

c1,c2,c3 = st.columns(3)
c1.metric("BTC Agora", f"${close.iloc[-1]:,.2f}")
c2.metric("Prob Alta", f"{prob_alta:.0f}%")
c3.metric("Alvo 1h", f"${proj[-1]:,.2f}")

fig = go.Figure()
fig.add_trace(go.Scatter(y=y, name="Real", line=dict(color="#0a66ff", width=3)))
fig.add_trace(go.Scatter(x=list(future_x), y=proj, name="Prumo 1h", line=dict(color="#ff9f0a", dash="dash", width=3)))
st.plotly_chart(fig, use_container_width=True)

if ENABLE:
    if prob_alta >= 70:
        send_telegram(f"🚀 *ALTA {prob_alta:.0f}%* BTC ${close.iloc[-1]:,.0f} -> ${proj[-1]:,.0f}")
        st.success(f"ALTA {prob_alta:.0f}% enviada!")
    elif prob_alta <= 30:
        send_telegram(f"🔻 *BAIXA {100-prob_alta:.0f}%* BTC ${close.iloc[-1]:,.0f} -> ${proj[-1]:,.0f}")
        st.error(f"BAIXA {100-prob_alta:.0f}% enviada!")

if IS_CLOUD:
    st.caption("☁️ Rodando 24h - atualiza a cada 60s")
    time.sleep(60)
    st.rerun()
