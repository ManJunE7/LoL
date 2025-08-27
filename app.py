import os, ast, requests, re, unicodedata
from typing import List, Dict
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="ARAM PS Dashboard", layout="wide")

# ------------------------------------------------------------------
# 향상된 Data-Dragon 매핑 시스템
# ------------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=86400)
def ddragon_version()->str:
    try:
        return requests.get("https://ddragon.leagueoflegends.com/api/versions.json", timeout=5).json()[0]
    except:
        return "14.1.1"

@st.cache_data(show_spinner=False, ttl=86400)
def load_dd_maps(ver:str):
    """향상된 Data Dragon 매핑 로드"""
    try:
        # Champion 매핑
        champs_response = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{ver}/data/en_US/champion.json", timeout=10)
        champs = champs_response.json()["data"]
        
        def normalize_name(s):
            """이름 정규화 함수"""
            if not isinstance(s, str):
                s = str(s)
            # 유니코드 정규화
            s = unicodedata.normalize("NFKD", s)
            # 특수문자 제거
            s = re.sub(r"[^\w\s]", "", s)
            # 공백 제거 및 소문자 변환
            return re.sub(r"\s+", "", s).lower()
        
        # 챔피언 매핑 생성
        champ_mappings = {}
        champ_alias = {}
        
        for champ_id, champ_data in champs.items():
            name = champ_data["name"]
            filename = champ_data["id"] + ".png"
            
            # 정확한 이름 매핑
            champ_mappings[name] = filename
            
            # 정규화된 이름 매핑
            normalized = normalize_name(name)
            champ_alias[normalized] = filename
            
            # 추가 별칭들
            champ_alias[champ_id.lower()] = filename
            
        # Items 매핑
        items_response = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{ver}/data/en_US/item.json", timeout=10)
        items = items_response.json()["data"]
        
        item_mappings = {}
        item_alias = {}
        
        for item_id, item_data in items.items():
            if "name" in item_data:
                name = item_data["name"]
                item_mappings[name] = item_id
                
                # 정규화된 이름 매핑
                normalized = normalize_name(name)
                item_alias[normalized] = item_id
        
        # Spells 매핑
        spells_response = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{ver}/data/en_US/summoner.json", timeout=10)
        spells = spells_response.json()["data"]
        
        spell_mappings = {}
        spell_alias = {}
        
        for spell_key, spell_data in spells.items():
            name = spell_data["name"]
            spell_id = spell_data["id"]
            
            spell_mappings[name] = spell_id
            
            # 정규화된 이름 매핑
            normalized = normalize_name(name)
            spell_alias[normalized] = spell_id
            
            # 한국어 스펠명 추가 매핑
            korean_spells = {
                "flash": "SummonerFlash", "ignite": "SummonerDot", "heal": "SummonerHeal",
                "barrier": "SummonerBarrier", "exhaust": "SummonerExhaust", 
                "teleport": "SummonerTeleport", "ghost": "SummonerHaste",
                "cleanse": "SummonerBoost", "smite": "SummonerSmite",
                "mark": "SummonerSnowball", "snowball": "SummonerSnowball",
                "clarity": "SummonerMana"
            }
            
            # 영어 소문자 매핑
            for eng_name, spell_key in korean_spells.items():
                spell_alias[eng_name] = spell_key
        
        return {
            "champ_mappings": champ_mappings, "champ_alias": champ_alias,
            "item_mappings": item_mappings, "item_alias": item_alias,
            "spell_mappings": spell_mappings, "spell_alias": spell_alias,
            "version": ver
        }
        
    except Exception as e:
        st.error(f"Data Dragon 로드 실패: {str(e)}")
        # Fallback 데이터
        return {
            "champ_mappings": {}, "champ_alias": {},
            "item_mappings": {}, "item_alias": {},
            "spell_mappings": {}, "spell_alias": {},
            "version": "14.1.1"
        }

# 전역 변수 초기화
DDRAGON_VERSION = ddragon_version()
DD = load_dd_maps(DDRAGON_VERSION)

def champion_icon_url(name: str) -> str:
    """챔피언 아이콘 URL 생성"""
    if not name or str(name).strip() == "":
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/champion/Aatrox.png"
    
    name_str = str(name).strip()
    
    # 정확한 매핑 시도
    if name_str in DD["champ_mappings"]:
        filename = DD["champ_mappings"][name_str]
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/champion/{filename}"
    
    # 정규화된 이름으로 매핑 시도
    normalized = re.sub(r"[^\w\s]", "", name_str).replace(" ", "").lower()
    if normalized in DD["champ_alias"]:
        filename = DD["champ_alias"][normalized]
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/champion/{filename}"
    
    # Fallback: 첫 글자 대문자로 변환
    fallback_name = re.sub(r"[^\w]", "", name_str)
    fallback_name = fallback_name[0].upper() + fallback_name[1:] if fallback_name else "Aatrox"
    return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/champion/{fallback_name}.png"

def item_icon_url(item: str) -> str:
    """아이템 아이콘 URL 생성 (디버깅 포함)"""
    if not item or str(item).strip() == "" or str(item).strip() == "0":
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/item/1001.png"
    
    item_str = str(item).strip()
    
    # 정확한 매핑 시도
    if item_str in DD["item_mappings"]:
        item_id = DD["item_mappings"][item_str]
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/item/{item_id}.png"
    
    # 정규화된 이름으로 매핑 시도
    normalized = re.sub(r"[^\w\s]", "", item_str).replace(" ", "").lower()
    if normalized in DD["item_alias"]:
        item_id = DD["item_alias"][normalized]
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/item/{item_id}.png"
    
    # 디버깅: 매핑 실패한 아이템 출력
    if st.session_state.get('debug_mode', False):
        st.write(f"매핑 실패한 아이템: '{item_str}'")
    
    # Fallback
    return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/item/1001.png"

