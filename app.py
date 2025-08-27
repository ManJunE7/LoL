# app.py
# ------------------------------------------------------------------
# ARAM PS Dashboard + Data-Dragon 아이콘 (개선된 버전)
# ------------------------------------------------------------------
import os, ast, requests, re, unicodedata
from typing import List
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="ARAM PS Dashboard", layout="wide")

# ------------------------------------------------------------------
# Data-Dragon 동적 매핑 (피드백 적용)
# ------------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=86400)
def ddragon_version()->str:
    """최신 Data Dragon 버전 자동 감지"""
    try:
        return requests.get("https://ddragon.leagueoflegends.com/api/versions.json", timeout=5).json()[0]
    except:
        return "14.1.1"  # fallback

@st.cache_data(show_spinner=False, ttl=86400)
def load_dd_maps(ver:str):
    """Data Dragon에서 모든 매핑 데이터 로드"""
    try:
        # Champion 매핑
        champs = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{ver}/data/en_US/champion.json", timeout=5).json()["data"]
        
        def norm(s):
            s = unicodedata.normalize("NFKD", s)
            s = s.replace(" ", "").replace("'", "").replace(".", "")
            s = s.replace("&", "").replace(":", "")
            return s
        
        champ_name2file = {cdata["name"]: cdata["id"] + ".png" for cdata in champs.values()}
        champ_alias = {norm(cdata["name"]).lower(): cdata["id"] + ".png" for cdata in champs.values()}
        
        # Items 매핑
        items = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{ver}/data/en_US/item.json", timeout=5).json()["data"]
        item_name2id = {v["name"]: k for k, v in items.items()}
        
        # Spells 매핑
        spells = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{ver}/data/en_US/summoner.json", timeout=5).json()["data"]
        spell_name2key = {v["name"]: v["id"] for v in spells.values()}
        
        return {
            "champ_name2file": champ_name2file, 
            "champ_alias": champ_alias,
            "item_name2id": item_name2id, 
            "spell_name2key": spell_name2key
        }
    except Exception as e:
        st.error(f"Data Dragon 로드 실패: {e}")
        # Fallback 하드코딩 데이터 반환
        return {
            "champ_name2file": {}, "champ_alias": {},
            "item_name2id": {"Infinity Edge": "3031", "Boots": "1001"},
            "spell_name2key": {"Flash": "SummonerFlash", "Ignite": "SummonerDot"}
        }

# 전역 변수 초기화
DDRAGON_VERSION = ddragon_version()
DD = load_dd_maps(DDRAGON_VERSION)

def champion_icon_url(name: str) -> str:
    """챔피언 아이콘 URL 생성 (동적 매핑)"""
    key = DD["champ_name2file"].get(name)
    if not key:
        n = re.sub(r"[ '&.:]", "", name).lower()
        key = DD["champ_alias"].get(n)
    if not key:
        # 최후 fallback
        key = re.sub(r"[ '&.:]", "", name)
        key = key[0].upper() + key[1:] if key else "Aatrox"
        key += ".png"
    return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/champion/{key}"

def item_icon_url(item: str) -> str:
    """아이템 아이콘 URL 생성 (동적 매핑)"""
    iid = DD["item_name2id"].get(item)
    if not iid:
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/item/1001.png"  # fallback
    return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/item/{iid}.png"

def spell_icon_url(spell: str) -> str:
    """스펠 아이콘 URL 생성 (동적 매핑)"""
    skey = DD["spell_name2key"].get(spell.strip())
    if not skey:
        skey = "SummonerFlash"  # fallback
    return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/spell/{skey}.png"

# ------------------------------------------------------------------
# CSV 로더 (기존 로직 유지)
# ------------------------------------------------------------------
CSV_CANDIDATES = [
    "aram_participants_with_full_runes_merged_plus.csv",
    "aram_participants_with_full_runes_merged.csv",
    "aram_participants_with_full_runes.csv",
    "aram_participants_clean_preprocessed.csv",
    "aram_participants_clean_no_dupe_items.csv",
    "aram_participants_with_items.csv",
]

def _discover_csv():
    for f in CSV_CANDIDATES:
        if os.path.exists(f): return f
    return None

def _yes(x): 
    return 1 if str(x).strip().lower() in ("1","true","t","yes") else 0

def _as_list(s):
    if isinstance(s,list): return s
    if not isinstance(s,str) or not s.strip(): return []
    try:
        v = ast.literal_eval(s)
        if isinstance(v,list): return v
    except: pass
    spl = "|" if "|" in s else "," if "," in s else None
    return [t.strip() for t in s.split(spl)] if spl else [s]

@st.cache_data(show_spinner=False)
def load_df(buf) -> pd.DataFrame:
    df = pd.read_csv(buf)
    df["win_clean"] = df.get("win",0).apply(_yes)
    s1 = "spell1_name" if "spell1_name" in df else "spell1"
    s2 = "spell2_name" if "spell2_name" in df else "spell2"
    df["spell_combo"] = (df[s1].astype(str) + " + " + df[s2].astype(str)).str.strip()
    
    for c in [c for c in df if c.startswith("item")]:
        df[c] = df[c].fillna("").astype(str).str.strip()
    
    for col in ("team_champs","enemy_champs"):
        if col in df: df[col] = df[col].apply(_as_list)
    
    df["duration_min"] = pd.to_numeric(df.get("game_end_min"),errors="coerce").fillna(18).clip(6,40)
    df["dpm"] = df.get("damage_total",np.nan)/df["duration_min"].replace(0,np.nan)
    
    for k in ("kills","deaths","assists"): 
        df[k] = df.get(k,0)
    
    df["kda"] = (df["kills"]+df["assists"])/df["deaths"].replace(0,np.nan)
    df["kda"] = df["kda"].fillna(df["kills"]+df["assists"])
    return df

