# app.py
# ARAM PS Dashboard - 최종 완성본 (모든 문제 해결)
import os, ast, requests, re, unicodedata
from typing import Dict, List, Optional
from difflib import get_close_matches
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(
    page_title="ARAM Analytics", 
    layout="wide", 
    page_icon="🏆",
    initial_sidebar_state="expanded"
)

# ------------------------------------------------------------------
# 확장된 아이템 & 스펠 매핑 (하드코딩)
# ------------------------------------------------------------------
EXTENDED_ITEM_MAPPING = {
    # 신발류
    "Boots of Speed": "1001",
    "Berserker's Greaves": "3006", 
    "Sorcerer's Shoes": "3020",
    "Plated Steelcaps": "3047",
    "Mercury's Treads": "3111",
    "Ionian Boots of Lucidity": "3158",
    "Boots of Swiftness": "3009",
    "Mobility Boots": "3117",
    
    # AD 아이템
    "Infinity Edge": "3031",
    "Bloodthirster": "3072",
    "The Collector": "6676",
    "Lord Dominik's Regards": "3036",
    "Mortal Reminder": "3033",
    "Kraken Slayer": "6672",
    "Galeforce": "6671",
    "Immortal Shieldbow": "6673",
    "Eclipse": "6692",
    "Prowler's Claw": "6693",
    "Essence Reaver": "3508",
    "Navori Quickblades": "6675",
    "Phantom Dancer": "3046",
    "Rapid Firecannon": "3094",
    "Runaan's Hurricane": "3085",
    "Statikk Shiv": "3087",
    "Stormrazor": "3095",
    
    # AP 아이템  
    "Rabadon's Deathcap": "3089",
    "Void Staff": "3135",
    "Zhonya's Hourglass": "3157",
    "Banshee's Veil": "3102",
    "Luden's Tempest": "6655",
    "Everfrost": "6656",
    "Riftmaker": "4633",
    "Crown of the Shattered Queen": "4636",
    "Hextech Rocketbelt": "3152",
    "Night Harvester": "4636",
    "Nashor's Tooth": "3115",
    "Lich Bane": "3100",
    "Cosmic Drive": "4629",
    "Demonic Embrace": "4628",
    "Shadowflame": "4645",
    "Horizon Focus": "4628",
    
    # 탱크 아이템
    "Sunfire Aegis": "6664",
    "Frostfire Gauntlet": "6662",
    "Turbo Chemtank": "6667",
    "Dead Man's Plate": "3742",
    "Randuin's Omen": "3143",
    "Thornmail": "3075",
    "Spirit Visage": "3065",
    "Force of Nature": "4401",
    "Abyssal Mask": "3001",
    "Frozen Heart": "3110",
    "Righteous Glory": "3800",
    "Warmog's Armor": "3083",
    
    # 서포터 아이템
    "Locket of the Iron Solari": "3190",
    "Shurelya's Battlesong": "2065",
    "Imperial Mandate": "4005",
    "Moonstone Renewer": "6617",
    "Staff of Flowing Water": "6616",
    "Chemtech Putrifier": "6609",
    "Ardent Censer": "3504",
    "Redemption": "3107",
    "Mikael's Blessing": "3222",
    
    # 정글 아이템
    "Goredrinker": "6630",
    "Stridebreaker": "6631",
    "Divine Sunderer": "6632",
    "Trinity Force": "3078",
    "Black Cleaver": "3071",
    "Sterak's Gage": "3053",
    "Death's Dance": "6333",
    "Maw of Malmortius": "3156",
    
    # 기타 인기 아이템
    "Guardian Angel": "3026",
    "Youmuu's Ghostblade": "3142",
    "Edge of Night": "3814",
    "Serpent's Fang": "6695",
    "Chempunk Chainsword": "6609",
    "Silvermere Dawn": "6035",
    "Mercurial Scimitar": "3139",
    "Wit's End": "3091",
    "Blade of the Ruined King": "3153",
    "Guinsoo's Rageblade": "3124",
    
    # 소모품/기타
    "Health Potion": "2003",
    "Control Ward": "2055",
    "Doran's Blade": "1055",
    "Doran's Ring": "1056",
    "Doran's Shield": "1054",
    "Long Sword": "1036",
    "Amplifying Tome": "1052",
    "Ruby Crystal": "1028",
    "Cloth Armor": "1029",
    "Null-Magic Mantle": "1033"
}

