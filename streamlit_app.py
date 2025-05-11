import streamlit as st
import pandas as pd
import numpy as np
import psycopg2
import requests
from bs4 import BeautifulSoup
import datetime
from streamlit_autorefresh import st_autorefresh

# ──────────────────────────────────────────────────────────────
# MUST be first Streamlit call
# ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="🎲 Statistici Kino Grecia", layout="wide")

# ──────────────────────────────────────────────────────────────
# Autorefresh la fiecare 60s
# ──────────────────────────────────────────────────────────────
st_autorefresh(interval=60_000, key="auto_refresh")

# ──────────────────────────────────────────────────────────────
# Parametri
# ──────────────────────────────────────────────────────────────
TOP_WINDOW   = 250   # pentru Top-5
VERDE_WINDOW = 196   # pentru verde/rosu
MAX_NUM      = 80

# ──────────────────────────────────────────────────────────────
# 1) Încarcă datele din Supabase (cache 60s)
# ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_db():
    DB_URL = st.secrets["DB_URL"]
    with psycopg2.connect(DB_URL) as conn:
        df = pd.read_sql(
            "SELECT drawn_at, nums FROM public.kino_draws ORDER BY drawn_at DESC",
            conn,
            parse_dates=["drawn_at"]
        )
    return df

# ──────────────────────────────────────────────────────────────
# 2) Scrape live ultima extragere (opțional)
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
# 3) Funcții de calcul
# ──────────────────────────────────────────────────────────────
def verde_freq(draws, window):
    v = np.zeros(MAX_NUM+1, dtype=int)
    for draw in draws[:window]:
        for n in draw:
            v[n] += 1
    return v[1:]  # îndex 0 corespunde numărului 1

def rosie_streak(draws, window):
    r = np.zeros(MAX_NUM+1, dtype=int)
    recent = draws[:window]
    for num in range(1, MAX_NUM+1):
        streak = 0
        for draw in recent:
            if num in draw:
                break
            streak += 1
        r[num] = streak
    return r[1:]

# ──────────────────────────────────────────────────────────────
#   Main
# ──────────────────────────────────────────────────────────────
def main():
    # 1. Încarcă istoric
    df = load_db()

    # 2. Încearcă live
    try:
        dt_live, nums_live = fetch_last_live()
        if dt_live > df["drawn_at"].iloc[0].to_pydatetime():
            new = pd.DataFrame([{"drawn_at": dt_live, "nums": nums_live}])
            df = pd.concat([new, df], ignore_index=True)
    except Exception:
        pass

    # 3. Pregătește liste de liste (recent → vechi)
    all_draws = df["nums"].tolist()

    # 4. Calcule
    #   a) frecvență totală (nu mai e folosită pentru top-5)
    total_counts = np.zeros(MAX_NUM+1, dtype=int)
    for draw in all_draws:
        for n in draw:
            total_counts[n] += 1

    #   b) frecvență Top-5 pe ultimele TOP_WINDOW
    freq_top   = verde_freq(all_draws, TOP_WINDOW)
    #   c) frecvență „verde” și streak „rosie” pe ultimele VERDE_WINDOW
    freq_verde = verde_freq(all_draws, VERDE_WINDOW)
    streak_rosie = rosie_streak(all_draws, VERDE_WINDOW)

    #   d) determine Top-5 după freq_top
    series_top = pd.Series(freq_top, index=range(1, MAX_NUM+1))
    top5       = series_top.nlargest(5)

    # ──────────────────────────────────────────────────────────────
    #  Interfață Streamlit
    # ──────────────────────────────────────────────────────────────
    st.title("🎲 Statistici Kino Grecia")

    # Top 5
    st.subheader(f"Top 5 după frecvența din ultimele {TOP_WINDOW} extrageri")
    df_top5 = (
        top5.rename("Frecvență TOP")
            .reset_index()
            .rename(columns={"index":"Număr"})
    )
    df_top5[f"VERDE({VERDE_WINDOW})"] = df_top5["Număr"].apply(lambda n: int(freq_verde[n-1]))
    df_top5[f"ROSIE({VERDE_WINDOW})"] = df_top5["Număr"].apply(lambda n: int(streak_rosie[n-1]))
    st.table(df_top5)

    # Restul numerelor 1-80
    st.subheader("Restul numerelor (1-80)")
    df_rest = pd.DataFrame({
        "Număr": range(1, MAX_NUM+1),
        f"VERDE({VERDE_WINDOW})": freq_verde,
        f"ROSIE({VERDE_WINDOW})": streak_rosie
    }).set_index("Număr")
    st.dataframe(df_rest, use_container_width=True)

if __name__ == "__main__":
    main()