# ------------------------------------------------------------------
# 사이드바 & 데이터 로드
# ------------------------------------------------------------------
st.sidebar.header("⚙️ 설정")
auto = _discover_csv()
st.sidebar.write("🔍 자동 검색:", auto if auto else "없음")
up = st.sidebar.file_uploader("CSV 업로드(선택)", type="csv")

df = load_df(up) if up else load_df(auto) if auto else None
if df is None:
    st.error("CSV 파일이 없습니다.")
    st.stop()

champions = sorted(df["champion"].dropna().unique())
sel = st.sidebar.selectbox("🎯 챔피언 선택", champions)

# ------------------------------------------------------------------
# 헤더 & 메트릭
# ------------------------------------------------------------------
dfc = df[df["champion"]==sel]
total = df["matchId"].nunique() if "matchId" in df else len(df)
games = len(dfc)
wr = round(dfc["win_clean"].mean()*100,2) if games else 0
pr = round(games/total*100,2) if total else 0
avg_k, avg_d, avg_a = [round(dfc[c].mean(),2) for c in ("kills","deaths","assists")]
avg_dpm = round(dfc["dpm"].mean(),1)

st.title("🏆 ARAM Analytics")

# 챔피언 아이콘 표시 (URL 직접 렌더링)
mid = st.columns([2,3,2])[1]
with mid:
    st.image(champion_icon_url(sel), width=100)  # ← PIL 제거, URL 직접 사용
    st.subheader(sel, divider=False)

m1,m2,m3,m4,m5 = st.columns(5)
m1.metric("게임 수", games)
m2.metric("승률", f"{wr}%")
m3.metric("픽률", f"{pr}%")
m4.metric("평균 K/D/A", f"{avg_k}/{avg_d}/{avg_a}")
m5.metric("평균 DPM", avg_dpm)

# ------------------------------------------------------------------
# 탭 구성
# ------------------------------------------------------------------
tab1,tab2,tab3,tab4 = st.tabs(["📊 게임 분석","⚔️ 아이템 & 스펠","⏱️ 타임라인","📋 상세 데이터"])

with tab1:
    if "first_blood_min" in dfc and dfc["first_blood_min"].notna().any():
        st.metric("퍼블 평균 분", round(dfc["first_blood_min"].mean(),2))
    if "game_end_min" in dfc:
        st.metric("평균 게임 시간", round(dfc["game_end_min"].mean(),2))

with tab2:
    left, right = st.columns(2)
    
    # 아이템 섹션 (안정화된 렌더링 적용)
    with left:
        st.subheader("🛡️ 아이템 성과")
        item_cols = [c for c in dfc if c.startswith("item")]
        rec = pd.concat([dfc[["matchId","win_clean",c]].rename(columns={c:"item"}) for c in item_cols])
        g = (rec[rec["item"]!=""]
             .groupby("item").agg(total=("matchId","count"), wins=("win_clean","sum"))
             .assign(win_rate=lambda d:(d.wins/d.total*100).round(2))
             .sort_values(["total","win_rate"],ascending=[False,False]).head(10).reset_index())
        
        # 컨테이너 기반 안정화된 렌더링
        for i, r in g.reset_index(drop=True).iterrows():
            block = st.container()  # 각 행마다 고유 컨테이너
            c_icon, c_name, c_pick, c_wr = block.columns([1,4,2,2])
            
            with c_icon: 
                st.image(item_icon_url(str(r.item)), width=32)  # URL 직접 사용
            with c_name: 
                st.write(str(r.item))
            with c_pick: 
                st.write(f"{int(r.total)} 게임")
            with c_wr: 
                st.write(f"{r.win_rate}%")
            st.divider()
    
    # 스펠 섹션 (안정화된 렌더링 적용)
    with right:
        st.subheader("✨ 스펠 조합")
        sp = (dfc.groupby("spell_combo")
              .agg(games=("matchId","count"), wins=("win_clean","sum"))
              .assign(win_rate=lambda d:(d.wins/d.games*100).round(2))
              .sort_values(["games","win_rate"],ascending=[False,False]).head(8).reset_index())
        
        for i, r in sp.reset_index(drop=True).iterrows():
            block = st.container()  # 각 행마다 고유 컨테이너
            spell_parts = str(r.spell_combo).split("+")
            s1, s2 = [s.strip() for s in spell_parts] if len(spell_parts) >= 2 else [spell_parts[0].strip(), ""]
            
            col_i, col_n, col_v = block.columns([2,3,2])
            with col_i:
                st.image(spell_icon_url(s1), width=28)  # URL 직접 사용
                if s2:
                    st.image(spell_icon_url(s2), width=28)  # URL 직접 사용
            with col_n: 
                st.write(str(r.spell_combo))
            with col_v: 
                st.write(f"{r.win_rate}%\n{int(r.games)}G")
            st.divider()

with tab3:
    if "first_core_item_min" in dfc and dfc["first_core_item_min"].notna().any():
        st.metric("1코어 평균 분", round(dfc["first_core_item_min"].mean(),2))
        fig = px.histogram(dfc, x="first_core_item_min", nbins=24, title="1코어 시점")
        fig.update_layout(plot_bgcolor="#1e2328", paper_bgcolor="#1e2328", font_color="#f0e6d2")
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.dataframe(dfc.drop(columns=["team_champs","enemy_champs"], errors="ignore"),
                 use_container_width=True)

st.caption(f"Data-Dragon v{DDRAGON_VERSION} · {len(champions)}챔프 · {total}경기")