EXTENDED_SPELL_MAPPING = {
    "Flash": "SummonerFlash",
    "Ignite": "SummonerDot", 
    "Heal": "SummonerHeal",
    "Barrier": "SummonerBarrier",
    "Exhaust": "SummonerExhaust",
    "Teleport": "SummonerTeleport",
    "Ghost": "SummonerHaste",
    "Cleanse": "SummonerBoost",
    "Smite": "SummonerSmite",
    "Mark": "SummonerSnowball",
    "Snowball": "SummonerSnowball", 
    "Clarity": "SummonerMana",
    "Poro-Toss": "SummonerSnowball",
    
    # 영어 소문자 매핑
    "flash": "SummonerFlash",
    "ignite": "SummonerDot",
    "heal": "SummonerHeal",
    "barrier": "SummonerBarrier",
    "exhaust": "SummonerExhaust",
    "teleport": "SummonerTeleport",
    "ghost": "SummonerHaste",
    "cleanse": "SummonerBoost",
    "smite": "SummonerSmite",
    "mark": "SummonerSnowball",
    "snowball": "SummonerSnowball",
    "clarity": "SummonerMana"
}

# ------------------------------------------------------------------
# Data Dragon 시스템
# ------------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=86400)
def ddragon_version() -> str:
    """최신 Data Dragon 버전 자동 감지"""
    try:
        response = requests.get("https://ddragon.leagueoflegends.com/api/versions.json", timeout=10)
        return response.json()[0]
    except Exception as e:
        st.warning(f"버전 감지 실패 (기본값 사용): {e}")
        return "15.1.1"

@st.cache_data(show_spinner=False, ttl=86400)
def load_dd_maps(ver: str) -> Dict:
    """Data Dragon 완전 매핑 시스템"""
    try:
        # Champion 데이터
        champs_url = f"https://ddragon.leagueoflegends.com/cdn/{ver}/data/en_US/champion.json"
        champs_response = requests.get(champs_url, timeout=15)
        champs = champs_response.json()["data"]
        
        # Item 데이터
        items_url = f"https://ddragon.leagueoflegends.com/cdn/{ver}/data/en_US/item.json"
        items_response = requests.get(items_url, timeout=15)
        items = items_response.json()["data"]
        
        # Spell 데이터
        spells_url = f"https://ddragon.leagueoflegends.com/cdn/{ver}/data/en_US/summoner.json"
        spells_response = requests.get(spells_url, timeout=15)
        spells = spells_response.json()["data"]
        
        def normalize_text(text: str) -> str:
            if not isinstance(text, str):
                text = str(text)
            text = unicodedata.normalize('NFKD', text)
            text = re.sub(r"[^\w\s]", "", text).replace(" ", "").lower()
            return text
        
        # 챔피언 매핑
        champ_exact = {}
        champ_normalized = {}
        
        for champ_key, champ_data in champs.items():
            name = champ_data["name"]
            filename = f"{champ_data['id']}.png"
            
            champ_exact[name] = filename
            champ_normalized[normalize_text(name)] = filename
            champ_normalized[champ_key.lower()] = filename
        
        # 아이템 매핑
        item_exact = {}
        item_normalized = {}
        
        for item_id, item_data in items.items():
            if "name" in item_data:
                name = item_data["name"]
                item_exact[name] = item_id
                item_normalized[normalize_text(name)] = item_id
        
        # 스펠 매핑  
        spell_exact = {}
        spell_normalized = {}
        
        for spell_data in spells.values():
            name = spell_data["name"]
            spell_id = spell_data["id"]
            
            spell_exact[name] = spell_id
            spell_normalized[normalize_text(name)] = spell_id
        
        return {
            "version": ver,
            "champ_exact": champ_exact,
            "champ_normalized": champ_normalized,
            "item_exact": item_exact,
            "item_normalized": item_normalized,
            "spell_exact": spell_exact,
            "spell_normalized": spell_normalized,
            "items_count": len(items),
            "spells_count": len(spells),
            "champs_count": len(champs)
        }
        
    except Exception as e:
        st.error(f"Data Dragon 로드 실패: {e}")
        return {
            "version": ver,
            "champ_exact": {}, "champ_normalized": {},
            "item_exact": {}, "item_normalized": {},
            "spell_exact": {}, "spell_normalized": {},
            "items_count": 0, "spells_count": 0, "champs_count": 0
        }

