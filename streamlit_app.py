import streamlit as st
import pandas as pd
import numpy as np
import psycopg2

# ──────────────────────────────────────────────────────────────
#  Configurație Streamlit
# ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="🎲 Statistici Kino Grecia", layout="wide")

# ──────────────────────────────────────────────────────────────
#  Încarcă și cache-uiește datele din Supabase
# ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_draws():
    DB_URL = st.secrets["DB_URL"]
    with psycopg2.connect(DB_URL) as conn:
        df = pd.read_sql(
            "SELECT nums FROM public.kino_draws ORDER BY drawn_at DESC",
            conn
        )
    # coloana nums e de tip array, .tolist() dă listă de liste Python
    return df["nums"].tolist()

draws = load_draws()

# ──────────────────────────────────────────────────────────────
#  Parametri
# ──────────────────────────────────────────────────────────────
WINDOW  = 196
MAX_NUM = 80

# ──────────────────────────────────────────────────────────────
#  Funcții de calcul
# ──────────────────────────────────────────────────────────────
def verde_freq(draws):
    v = np.zeros(MAX_NUM+1, dtype=int)
    for draw in draws[:WINDOW]:
        for n in draw:
            v[n] += 1
    return v[1:]  # returnează frecvențele pentru 1..MAX_NUM

def rosie_streak(draws):
    r = np.zeros(MAX_NUM+1, dtype=int)
    for num in range(1, MAX_NUM+1):
        streak = 0
        for draw in draws:
            if num in draw:
                break
            streak += 1
        r[num] = streak
    return r[1:]  # returnează streak-urile pentru 1..MAX_NUM

# ──────────────────────────────────────────────────────────────
#  Compută statistici
# ──────────────────────────────────────────────────────────────
freq  = verde_freq(draws)
rosie = rosie_streak(draws)

# frecvența totală pe toate extragerile
total_counts = np.zeros(MAX_NUM+1, dtype=int)
for draw in draws:
    for n in draw:
        total_counts[n] += 1

# seria cu Top 5 după frecvența totală
top5 = pd.Series(total_counts[1:], index=range(1, MAX_NUM+1))\
         .nlargest(5)

# ──────────────────────────────────────────────────────────────
#  Interfață Streamlit
# ──────────────────────────────────────────────────────────────
st.title("🎲 Statistici Kino Grecia")

st.subheader(f"Frecvență ultimele {WINDOW} extrageri")
st.bar_chart(pd.Series(freq, index=range(1, MAX_NUM+1)))

# Top 5
st.subheader("Top 5 după frecvența TOTALĂ")
df_top5 = (
    top5
    .rename("Frecvență Totală")
    .reset_index()
    .rename(columns={"index": "Număr"})
)
df_top5[f"VERDE({WINDOW})"] = df_top5["Număr"].apply(lambda n: int(freq[n-1]))
df_top5[f"ROSIE({WINDOW})"] = df_top5["Număr"].apply(lambda n: int(rosie[n-1]))
st.table(df_top5)

# Restul numerelor
df_rest = pd.DataFrame({
    "Număr": list(range(1, MAX_NUM+1)),
    "Frecvență Totală": total_counts[1:],
    f"VERDE({WINDOW})": freq,
    f"ROSIE({WINDOW})": rosie
})
df_rest = df_rest[~df_rest["Număr"].isin(df_top5["Număr"])]

st.subheader("Restul numerelor (1-80)")
st.dataframe(df_rest.set_index("Număr"), use_container_width=True)