def spell_icon_url(spell: str) -> str:
    """스펠 아이콘 URL 생성"""
    if not spell or str(spell).strip() == "":
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/spell/SummonerFlash.png"
    
    spell_str = str(spell).strip()
    
    # 정확한 매핑 시도
    if spell_str in DD["spell_mappings"]:
        spell_id = DD["spell_mappings"][spell_str]
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/spell/{spell_id}.png"
    
    # 정규화된 이름으로 매핑 시도
    normalized = spell_str.lower()
    if normalized in DD["spell_alias"]:
        spell_id = DD["spell_alias"][normalized]
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/spell/{spell_id}.png"
    
    # Fallback
    return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/spell/SummonerFlash.png"

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
# 메인 앱
# ------------------------------------------------------------------
st.sidebar.header("⚙️ 설정")

# 디버깅 모드 토글
debug_mode = st.sidebar.checkbox("🐛 디버깅 모드", value=False)
st.session_state['debug_mode'] = debug_mode

auto = _discover_csv()
st.sidebar.write("🔍 자동 검색:", auto if auto else "없음")
up = st.sidebar.file_uploader("CSV 업로드(선택)", type="csv")

df = load_df(up) if up else load_df(auto) if auto else None
if df is None:
    st.error("CSV 파일이 없습니다.")
    st.stop()

champions = sorted(df["champion"].dropna().unique())
sel = st.sidebar.selectbox("🎯 챔피언 선택", champions)

# 디버깅 정보 표시
if debug_mode:
    st.sidebar.subheader("🔍 디버깅 정보")
    st.sidebar.write(f"Data Dragon 버전: {DDRAGON_VERSION}")
    st.sidebar.write(f"로드된 아이템 수: {len(DD['item_mappings'])}")
    st.sidebar.write(f"로드된 스펠 수: {len(DD['spell_mappings'])}")

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

# 챔피언 아이콘 표시
mid = st.columns([2,3,2])[1]
with mid:
    st.image(champion_icon_url(sel), width=100)
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
    
    # 아이템 섹션 (개선된 데이터 처리)
    with left:
        st.subheader("🛡️ 아이템 성과")
        item_cols = [c for c in dfc.columns if c.startswith("item")]
        
        if item_cols:
            # 아이템 데이터 재구성 (Series 객체 문제 해결)
            item_data = []
            for col in item_cols:
                for idx, row in dfc.iterrows():
                    item_name = row[col]
                    if item_name and str(item_name).strip() not in ["", "0", "nan"]:
                        item_data.append({
                            'matchId': row.get('matchId', idx),
                            'win_clean': row['win_clean'],
                            'item': str(item_name).strip()
                        })
            
            if item_data:
                item_df = pd.DataFrame(item_data)
                g = (item_df.groupby("item")
                     .agg(total=("matchId","count"), wins=("win_clean","sum"))
                     .assign(win_rate=lambda d:(d.wins/d.total*100).round(2))
                     .sort_values(["total","win_rate"], ascending=[False,False])
                     .head(10)
                     .reset_index())
                
                # 안정화된 렌더링
                for i, row in g.iterrows():
                    block = st.container()
                    c_icon, c_name, c_pick, c_wr = block.columns([1,4,2,2])
                    
                    item_name = str(row['item'])
                    
                    with c_icon: 
                        st.image(item_icon_url(item_name), width=32)
                    with c_name: 
                        st.write(item_name)
                    with c_pick: 
                        st.write(f"{int(row['total'])} 게임")
                    with c_wr: 
                        st.write(f"{row['win_rate']}%")
                    
                    # 디버깅 정보
                    if debug_mode:
                        st.caption(f"매핑: {item_name} -> {item_icon_url(item_name)}")
                    
                    st.divider()
            else:
                st.write("아이템 데이터가 없습니다.")
        else:
            st.write("아이템 컬럼을 찾을 수 없습니다.")
    
    # 스펠 섹션
    with right:
        st.subheader("✨ 스펠 조합")
        sp = (dfc.groupby("spell_combo")
              .agg(games=("matchId","count"), wins=("win_clean","sum"))
              .assign(win_rate=lambda d:(d.wins/d.games*100).round(2))
              .sort_values(["games","win_rate"], ascending=[False,False])
              .head(8)
              .reset_index())
        
        for i, row in sp.iterrows():
            block = st.container()
            spell_parts = str(row['spell_combo']).split("+")
            s1 = spell_parts[0].strip() if len(spell_parts) > 0 else ""
            s2 = spell_parts[1].strip() if len(spell_parts) > 1 else ""
            
            col_i, col_n, col_v = block.columns([2,3,2])
            
            with col_i:
                if s1:
                    st.image(spell_icon_url(s1), width=28)
                if s2:
                    st.image(spell_icon_url(s2), width=28)
            with col_n: 
                st.write(str(row['spell_combo']))
            with col_v: 
                st.write(f"{row['win_rate']}%\n{int(row['games'])}G")
            
            # 디버깅 정보
            if debug_mode:
                st.caption(f"스펠: {s1} + {s2}")
            
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