# 전역 변수 초기화
DDRAGON_VERSION = ddragon_version()
DD_MAPS = load_dd_maps(DDRAGON_VERSION)

# ------------------------------------------------------------------
# 향상된 아이콘 URL 생성 함수들
# ------------------------------------------------------------------
def champion_icon_url(name: str) -> str:
    """챔피언 아이콘 URL 생성"""
    if not name or pd.isna(name):
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/champion/Aatrox.png"
    
    name_str = str(name).strip()
    
    # 정확한 매칭
    if name_str in DD_MAPS["champ_exact"]:
        filename = DD_MAPS["champ_exact"][name_str]
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/champion/{filename}"
    
    # 정규화된 매칭
    normalized = re.sub(r"[^\w\s]", "", name_str).replace(" ", "").lower()
    if normalized in DD_MAPS["champ_normalized"]:
        filename = DD_MAPS["champ_normalized"][normalized]
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/champion/{filename}"
    
    # Fallback
    fallback_name = re.sub(r"[^\w]", "", name_str)
    if fallback_name:
        fallback_name = fallback_name[0].upper() + fallback_name[1:]
    else:
        fallback_name = "Aatrox"
    
    return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/champion/{fallback_name}.png"

def get_item_icon_url(item: str) -> str:
    """통합된 아이템 아이콘 URL 생성 (모든 방법 사용)"""
    if not item or pd.isna(item) or str(item).strip() in ["", "0", "nan", "None"]:
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/item/1001.png"
    
    item_str = str(item).strip()
    
    # 1. 확장된 하드코딩 매핑 우선
    if item_str in EXTENDED_ITEM_MAPPING:
        item_id = EXTENDED_ITEM_MAPPING[item_str]
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/item/{item_id}.png"
    
    # 2. Data Dragon 정확한 매핑
    if item_str in DD_MAPS.get("item_exact", {}):
        item_id = DD_MAPS["item_exact"][item_str]
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/item/{item_id}.png"
    
    # 3. 정규화된 Data Dragon 매핑
    normalized = re.sub(r"[^\w\s]", "", item_str).replace(" ", "").lower()
    if normalized in DD_MAPS.get("item_normalized", {}):
        item_id = DD_MAPS["item_normalized"][normalized]
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/item/{item_id}.png"
    
    # 4. Fuzzy matching 시도
    try:
        close_matches = get_close_matches(item_str, EXTENDED_ITEM_MAPPING.keys(), n=1, cutoff=0.7)
        if close_matches:
            matched_item = close_matches[0]
            item_id = EXTENDED_ITEM_MAPPING[matched_item]
            return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/item/{item_id}.png"
    except:
        pass
    
    # 5. 기본값
    return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/item/1001.png"

