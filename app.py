# app.py
# ARAM PS Dashboard - 최종 완성본
import os, ast, requests, re, unicodedata
from typing import Dict, List
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="ARAM Analytics", layout="wide", page_icon="🏆")

# ------------------------------------------------------------------
# 완전히 개선된 Data Dragon 시스템
# ------------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=86400)
def ddragon_version() -> str:
    """최신 Data Dragon 버전 자동 감지"""
    try:
        response = requests.get("https://ddragon.leagueoflegends.com/api/versions.json", timeout=10)
        return response.json()[0]
    except Exception as e:
        st.warning(f"버전 감지 실패: {e}")
        return "14.1.1"

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
            """텍스트 정규화"""
            if not isinstance(text, str):
                text = str(text)
            # 유니코드 정규화
            text = unicodedata.normalize('NFKD', text)
            # 특수문자 제거 및 소문자 변환
            text = re.sub(r"[^\w\s]", "", text).replace(" ", "").lower()
            return text
        
        # 챔피언 매핑 생성
        champ_exact = {}
        champ_normalized = {}
        
        for champ_key, champ_data in champs.items():
            name = champ_data["name"]
            filename = f"{champ_data['id']}.png"
            
            champ_exact[name] = filename
            champ_normalized[normalize_text(name)] = filename
            champ_normalized[champ_key.lower()] = filename
        
        # 아이템 매핑 생성
        item_exact = {}
        item_normalized = {}
        
        for item_id, item_data in items.items():
            if "name" in item_data:
                name = item_data["name"]
                item_exact[name] = item_id
                item_normalized[normalize_text(name)] = item_id
        
        # 스펠 매핑 생성
        spell_exact = {}
        spell_normalized = {}
        
        for spell_data in spells.values():
            name = spell_data["name"]
            spell_id = spell_data["id"]
            
            spell_exact[name] = spell_id
            spell_normalized[normalize_text(name)] = spell_id
            
            # 추가 영어 매핑
            english_mappings = {
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
            
            for eng, spell_key in english_mappings.items():
                spell_normalized[eng] = spell_key
        
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
            "version": "14.1.1",
            "champ_exact": {}, "champ_normalized": {},
            "item_exact": {}, "item_normalized": {},
            "spell_exact": {}, "spell_normalized": {},
            "items_count": 0, "spells_count": 0, "champs_count": 0
        }

# 전역 변수 초기화
DDRAGON_VERSION = ddragon_version()
DD_MAPS = load_dd_maps(DDRAGON_VERSION)

def champion_icon_url(name: str) -> str:
    """챔피언 아이콘 URL 생성"""
    if not name or pd.isna(name):
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/champion/Aatrox.png"
    
    name_str = str(name).strip()
    
    # 정확한 매칭 시도
    if name_str in DD_MAPS["champ_exact"]:
        filename = DD_MAPS["champ_exact"][name_str]
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/champion/{filename}"
    
    # 정규화된 매칭 시도
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

def item_icon_url(item: str) -> str:
    """아이템 아이콘 URL 생성 (개선됨)"""
    if not item or pd.isna(item) or str(item).strip() in ["", "0", "nan", "None"]:
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/item/1001.png"
    
    item_str = str(item).strip()
    
    # 정확한 매칭
    if item_str in DD_MAPS["item_exact"]:
        item_id = DD_MAPS["item_exact"][item_str]
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/item/{item_id}.png"
    
    # 정규화된 매칭
    normalized = re.sub(r"[^\w\s]", "", item_str).replace(" ", "").lower()
    if normalized in DD_MAPS["item_normalized"]:
        item_id = DD_MAPS["item_normalized"][normalized]
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/item/{item_id}.png"
    
    return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/item/1001.png"

def spell_icon_url(spell: str) -> str:
    """스펠 아이콘 URL 생성 (개선됨)"""
    if not spell or pd.isna(spell):
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/spell/SummonerFlash.png"
    
    spell_str = str(spell).strip()
    
    # 정확한 매칭
    if spell_str in DD_MAPS["spell_exact"]:
        spell_id = DD_MAPS["spell_exact"][spell_str]
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/spell/{spell_id}.png"
    
    # 정규화된 매칭
    normalized = spell_str.lower()
    if normalized in DD_MAPS["spell_normalized"]:
        spell_id = DD_MAPS["spell_normalized"][normalized]
        return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/spell/{spell_id}.png"
    
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
    """CSV 파일 자동 감지"""
    for filename in CSV_CANDIDATES:
        if os.path.exists(filename):
            return filename
    return None

