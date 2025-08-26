# app.py
# ------------------------------------------------------------------
# ARAM PS Dashboard + Data-Dragon 아이콘
# 필요 패키지: streamlit, pandas, numpy, plotly, requests, pillow
# ------------------------------------------------------------------
import os, ast, requests
from io import BytesIO
from typing import List

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
from PIL import Image

st.set_page_config(page_title="ARAM PS Dashboard", layout="wide")

# ------------------------------------------------------------------
# Data-Dragon 이미지 URL 함수
# ------------------------------------------------------------------
DDRAGON_VERSION = "14.1.1"        # 버전 필요 시 교체

# 챔피언 이름 예외 매핑
_CHAMP_FIX = {
    "Aurelion Sol": "AurelionSol", "Cho'Gath": "Chogath", "Dr. Mundo": "DrMundo",
    "Jarvan IV": "JarvanIV", "Kai'Sa": "Kaisa", "Kha'Zix": "Khazix",
    "Kog'Maw": "KogMaw", "LeBlanc": "Leblanc", "Lee Sin": "LeeSin",
    "Master Yi": "MasterYi", "Miss Fortune": "MissFortune", "Nunu & Willump": "Nunu",
    "Rek'Sai": "RekSai", "Renata Glasc": "Renata", "Tahm Kench": "TahmKench",
    "Twisted Fate": "TwistedFate", "Vel'Koz": "Velkoz", "Wukong": "MonkeyKing",
    "Xin Zhao": "XinZhao"
}

@st.cache_data(show_spinner=False)
def champion_icon_url(name: str) -> str:
    n = _CHAMP_FIX.get(name, name.replace(" ", "").replace("'", ""))
    return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/champion/{n}.png"

# (자주 쓰는) 아이템 이름 → ID 매핑
_ITEM_ID = {
    "Infinity Edge": "3031", "Rabadon's Deathcap": "3089", "Void Staff": "3135",
    "Zhonya's Hourglass": "3157", "Kraken Slayer": "6672", "Galeforce": "6671",
    "Berserker's Greaves": "3006", "Ionian Boots of Lucidity": "3158",
    "Plated Steelcaps": "3047", "Mercury's Treads": "3111", "Boots of Swiftness": "3009",
    "Health Potion": "2003", "Control Ward": "2055", "Doran's Blade": "1055",
    "Doran's Ring": "1056", "Doran's Shield": "1054",
}
def item_icon_url(item_name: str) -> str:
    id_ = _ITEM_ID.get(item_name, "1001")   # 기본: Boots of Speed
    return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/item/{id_}.png"

# 스펠 이름 → 키 매핑
_SPELL_KEY = {
    "Flash":"SummonerFlash", "Ignite":"SummonerDot", "Heal":"SummonerHeal",
    "Barrier":"SummonerBarrier", "Exhaust":"SummonerExhaust", "Teleport":"SummonerTeleport",
    "Ghost":"SummonerHaste", "Cleanse":"SummonerBoost", "Smite":"SummonerSmite",
    "Mark":"SummonerSnowball", "Snowball":"SummonerSnowball", "Clarity":"SummonerMana"
}
def spell_icon_url(spell: str) -> str:
    key = _SPELL_KEY.get(spell.strip(), "SummonerFlash")
    return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/spell/{key}.png"

# URL → PIL.Image 로드 (캐싱)
@st.cache_data(show_spinner=False)
def load_image(url: str) -> Image.Image | None:
    try:
        data = requests.get(url, timeout=5).content
        return Image.open(BytesIO(data))
    except Exception:
        return None

# ------------------------------------------------------------------
# CSV 자동 탐색 & 로더
# ------------------------------------------------------------------
CSV_CANDIDATES = [
    "aram_participants_with_full_runes_merged_plus.csv",
    "aram_participants_with_full_runes_merged.csv",
    "aram_participants_with_full_runes.csv",
    "aram_participants_clean_preprocessed.csv",
    "aram_participants_clean_no_dupe_items.csv",
    "aram_participants_with_items.csv",
]
def _discover_csv() -> str | None:
    for f in CSV_CANDIDATES:
        if os.path.exists(f):
            return f
    return None