def get_spell_icon_url(spell: str) -> str:
    """통합된 스펠 아이콘 URL 생성"""
    if not spell or pd.isna(spell):
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/spell/SummonerFlash.png"
    
    spell_str = str(spell).strip()
    
    # 1. 확장된 하드코딩 매핑 우선
    if spell_str in EXTENDED_SPELL_MAPPING:
        spell_id = EXTENDED_SPELL_MAPPING[spell_str]
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/spell/{spell_id}.png"
    
    # 2. Data Dragon 정확한 매핑
    if spell_str in DD_MAPS.get("spell_exact", {}):
        spell_id = DD_MAPS["spell_exact"][spell_str]
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/spell/{spell_id}.png"
    
    # 3. 정규화된 매핑
    normalized = spell_str.lower()
    if normalized in DD_MAPS.get("spell_normalized", {}):
        spell_id = DD_MAPS["spell_normalized"][normalized]
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/spell/{spell_id}.png"
    
    # 4. Fuzzy matching
    try:
        close_matches = get_close_matches(spell_str, EXTENDED_SPELL_MAPPING.keys(), n=1, cutoff=0.7)
        if close_matches:
            matched_spell = close_matches[0]
            spell_id = EXTENDED_SPELL_MAPPING[matched_spell]
            return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/spell/{spell_id}.png"
    except:
        pass
    
    return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/spell/SummonerFlash.png"

# ------------------------------------------------------------------
# 개선된 CSV 로더 
# ------------------------------------------------------------------
CSV_CANDIDATES = [
    "aram_participants_with_full_runes_merged_plus.csv",
    "aram_participants_with_full_runes_merged.csv", 
    "aram_participants_with_full_runes.csv",
    "aram_participants_clean_preprocessed.csv",
    "aram_participants_clean_no_dupe_items.csv",
    "aram_participants_with_items.csv",
]

def discover_csv():
    for filename in CSV_CANDIDATES:
        if os.path.exists(filename):
            return filename
    return None

def safe_convert(x):
    return 1 if str(x).strip().lower() in ("1", "true", "t", "yes") else 0

def parse_list_column(s):
    if isinstance(s, list):
        return s
    if not isinstance(s, str) or not s.strip():
        return []
    try:
        v = ast.literal_eval(s)
        if isinstance(v, list):
            return v
    except:
        pass
    
    delimiter = "|" if "|" in s else "," if "," in s else None
    return [t.strip() for t in s.split(delimiter)] if delimiter else [s]

@st.cache_data(show_spinner=False)
def load_dataframe(file_input) -> pd.DataFrame:
    """데이터프레임 로드 및 전처리"""
    try:
        df = pd.read_csv(file_input)
        
        # 기본 컬럼 처리
        df["win_clean"] = df.get("win", 0).apply(safe_convert)
        
        # 스펠 컬럼 처리
        s1_col = "spell1_name" if "spell1_name" in df.columns else "spell1"
        s2_col = "spell2_name" if "spell2_name" in df.columns else "spell2"
        
        df["spell_combo"] = (
            df[s1_col].astype(str).fillna("") + " + " + 
            df[s2_col].astype(str).fillna("")
        ).str.strip()
        
        # 아이템 컬럼 정리
        item_cols = [col for col in df.columns if col.startswith("item")]
        for col in item_cols:
            df[col] = df[col].fillna("").astype(str).str.strip()
        
        # 리스트 형태 컬럼 처리
        for col in ["team_champs", "enemy_champs"]:
            if col in df.columns:
                df[col] = df[col].apply(parse_list_column)
        
        # 게임 시간 및 DPM 계산
        df["duration_min"] = pd.to_numeric(df.get("game_end_min"), errors="coerce").fillna(18).clip(6, 40)
        df["dpm"] = df.get("damage_total", np.nan) / df["duration_min"].replace(0, np.nan)
        
        # KDA 계산
        for stat in ["kills", "deaths", "assists"]:
            df[stat] = pd.to_numeric(df.get(stat, 0), errors="coerce").fillna(0)
        
        df["kda"] = (df["kills"] + df["assists"]) / df["deaths"].replace(0, np.nan)
        df["kda"] = df["kda"].fillna(df["kills"] + df["assists"])
        
        return df
        
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return pd.DataFrame()

