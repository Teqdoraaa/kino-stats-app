import os
import psycopg2
import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(page_title="Kino Grecia Stats")

# Încarcă DSN-ul din Streamlit secrets
DB_URL = st.secrets["DB_URL"]

@st.cache_data(ttl=300)
def load_draws():
    with psycopg2.connect(DB_URL) as conn:
        df = pd.read_sql(
            "SELECT nums FROM public.kino_draws ORDER BY drawn_at DESC",
            conn
        )
    return df["nums"].tolist()

draws = load_draws()
WINDOW, MAX_NUM = 196, 80

# Calcule frecvențe și streak-uri
def verde_freq(d):
    v = np.zeros(MAX_NUM+1, int)
    for draw in d[:WINDOW]:
        for n in draw: v[n] += 1
    return v[1:]

def rosie_streak(d):
    r = np.zeros(MAX_NUM+1, int)
    for n in range(1, MAX_NUM+1):
        streak=0
        for draw in d:
            if n in draw: break
            streak+=1
        r[n]=streak
    return r[1:]

freq = verde_freq(draws)

st.title("🎲 Statistici Kino Grecia")
st.subheader(f"Frecvență ultimele {WINDOW} extrageri")
st.bar_chart(pd.Series(freq, index=range(1, MAX_NUM+1)))

# Top 5 total
total = np.zeros(MAX_NUM+1,int)
for draw in draws:
    for n in draw: total[n]+=1
top5 = pd.Series(total[1:], index=range(1,MAX_NUM+1)).nlargest(5)
st.subheader("Top 5 după frecvența TOTALĂ")
st.table(top5.rename("Frecvență"))