# win 문자열 → bool
def _yes(x) -> int:
    return 1 if str(x).strip().lower() in ("1","true","t","yes") else 0

def _as_list(s):
    if isinstance(s, list): return s
    if not isinstance(s, str) or not s.strip(): return []
    try:
        v = ast.literal_eval(s)
        if isinstance(v, list): return v
    except Exception:
        pass
    splitter = "|" if "|" in s else "," if "," in s else None
    return [t.strip() for t in s.split(splitter)] if splitter else [s]

@st.cache_data(show_spinner=False)
def load_df(buf) -> pd.DataFrame:
    df = pd.read_csv(buf)

    # 기본 컬럼 처리
    df["win_clean"] = df.get("win", 0).apply(_yes)
    s1 = "spell1_name" if "spell1_name" in df else "spell1"
    s2 = "spell2_name" if "spell2_name" in df else "spell2"
    df["spell_combo"] = (df[s1].astype(str) + " + " + df[s2].astype(str)).str.strip()

    for c in [c for c in df if c.startswith("item")]:
        df[c] = df[c].fillna("").astype(str).str.strip()

    for col in ("team_champs","enemy_champs"):
        if col in df: df[col] = df[col].apply(_as_list)

    df["duration_min"] = pd.to_numeric(df.get("game_end_min"), errors="coerce").fillna(18).clip(6, 40)
    if "damage_total" in df:
        df["dpm"] = df["damage_total"] / df["duration_min"].replace(0, np.nan)
    else:
        df["dpm"] = np.nan

    for k in ("kills","deaths","assists"):
        df[k] = df.get(k, 0)
    df["kda"] = (df["kills"] + df["assists"]) / df["deaths"].replace(0, np.nan)
    df["kda"] = df["kda"].fillna(df["kills"] + df["assists"])
    return df

# ------------------------------------------------------------------
# 사이드바: 데이터 업로드 & 챔프 선택
# ------------------------------------------------------------------
st.sidebar.header("⚙️  설정")
auto_path = _discover_csv()
st.sidebar.write("🔍 자동 검색:", auto_path if auto_path else "없음")
uploaded = st.sidebar.file_uploader("CSV 업로드(선택)", type="csv")

df = load_df(uploaded) if uploaded else load_df(auto_path) if auto_path else None
if df is None:
    st.error("CSV 파일을 찾지 못했습니다.")
    st.stop()

champions = sorted(df["champion"].dropna().unique())
sel_champ = st.sidebar.selectbox("🎯 챔피언 선택", champions)

# ------------------------------------------------------------------
# 챔피언 헤더 + 메트릭
# ------------------------------------------------------------------
dfc = df[df["champion"] == sel_champ]
total_matches = df["matchId"].nunique() if "matchId" in df else len(df)
games = len(dfc)
winrate = round(dfc["win_clean"].mean()*100,2) if games else 0
pickrate = round(games/total_matches*100,2) if total_matches else 0
avg_k = round(dfc["kills"].mean(),2)
avg_d = round(dfc["deaths"].mean(),2)
avg_a = round(dfc["assists"].mean(),2)
avg_dpm = round(dfc["dpm"].mean(),1)

st.title("🏆 ARAM Analytics")

# 챔피언 아이콘 + 이름
ic = load_image(champion_icon_url(sel_champ))
c1, c2, c3 = st.columns([2,3,2])
with c2:
    if ic: st.image(ic, width=100)
    st.subheader(sel_champ, divider=False)