# ------------------------------------------------------------------
# 데이터 분석 함수들
# ------------------------------------------------------------------
def analyze_actual_data(df: pd.DataFrame):
    """실제 CSV 데이터에서 아이템/스펠 분석"""
    st.subheader("🔍 실제 데이터 분석")
    
    # 아이템 분석
    item_cols = [col for col in df.columns if col.startswith("item")]
    all_items = set()
    
    for col in item_cols:
        unique_items = df[col].dropna().unique()
        for item in unique_items:
            if str(item).strip() not in ["", "0", "nan", "None"]:
                all_items.add(str(item).strip())
    
    with st.expander(f"📦 아이템 목록 ({len(all_items)}개)"):
        col1, col2 = st.columns(2)
        items_list = sorted(all_items)
        
        mid_point = len(items_list) // 2
        with col1:
            for item in items_list[:mid_point]:
                st.write(f"• {item}")
        with col2:
            for item in items_list[mid_point:]:
                st.write(f"• {item}")
    
    # 스펠 분석
    spell_cols = ["spell1", "spell2", "spell1_name", "spell2_name"]
    all_spells = set()
    
    for col in spell_cols:
        if col in df.columns:
            unique_spells = df[col].dropna().unique()
            for spell in unique_spells:
                if str(spell).strip() not in ["", "0", "nan", "None"]:
                    all_spells.add(str(spell).strip())
    
    with st.expander(f"✨ 스펠 목록 ({len(all_spells)}개)"):
        for spell in sorted(all_spells):
            st.write(f"• {spell}")
    
    return sorted(all_items), sorted(all_spells)

def analyze_champion_data(df: pd.DataFrame, champion: str):
    """챔피언별 데이터 분석 및 CSV 저장"""
    champion_df = df[df["champion"] == champion].copy()
    
    # 아이템 데이터 추출
    item_cols = [col for col in champion_df.columns if col.startswith("item")]
    items_data = []
    
    for idx, row in champion_df.iterrows():
        for col in item_cols:
            item_value = row[col]
            if pd.notna(item_value) and str(item_value).strip() not in ["", "0", "nan", "None"]:
                items_data.append({
                    "matchId": row.get("matchId", idx),
                    "win_clean": row.get("win_clean", 0),
                    "item": str(item_value).strip(),
                    "champion": champion
                })
    
    # 스펠 데이터 추출
    s1_col = "spell1_name" if "spell1_name" in champion_df.columns else "spell1"
    s2_col = "spell2_name" if "spell2_name" in champion_df.columns else "spell2"
    
    spells_data = []
    for idx, row in champion_df.iterrows():
        spell1 = str(row.get(s1_col, "")).strip()
        spell2 = str(row.get(s2_col, "")).strip()
        
        if spell1 and spell1 not in ["", "nan", "None"]:
            spells_data.append({
                "matchId": row.get("matchId", idx),
                "win_clean": row.get("win_clean", 0),
                "spell": spell1,
                "spell_combo": f"{spell1} + {spell2}",
                "champion": champion
            })
    
    # CSV 저장
    results = {}
    if items_data:
        items_df = pd.DataFrame(items_data)
        items_filename = f"{champion}_items_analysis.csv"
        items_df.to_csv(items_filename, index=False, encoding='utf-8')
        results["items"] = items_filename
    
    if spells_data:
        spells_df = pd.DataFrame(spells_data)
        spells_filename = f"{champion}_spells_analysis.csv"
        spells_df.to_csv(spells_filename, index=False, encoding='utf-8')
        results["spells"] = spells_filename
    
    return results