def safe_convert(x):
    """안전한 타입 변환"""
    return 1 if str(x).strip().lower() in ("1", "true", "t", "yes") else 0

def parse_list_column(s):
    """리스트 형태 컬럼 파싱"""
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
# 데이터 분석 및 내보내기 함수
# ------------------------------------------------------------------
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
        st.sidebar.write(f"**챔피언**: {DD_MAPS['champs_count']}개")
        st.sidebar.write(f"**아이템**: {DD_MAPS['items_count']}개")
        st.sidebar.write(f"**스펠**: {DD_MAPS['spells_count']}개")
    
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
    
    # 데이터 분석 버튼
    st.sidebar.subheader("📊 데이터 분석")
    if st.sidebar.button("CSV로 분석 데이터 저장"):
        with st.spinner("데이터 분석 중..."):
            results = analyze_champion_data(df, selected_champion)
            if results:
                st.sidebar.success(f"✅ 분석 완료!")
                for data_type, filename in results.items():
                    st.sidebar.write(f"- {data_type}: `{filename}`")
    
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
        col1, col2 = st.columns(2)
        
        with col1:
            if "first_blood_min" in champion_df and champion_df["first_blood_min"].notna().any():
                avg_fb = round(champion_df["first_blood_min"].mean(), 2)
                st.metric("🩸 평균 퍼스트 블러드", f"{avg_fb}분")
        
        with col2:
            if "game_end_min" in champion_df:
                avg_duration = round(champion_df["game_end_min"].mean(), 2)
                st.metric("⏰ 평균 게임 시간", f"{avg_duration}분")
    
    with tab2:
        left_col, right_col = st.columns(2)
        
        # 아이템 분석 (완전히 재구성됨)
        with left_col:
            st.subheader("🛡️ 인기 아이템")
            
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
                                 .head(12))
                    
                    for idx, (item_name, stats) in enumerate(item_stats.iterrows()):
                        item_container = st.container()
                        icon_col, name_col, games_col, wr_col = item_container.columns([1, 4, 2, 2])
                        
                        with icon_col:
                            st.image(item_icon_url(item_name), width=36)
                        with name_col:
                            st.write(f"**{item_name}**")
                        with games_col:
                            st.write(f"{int(stats.games)}게임")
                        with wr_col:
                            st.write(f"{stats.win_rate}%")
                        
                        if debug_mode:
                            st.caption(f"URL: {item_icon_url(item_name)}")
                        
                        st.divider()
                else:
                    st.info("아이템 데이터가 없습니다.")
            else:
                st.info("아이템 컬럼을 찾을 수 없습니다.")
        
        # 스펠 분석 (완전히 재구성됨)
        with right_col:
            st.subheader("✨ 스펠 조합")
            
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
                    if s1:
                        st.image(spell_icon_url(s1), width=32)
                    if s2:
                        st.image(spell_icon_url(s2), width=32)
                
                with name_col:
                    st.write(f"**{combo}**")
                
                with stats_col:
                    st.write(f"{stats.win_rate}%")
                    st.caption(f"{int(stats.games)}게임")
                
                if debug_mode:
                    st.caption(f"S1: {spell_icon_url(s1)}")
                    st.caption(f"S2: {spell_icon_url(s2)}")
                
                st.divider()
    
    with tab3:
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
    
    with tab4:
        st.subheader("📊 전체 데이터")
        
        # 컬럼 선택
        display_cols = st.multiselect(
            "표시할 컬럼 선택:",
            options=list(champion_df.columns),
            default=[col for col in ["champion", "win_clean", "kills", "deaths", "assists", "dpm"] if col in champion_df.columns]
        )
        
        if display_cols:
            st.dataframe(
                champion_df[display_cols],
                use_container_width=True,
                height=400
            )
        else:
            st.dataframe(champion_df, use_container_width=True, height=400)
    
    # 푸터
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption(f"🎮 **{len(champions)}** 챔피언")
    with col2:
        st.caption(f"📊 **{total_games:,}** 총 게임")
    with col3:
        st.caption(f"🔄 Data Dragon **v{DDRAGON_VERSION}**")

if __name__ == "__main__":
    main()