# 메트릭 카드
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("게임 수", games)
m2.metric("승률", f"{winrate}%")
m3.metric("픽률", f"{pickrate}%")
m4.metric("평균 K/D/A", f"{avg_k}/{avg_d}/{avg_a}")
m5.metric("평균 DPM", avg_dpm)

# ------------------------------------------------------------------
# 탭: 게임 분석 | 아이템/룬 | 타임라인 | 원본
# ------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["📊 게임 분석", "⚔️ 아이템 & 스펠", "⏱️ 타임라인", "📋 상세 데이터"])

# ---------- 📊 게임 분석 ----------
with tab1:
    t_cols = ["first_blood_min","blue_first_tower_min","red_first_tower_min","game_end_min","gold_spike_min"]
    if any(c in dfc for c in t_cols):
        t1, t2, t3 = st.columns(3)
        if "first_blood_min" in dfc and dfc["first_blood_min"].notna().any():
            t1.metric("퍼블 평균분", round(dfc["first_blood_min"].mean(),2))
        if "game_end_min" in dfc:
            t3.metric("평균 게임시간", round(dfc["game_end_min"].mean(),2))

# ---------- ⚔️ 아이템 & 스펠 ----------
with tab2:
    left, right = st.columns(2)

    # 아이템 성과
    with left:
        st.subheader("🛡️ 아이템 성과")
        item_cols = [c for c in dfc if c.startswith("item")]
        rec = pd.concat(
            [dfc[["matchId","win_clean",c]].rename(columns={c:"item"}) for c in item_cols],
            ignore_index=True
        )
        g = (rec[rec["item"]!=""]
             .groupby("item").agg(total=("matchId","count"), wins=("win_clean","sum"))
             .assign(win_rate=lambda d: (d["wins"]/d["total"]*100).round(2))
             .sort_values(["total","win_rate"], ascending=[False,False])
             .head(10)
             .reset_index())

        for _, row in g.iterrows():
            c_icon, c_name, c_pick, c_wr = st.columns([1,4,2,2])
            with c_icon: st.image(item_icon_url(row.item), width=32)
            with c_name: st.write(row.item)
            with c_pick: st.write(f"{row.total}게임")
            with c_wr:   st.write(f"{row.win_rate}%")
            st.divider()

    # 스펠 조합
    with right:
        st.subheader("✨ 스펠 조합")
        sp = (dfc.groupby("spell_combo")
              .agg(games=("matchId","count"), wins=("win_clean","sum"))
              .assign(win_rate=lambda d: (d["wins"]/d["games"]*100).round(2))
              .sort_values(["games","win_rate"], ascending=[False,False])
              .head(8)
              .reset_index())

        for _, r in sp.iterrows():
            s1, s2 = [s.strip() for s in r.spell_combo.split("+")]
            col_i, col_n, col_v = st.columns([2,3,2])
            with col_i:
                st.image(spell_icon_url(s1), width=28)
                st.image(spell_icon_url(s2), width=28)
            with col_n: st.write(r.spell_combo)
            with col_v: st.write(f"{r.win_rate}%\n{r.games}G")
            st.divider()

# ---------- ⏱️ 타임라인 ----------
with tab3:
    if "first_core_item_min" in dfc:
        st.metric("1코어 평균 분", round(dfc["first_core_item_min"].mean(),2))
    if "first_core_item_min" in dfc and dfc["first_core_item_min"].notna().any():
        fig = px.histogram(dfc, x="first_core_item_min", nbins=24, title="1코어 시점 분포")
        fig.update_layout(plot_bgcolor="#1e2328", paper_bgcolor="#1e2328", font_color="#f0e6d2")
        st.plotly_chart(fig, use_container_width=True)

# ---------- 📋 원본 ----------
with tab4:
    st.dataframe(dfc.drop(columns=["team_champs","enemy_champs"], errors="ignore"),
                 use_container_width=True)

st.caption(f"Data-Dragon v{DDRAGON_VERSION} | 총 {len(champions)}챔프 · {total_matches}경기")