# ------------------------------------------------------------------
# 메인 애플리케이션
# ------------------------------------------------------------------
def main():
    # 사이드바 설정
    st.sidebar.header("⚙️ 대시보드 설정")
    
    # 디버그 모드
    debug_mode = st.sidebar.checkbox("🐛 디버그 모드", value=False)
    
    # Data Dragon 정보
    if debug_mode:
        st.sidebar.subheader("🔍 시스템 정보")
        st.sidebar.write(f"**DD 버전**: {DDRAGON_VERSION}")
        st.sidebar.write(f"**챔피언**: {DD_MAPS.get('champs_count', 0)}개")
        st.sidebar.write(f"**아이템**: {DD_MAPS.get('items_count', 0)}개")
        st.sidebar.write(f"**스펠**: {DD_MAPS.get('spells_count', 0)}개")
        st.sidebar.write(f"**하드코딩 아이템**: {len(EXTENDED_ITEM_MAPPING)}개")
        st.sidebar.write(f"**하드코딩 스펠**: {len(EXTENDED_SPELL_MAPPING)}개")
    
    # 파일 로드
    auto_csv = discover_csv()
    st.sidebar.write("🔍 **자동 검색**:", auto_csv if auto_csv else "없음")
    
    uploaded_file = st.sidebar.file_uploader("📁 CSV 파일 업로드", type="csv")
    
    # 데이터 로드
    if uploaded_file:
        df = load_dataframe(uploaded_file)
    elif auto_csv:
        df = load_dataframe(auto_csv)
    else:
        st.error("❌ CSV 파일을 업로드하거나 프로젝트 폴더에 넣어주세요.")
        st.stop()
    
    if df.empty:
        st.error("❌ 데이터를 로드할 수 없습니다.")
        st.stop()
    
    # 챔피언 선택
    champions = sorted(df["champion"].dropna().unique())
    selected_champion = st.sidebar.selectbox("🎯 챔피언 선택", champions)
    
    # 데이터 분석 섹션
    st.sidebar.subheader("📊 데이터 분석")
    
    # 실제 데이터 분석 버튼
    if st.sidebar.button("🔍 실제 데이터 분석"):
        with st.sidebar:
            with st.spinner("데이터 분석 중..."):
                items, spells = analyze_actual_data(df)
                st.success(f"✅ 분석 완료!\n아이템: {len(items)}개\n스펠: {len(spells)}개")
    
    # CSV 저장 버튼
    if st.sidebar.button("💾 CSV로 분석 데이터 저장"):
        with st.sidebar:
            with st.spinner("데이터 저장 중..."):
                results = analyze_champion_data(df, selected_champion)
                if results:
                    st.success(f"✅ 저장 완료!")
                    for data_type, filename in results.items():
                        st.write(f"- {data_type}: `{filename}`")
    
    # 메인 대시보드
    champion_df = df[df["champion"] == selected_champion]
    total_games = df["matchId"].nunique() if "matchId" in df else len(df)
    champion_games = len(champion_df)
    win_rate = round(champion_df["win_clean"].mean() * 100, 2) if champion_games else 0
    pick_rate = round(champion_games / total_games * 100, 2) if total_games else 0
    
    avg_kills = round(champion_df["kills"].mean(), 2)
    avg_deaths = round(champion_df["deaths"].mean(), 2)
    avg_assists = round(champion_df["assists"].mean(), 2)
    avg_dpm = round(champion_df["dpm"].mean(), 1)
    
    # 헤더
    st.title("🏆 ARAM Analytics Dashboard")
    st.markdown("---")
    
    # 챔피언 정보
    col1, col2, col3 = st.columns([2, 3, 2])
    with col2:
        st.image(champion_icon_url(selected_champion), width=120)
        st.subheader(f"**{selected_champion}**", divider=True)
    
    # 메트릭
    metric_cols = st.columns(5)
    with metric_cols[0]:
        st.metric("🎮 게임 수", f"{champion_games:,}")
    with metric_cols[1]:
        st.metric("🏆 승률", f"{win_rate}%")
    with metric_cols[2]:
        st.metric("📊 픽률", f"{pick_rate}%")
    with metric_cols[3]:
        st.metric("⚔️ 평균 KDA", f"{avg_kills}/{avg_deaths}/{avg_assists}")
    with metric_cols[4]:
        st.metric("💥 평균 DPM", f"{avg_dpm:,}")
    
    # 탭 구성
    tab1, tab2, tab3, tab4 = st.tabs(["📈 게임 통계", "⚔️ 아이템 & 스펠", "⏱️ 타임라인", "📋 상세 데이터"])
    
    with tab1:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if "first_blood_min" in champion_df and champion_df["first_blood_min"].notna().any():
                avg_fb = round(champion_df["first_blood_min"].mean(), 2)
                st.metric("🩸 평균 퍼스트 블러드", f"{avg_fb}분")
        
        with col2:
            if "game_end_min" in champion_df:
                avg_duration = round(champion_df["game_end_min"].mean(), 2)
                st.metric("⏰ 평균 게임 시간", f"{avg_duration}분")
        
        with col3:
            avg_kda_val = round(champion_df["kda"].mean(), 2)
            st.metric("🎯 평균 KDA", f"{avg_kda_val}")
    
    with tab2:
        left_col, right_col = st.columns(2)
        
        # 아이템 분석 (완전히 재구성됨)
        with left_col:
            st.subheader("🛡️ 인기 아이템 Top 15")
            
            item_cols = [col for col in champion_df.columns if col.startswith("item")]
            if item_cols:
                # 아이템 데이터 완전히 재구성
                all_items = []
                for _, row in champion_df.iterrows():
                    match_id = row.get("matchId", row.name)
                    win = row.get("win_clean", 0)
                    
                    for col in item_cols:
                        item_name = row[col]
                        if pd.notna(item_name) and str(item_name).strip() not in ["", "0", "nan", "None"]:
                            all_items.append({
                                "matchId": match_id,
                                "win_clean": win,
                                "item": str(item_name).strip()
                            })
                
                if all_items:
                    items_df = pd.DataFrame(all_items)
                    item_stats = (items_df.groupby("item")
                                 .agg(games=("matchId", "count"), wins=("win_clean", "sum"))
                                 .assign(win_rate=lambda x: (x.wins / x.games * 100).round(2))
                                 .sort_values(["games", "win_rate"], ascending=[False, False])
                                 .head(15))
                    
                    for idx, (item_name, stats) in enumerate(item_stats.iterrows()):
                        item_container = st.container()
                        icon_col, name_col, games_col, wr_col = item_container.columns([1, 4, 2, 2])
                        
                        with icon_col:
                            st.image(get_item_icon_url(item_name), width=36)
                        with name_col:
                            st.write(f"**{item_name}**")
                        with games_col:
                            st.write(f"{int(stats.games)}게임")
                        with wr_col:
                            color = "🟢" if stats.win_rate >= 55 else "🟡" if stats.win_rate >= 45 else "🔴"
                            st.write(f"{color} {stats.win_rate}%")
                        
                        if debug_mode:
                            st.caption(f"URL: {get_item_icon_url(item_name)}")
                        
                        st.divider()
                else:
                    st.info("아이템 데이터가 없습니다.")
            else:
                st.info("아이템 컬럼을 찾을 수 없습니다.")
        
        # 스펠 분석 (완전히 재구성됨)
        with right_col:
            st.subheader("✨ 스펠 조합 Top 10")
            
            spell_stats = (champion_df.groupby("spell_combo")
                          .agg(games=("matchId", "count"), wins=("win_clean", "sum"))
                          .assign(win_rate=lambda x: (x.wins / x.games * 100).round(2))
                          .sort_values(["games", "win_rate"], ascending=[False, False])
                          .head(10))
            
            for idx, (combo, stats) in enumerate(spell_stats.iterrows()):
                spell_container = st.container()
                spell_parts = str(combo).split(" + ")
                s1 = spell_parts[0].strip() if len(spell_parts) > 0 else ""
                s2 = spell_parts[1].strip() if len(spell_parts) > 1 else ""
                
                icon_col, name_col, stats_col = spell_container.columns([2, 3, 2])
                
                with icon_col:
                    spell_icons = st.columns(2)
                    if s1:
                        with spell_icons[0]:
                            st.image(get_spell_icon_url(s1), width=32)
                    if s2:
                        with spell_icons[1]:
                            st.image(get_spell_icon_url(s2), width=32)
                
                with name_col:
                    st.write(f"**{combo}**")
                
                with stats_col:
                    color = "🟢" if stats.win_rate >= 55 else "🟡" if stats.win_rate >= 45 else "🔴"
                    st.write(f"{color} {stats.win_rate}%")
                    st.caption(f"{int(stats.games)}게임")
                
                if debug_mode:
                    st.caption(f"S1: {get_spell_icon_url(s1)}")
                    st.caption(f"S2: {get_spell_icon_url(s2)}")
                
                st.divider()
    
    with tab3:
        col1, col2 = st.columns(2)
        
        with col1:
            if "first_core_item_min" in champion_df and champion_df["first_core_item_min"].notna().any():
                avg_first_core = round(champion_df["first_core_item_min"].mean(), 2)
                st.metric("⚡ 평균 1코어 완성", f"{avg_first_core}분")
                
                # 1코어 타이밍 히스토그램
                fig = px.histogram(
                    champion_df.dropna(subset=["first_core_item_min"]),
                    x="first_core_item_min",
                    nbins=20,
                    title=f"{selected_champion} - 1코어 완성 타이밍 분포",
                    labels={"first_core_item_min": "분", "count": "게임 수"}
                )
                fig.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#ffffff"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("1코어 타이밍 데이터가 없습니다.")
        
        with col2:
            if "dpm" in champion_df:
                # DPM 분포 히스토그램
                fig_dpm = px.histogram(
                    champion_df.dropna(subset=["dpm"]),
                    x="dpm",
                    nbins=20,
                    title=f"{selected_champion} - DPM 분포",
                    labels={"dpm": "DPM", "count": "게임 수"}
                )
                fig_dpm.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#ffffff"
                )
                st.plotly_chart(fig_dpm, use_container_width=True)
    
    with tab4:
        st.subheader("📊 전체 데이터")
        
        # 컬럼 선택
        all_cols = list(champion_df.columns)
        default_cols = [col for col in ["champion", "win_clean", "kills", "deaths", "assists", "dpm"] if col in all_cols]
        
        display_cols = st.multiselect(
            "표시할 컬럼 선택:",
            options=all_cols,
            default=default_cols
        )
        
        if display_cols:
            st.dataframe(
                champion_df[display_cols],
                use_container_width=True,
                height=400
            )
        else:
            st.dataframe(champion_df, use_container_width=True, height=400)
        
        # 데이터 다운로드
        csv = champion_df.to_csv(index=False)
        st.download_button(
            label="📥 현재 챔피언 데이터 다운로드",
            data=csv,
            file_name=f"{selected_champion}_data.csv",
            mime="text/csv"
        )
    
    # 푸터
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.caption(f"🎮 **{len(champions)}** 챔피언")
    with col2:
        st.caption(f"📊 **{total_games:,}** 총 게임")
    with col3:
        st.caption(f"🔄 Data Dragon **v{DDRAGON_VERSION}**")
    with col4:
        st.caption(f"🛡️ **{len(EXTENDED_ITEM_MAPPING)}** 매핑 아이템")

if __name__ == "__main__":
    main()
