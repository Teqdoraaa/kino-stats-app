import streamlit as st
import pandas as pd
import numpy as np
import psycopg2
import requests
from bs4 import BeautifulSoup
import datetime
from streamlit_autorefresh import st_autorefresh

# ──────────────────────────────────────────────────────────────
# Autorefresh la fiecare 60 secunde (60000 ms)
# ──────────────────────────────────────────────────────────────
# rulează un rerun automat, fără să dai tu refresh
st_autorefresh(interval=60_000, key="auto_refresh")

# ──────────────────────────────────────────────────────────────
# Configurație Streamlit
# ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🎲 Statistici Kino Grecia",
    layout="wide"
)

# ──────────────────────────────────────────────────────────────
# Parametri
# ──────────────────────────────────────────────────────────────
WINDOW  = 250      # ultimele 250 de extrageri
MAX_NUM = 80

# ──────────────────────────────────────────────────────────────
# 1) Încarcă baza deja populată (cache TTL = 60s)
# ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_db():
    DB_URL = st.secrets["DB_URL"]
    with psycopg2.connect(DB_URL) as conn:
        df = pd.read_sql(
            "SELECT drawn_at, nums FROM public.kino_draws "
            "ORDER BY drawn_at DESC",
            conn,
            parse_dates=["drawn_at"]
        )
    return df

# ──────────────────────────────────────────────────────────────
# 2) Extrage live ultima extragere (fără cache)
# ──────────────────────────────────────────────────────────────
def fetch_last_live():
    URL = "https://grkino.com/arhiva.php"
    resp = requests.get(URL, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table", id="archive")
    first_tr = table.find_all("tr")[1]
    cols     = [td.get_text(strip=True) for td in first_tr.find_all("td")]
    dt       = datetime.datetime.strptime(cols[0], "%d.%m.%Y %H:%M")
    nums     = [int(n) for n in cols[1].split() if n.isdigit()]
    return dt, nums

# ──────────────────────────────────────────────────────────────
# 3) Funcții de calcul (verde + roșu)
# ──────────────────────────────────────────────────────────────
def verde_freq(draws):
    v = np.zeros(MAX_NUM+1, dtype=int)
    for draw in draws[:WINDOW]:
        for n in draw:
            v[n] += 1
    return v[1:]

def rosie_streak(draws):
    r = np.zeros(MAX_NUM+1, dtype=int)
    recent = draws[:WINDOW]
    for num in range(1, MAX_NUM+1):
        streak = 0
        for draw in recent:
            if num in draw:
                break
            streak += 1
        r[num] = streak
    return r[1:]

# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────
def main():
    # 1. Încarcă tragerile din DB (cache 60s)
    df = load_db()

    # 2. Încearcă să adaugi live dacă e mai nouă decât ultima din df
    try:
        dt_live, nums_live = fetch_last_live()
        if dt_live > df["drawn_at"].iloc[0].to_pydatetime():
            new = pd.DataFrame([{"drawn_at": dt_live, "nums": nums_live}])
            df = pd.concat([new, df], ignore_index=True)
    except Exception:
        pass

    # 3. Pregătește listele
    all_draws    = df["nums"].tolist()
    draws_recent = all_draws[:WINDOW]

    # 4. Calcule
    total_counts  = np.zeros(MAX_NUM+1, dtype=int)
    for draw in all_draws:
        for n in draw:
            total_counts[n] += 1

    freq_verde   = verde_freq(all_draws)
    streak_rosie = rosie_streak(all_draws)

    # Top 5 după frecvența totală
    series_total = pd.Series(total_counts[1:], index=range(1, MAX_NUM+1))
    top5 = series_total.nlargest(5)

    # ──────────────────────────────────────────────────────────────
    #  Interfața Streamlit
    # ──────────────────────────────────────────────────────────────
    st.title("🎲 Statistici Kino Grecia")

    # Top 5
    st.subheader(f"Top 5 ultimele {WINDOW} extrageri (frecvență totală)")
    df_top5 = (
        top5.rename("Frecvență Totală")
            .reset_index()
            .rename(columns={"index": "Număr"})
    )
    df_top5[f"VERDE({WINDOW})"] = df_top5["Număr"].apply(lambda n: int(freq_verde[n-1]))
    df_top5[f"ROSIE({WINDOW})"] = df_top5["Număr"].apply(lambda n: int(streak_rosie[n-1]))
    st.table(df_top5)

    # Restul numerelor
    st.subheader("Restul numerelor (1-80)")
    df_rest = pd.DataFrame({
        "Număr": range(1, MAX_NUM+1),
        "Frecvență Totală": total_counts[1:],
        f"VERDE({WINDOW})": freq_verde,
        f"ROSIE({WINDOW})": streak_rosie
    })
    df_rest = df_rest[~df_rest["Număr"].isin(df_top5["Număr"])]
    st.dataframe(df_rest.set_index("Număr"), use_container_width=True)

if __name__ == "__main__":
    main()