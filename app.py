import streamlit as st, requests, pandas as pd, numpy as np, plotly.graph_objects as go, time

st.set_page_config(page_title="Prumo BTC V1.3", layout="wide")
st.title("🔵 Prumo BTC V1.3 - Alta e Baixa")

# PEGA DOS SECRETS NA NUVEM
try:
    TOKEN = st.secrets["TOKEN"]
    CHAT_ID = st.secrets["CHAT_ID"]
    IS_CLOUD = True
except:
    IS_CLOUD = False
    TOKEN = None
    CHAT_ID = None
    st.sidebar.warning("Rodando local - Configure Secrets na nuvem")

ENABLE = st.sidebar.checkbox("Ativar alertas >70%", value=True)

def send_telegram(msg):
    if not TOKEN or not CHAT_ID:
        return False
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
        return True
    except:
        return False

if not IS_CLOUD:
    if st.sidebar.button("🔔 TESTAR ALTA E BAIXA", type="primary", use_container_width=True):
        if send_telegram("✅ *PRUMO V1.3 CONECTADO!* \n🚀 ALTA >70%\n🔻 BAIXA >70%"):
            st.sidebar.success("Enviado! Olha Telegram")
            st.balloons()
        else:
            st.sidebar.error("Configure o Secrets!")

@st.cache_data(ttl=30)
def get_data():
    try:
        r = requests.get("https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=5m&limit=100", timeout=15)
        data = r.json()
        if not isinstance(data, list) or len(data) == 0:
            return None
        df = pd.DataFrame(data, columns=["a","b","c","d","close","e","f","g","h","i","j","k"])
        df["close"] = pd.to_numeric(df["close"], errors='coerce')
        df = df.dropna()
        if len(df) < 20:
            return None
        return df
    except Exception as e:
        return None

df = get_data()

if df is None or len(df) == 0:
    st.warning("⚠️ Binance ocupada, tentando de novo em 15s... (é normal)")
    time.sleep(15)
    st.rerun()

close = df["close"]
y = close.values[-60:]
if len(y) < 10:
    st.error("Poucos dados, recarregando...")
    time.sleep(5)
    st.rerun()

x = np.arange(len(y))
slope, intercept = np.polyfit(x, y, 1)
future_x = np.arange(len(y), len(y)+12)
proj = slope * future_x + intercept
prob_alta = max(5, min(95, 50 + slope*8000))

c1,c2,c3 = st.columns(3)
c1.metric("BTC Agora", f"${close.iloc[-1]:,.2f}")
c2.metric("Prob Alta", f"{prob_alta:.0f}%", f"{'BAIXA' if prob_alta<50 else 'ALTA'}")
c3.metric("Alvo 1h", f"${proj[-1]:,.2f}")

fig = go.Figure()
fig.add_trace(go.Scatter(y=y, name="Real", line=dict(color="#0a66ff", width=3)))
fig.add_trace(go.Scatter(x=list(future_x), y=proj, name="Prumo 1h", line=dict(color="#ff9f0a", dash="dash", width=3)))
st.plotly_chart(fig, use_container_width=True)

if ENABLE:
    if prob_alta >= 70:
        send_telegram(f"🚀 *SINAL DE ALTA {prob_alta:.0f}%* \nBTC: ${close.iloc[-1]:,.0f} \nAlvo 1h: ${proj[-1]:,.0f}")
        st.success(f"Sinal de ALTA {prob_alta:.0f}% enviado!")
    elif prob_alta <= 30:
        prob_baixa = 100 - prob_alta
        send_telegram(f"🔻 *SINAL DE BAIXA {prob_baixa:.0f}%* \nBTC: ${close.iloc[-1]:,.0f} \nAlvo 1h: ${proj[-1]:,.0f}")
        st.error(f"Sinal de BAIXA {prob_baixa:.0f}% enviado!")

if IS_CLOUD:
    st.caption("☁️ Rodando 24h na nuvem. Atualiza a cada 60s")
    time.sleep(60)
    st.rerun()
