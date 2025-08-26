# app.py
# ----------------------------------------------
# ARAM PS Dashboard (Champion-centric) - lol.ps 스타일
# 레포 루트에 있는 CSV를 자동 탐색해서 로드합니다.
# 필요 패키지: streamlit, pandas, numpy, plotly
# ----------------------------------------------
import os, ast
from typing import List
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="ARAM PS Dashboard", layout="wide")

# CSS 스타일링 추가
st.markdown("""
<style>
/* 전체 앱 배경 및 테마 */
.stApp {
    background: linear-gradient(135deg, #0f1419 0%, #1a1f2e 100%);
    color: #ffffff;
}

/* 사이드바 스타일링 */
.css-1d391kg {
    background: #1e2328;
    border-right: 2px solid #3c3c41;
}

/* 메인 컨테이너 */
.main .block-container {
    padding-top: 2rem;
    padding-left: 2rem;
    padding-right: 2rem;
    max-width: 1200px;
}

/* 메트릭 카드 스타일링 */
[data-testid="metric-container"] {
    background: linear-gradient(135deg, #1e2328 0%, #2a2d35 100%);
    border: 1px solid #3c3c41;
    padding: 1.5rem;
    border-radius: 12px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
    text-align: center;
}

/* 제목 스타일링 */
h1 {
    color: #c9aa71;
    text-align: center;
    font-weight: 700;
    margin-bottom: 2rem;
    font-size: 3rem;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
}

h2, h3 {
    color: #f0e6d2;
    border-bottom: 2px solid #c9aa71;
    padding-bottom: 0.5rem;
    margin-top: 2rem;
}

/* 데이터프레임 스타일링 */
.stDataFrame {
    background: #1e2328;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #3c3c41;
}

/* 버튼 스타일링 */
.stButton > button {
    background: linear-gradient(135deg, #c9aa71 0%, #f0e6d2 100%);
    color: #1e2328;
    font-weight: 600;
    border: none;
    border-radius: 8px;
    padding: 0.5rem 1rem;
    transition: all 0.3s ease;
}

.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(201, 170, 113, 0.3);
}

/* 선택박스 스타일링 */
.stSelectbox > div > div {
    background: #1e2328;
    color: #f0e6d2;
    border: 1px solid #3c3c41;
    border-radius: 8px;
}

/* 탭 스타일링 */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background: #1e2328;
    border-radius: 8px;
    padding: 0.5rem;
}

.stTabs [data-baseweb="tab"] {
    background: #2a2d35;
    color: #f0e6d2;
    border-radius: 8px;
    padding: 0.75rem 1.5rem;
    border: 1px solid #3c3c41;
    transition: all 0.3s ease;
}

.stTabs [data-baseweb="tab"]:hover {
    background: #3c3c41;
    color: #c9aa71;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #c9aa71 0%, #f0e6d2 100%);
    color: #1e2328 !important;
    border-color: #c9aa71;
}

/* 사이드바 제목 */
.css-1d391kg h2 {
    color: #c9aa71;
    text-align: center;
    border-bottom: 2px solid #c9aa71;
    padding-bottom: 1rem;
    margin-bottom: 2rem;
}

/* Plotly 차트 배경 */
.js-plotly-plot {
    background: #1e2328 !important;
    border-radius: 8px;
    border: 1px solid #3c3c41;
}
</style>
""", unsafe_allow_html=True)

# 0) 후보 파일명들(우선순위 순)
CSV_CANDIDATES = [
    "aram_participants_with_full_runes_merged_plus.csv",
    "aram_participants_with_full_runes_merged.csv",
    "aram_participants_with_full_runes.csv",
    "aram_participants_clean_preprocessed.csv",
    "aram_participants_clean_no_dupe_items.csv",
    "aram_participants_with_items.csv",
]

# ---------- 유틸 ----------
def _yes(x) -> int:
    s = str(x).strip().lower()
    return 1 if s in ("1","true","t","yes") else 0

def _first_nonempty(*vals):
    for v in vals:
        if v is None:
            continue
        s = str(v).strip()
        if s and s.lower() not in ("nan", "none"):
            return s
    return ""

def _as_list(s):
    if isinstance(s, list):
        return s
    if not isinstance(s, str):
        return []
    s = s.strip()
    if not s:
        return []
    # 리스트형 문자열이면 파싱
    try:
        v = ast.literal_eval(s)
        if isinstance(v, list):
            return v
    except Exception:
        pass
    # 파이프/쉼표도 지원
    if "|" in s:
        return [t.strip() for t in s.split("|") if t.strip()]
    if "," in s:
        return [t.strip() for t in s.split(",") if t.strip()]
    return [s]

def _discover_csv() -> str | None:
    for name in CSV_CANDIDATES:
        if os.path.exists(name):
            return name
    return None

# ---------- 데이터 로드 ----------
@st.cache_data(show_spinner=False)
def load_df(path_or_buffer) -> pd.DataFrame:
    df = pd.read_csv(path_or_buffer)
    # win -> 0/1
    if "win" in df.columns:
        df["win_clean"] = df["win"].apply(_yes)
    else:
        df["win_clean"] = 0
    # 스펠 이름 컬럼 정규화(spell1_name/spell1)
    s1 = "spell1_name" if "spell1_name" in df.columns else ("spell1" if "spell1" in df.columns else None)
    s2 = "spell2_name" if "spell2_name" in df.columns else ("spell2" if "spell2" in df.columns else None)
    df["spell1_final"] = df[s1].astype(str) if s1 else ""
    df["spell2_final"] = df[s2].astype(str) if s2 else ""
    df["spell_combo"]  = (df["spell1_final"] + " + " + df["spell2_final"]).str.strip()
    # 아이템 문자열 정리
    for c in [c for c in df.columns if c.startswith("item")]:
        df[c] = df[c].fillna("").astype(str).str.strip()
    # 팀/상대 조합 문자열 → 리스트
    for col in ("team_champs", "enemy_champs"):
        if col in df.columns:
            df[col] = df[col].apply(_as_list)
    # 경기시간(분)
    if "game_end_min" in df.columns:
        df["duration_min"] = pd.to_numeric(df["game_end_min"], errors="coerce")
    else:
        df["duration_min"] = np.nan
    df["duration_min"] = df["duration_min"].fillna(18.0).clip(lower=6.0, upper=40.0)
    # DPM, KDA
    if "damage_total" in df.columns:
        df["dpm"] = df["damage_total"] / df["duration_min"].replace(0, np.nan)
    else:
        df["dpm"] = np.nan
    for c in ("kills","deaths","assists"):
        if c not in df.columns:
            df[c] = 0
    df["kda"] = (df["kills"] + df["assists"]) / df["deaths"].replace(0, np.nan)
    df["kda"] = df["kda"].fillna(df["kills"] + df["assists"])
    return df

# ---------- 파일 입력부 ----------
st.sidebar.markdown("""
<div style="text-align: center; padding: 1rem 0; border-bottom: 1px solid #3c3c41; margin-bottom: 1rem;">
    <h2 style="color: #c9aa71; margin: 0;">⚙️ 설정</h2>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("#### 📁 데이터")
auto_path = _discover_csv()
st.sidebar.write("🔍 자동 검색:", auto_path if auto_path else "없음")
uploaded = st.sidebar.file_uploader("CSV 업로드(선택)", type=["csv"])

if uploaded is not None:
    df = load_df(uploaded)
elif auto_path is not None:
    df = load_df(auto_path)
else:
    st.error("레포 루트에서 CSV를 찾을 수 없습니다. CSV를 업로드해 주세요.")
    st.stop()

# ---------- 필터 ----------
st.sidebar.markdown("---")
st.sidebar.markdown("#### 🎯 챔피언 선택")
champions = sorted(df["champion"].dropna().unique().tolist())
if not champions:
    st.error("champion 컬럼이 비어있습니다.")
    st.stop()

sel_champ = st.sidebar.selectbox("챔피언 선택", champions)

# ---------- 서브셋 & 지표 ----------
dfc = df[df["champion"] == sel_champ].copy()
total_matches = df["matchId"].nunique() if "matchId" in df.columns else len(df["matchId"])
games = len(dfc)
winrate = round(dfc["win_clean"].mean()*100, 2) if games else 0.0
pickrate = round(games/total_matches*100, 2) if total_matches else 0.0
avg_k, avg_d, avg_a = round(dfc["kills"].mean(),2), round(dfc["deaths"].mean(),2), round(dfc["assists"].mean(),2)
avg_kda = round(dfc["kda"].mean(), 2)
avg_dpm = round(dfc["dpm"].mean(), 1)

# 메인 제목
st.markdown(f"""
<div style="text-align: center; padding: 2rem 0;">
    <h1 style="font-size: 3rem; margin: 0; background: linear-gradient(135deg, #c9aa71 0%, #f0e6d2 100%); 
               -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
        🏆 ARAM Analytics
    </h1>
    <h2 style="font-size: 2rem; margin: 0.5rem 0; color: #f0e6d2;">
        {sel_champ}
    </h2>
    <div style="width: 100px; height: 3px; background: linear-gradient(135deg, #c9aa71 0%, #f0e6d2 100%); 
                margin: 1rem auto; border-radius: 2px;"></div>
</div>
""", unsafe_allow_html=True)

# 메트릭 카드들
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("게임 수", games)
c2.metric("승률(%)", winrate)
c3.metric("픽률(%)", pickrate)
c4.metric("평균 K/D/A", f"{avg_k}/{avg_d}/{avg_a}")
c5.metric("평균 DPM", avg_dpm)

# 탭으로 콘텐츠 구성
tab1, tab2, tab3, tab4 = st.tabs(["📊 게임 분석", "⚔️ 아이템 & 룬", "⏱️ 타임라인", "📋 상세 데이터"])

with tab1:
    # ---------- 타임라인(있으면 표시) ----------
    tl_cols = ["first_blood_min","blue_first_tower_min","red_first_tower_min","game_end_min","gold_spike_min"]
    if any(c in dfc.columns for c in tl_cols):
        st.subheader("⚡ 게임 플로우")
        t1, t2, t3 = st.columns(3)
        if "first_blood_min" in dfc.columns and dfc["first_blood_min"].notna().any():
            t1.metric("퍼블 평균(분)", round(dfc["first_blood_min"].mean(), 2))
        if ("blue_first_tower_min" in dfc.columns) or ("red_first_tower_min" in dfc.columns):
            bt = round(dfc["blue_first_tower_min"].dropna().mean(), 2) if "blue_first_tower_min" in dfc.columns else np.nan
            rt = round(dfc["red_first_tower_min"].dropna().mean(), 2) if "red_first_tower_min" in dfc.columns else np.nan
            t2.metric("첫 포탑 평균(블루/레드)", f"{bt} / {rt}")
        if "game_end_min" in dfc.columns and dfc["game_end_min"].notna().any():
            t3.metric("평균 게임시간(분)", round(dfc["game_end_min"].mean(), 2))

with tab2:
    # ---------- 코어 아이템 구매시각 ----------
    core_cols = [c for c in ["first_core_item_min","first_core_item_name",
                            "second_core_item_min","second_core_item_name"] if c in dfc.columns]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🛡️ 아이템 성과")
        def item_stats(sub: pd.DataFrame) -> pd.DataFrame:
            item_cols = [c for c in sub.columns if c.startswith("item")]
            rec = []
            for c in item_cols:
                rec.append(sub[["matchId","win_clean",c]].rename(columns={c:"item"}))
            u = pd.concat(rec, ignore_index=True)
            u = u[u["item"].astype(str)!=""]
            g = (u.groupby("item")
                .agg(total_picks=("matchId","count"), wins=("win_clean","sum"))
                .reset_index())
            g["win_rate"] = (g["wins"]/g["total_picks"]*100).round(2)
            g = g.sort_values(["total_picks","win_rate"], ascending=[False,False])
            return g
        
        st.dataframe(item_stats(dfc).head(15), use_container_width=True)
    
    with col2:
        st.subheader("✨ 스펠 조합")
        if "spell_combo" in dfc.columns and dfc["spell_combo"].str.strip().any():
            sp = (dfc.groupby("spell_combo")
                  .agg(games=("matchId","count"), wins=("win_clean","sum"))
                  .reset_index())
            sp["win_rate"] = (sp["wins"]/sp["games"]*100).round(2)
            sp = sp.sort_values(["games","win_rate"], ascending=[False,False])
            st.dataframe(sp.head(10), use_container_width=True)
        else:
            st.info("스펠 정보가 부족합니다.")
        
        st.subheader("🔮 룬 조합")
        if ("rune_core" in dfc.columns) and ("rune_sub" in dfc.columns):
            rn = (dfc.groupby(["rune_core","rune_sub"])
                  .agg(games=("matchId","count"), wins=("win_clean","sum"))
                  .reset_index())
            rn["win_rate"] = (rn["wins"]/rn["games"]*100).round(2)
            rn = rn.sort_values(["games","win_rate"], ascending=[False,False])
            st.dataframe(rn.head(10), use_container_width=True)
        else:
            st.info("룬 정보가 부족합니다.")

with tab3:
    if core_cols:
        st.subheader("⏰ 코어 아이템 타이밍")
        a, b = st.columns(2)
        if "first_core_item_min" in dfc.columns and dfc["first_core_item_min"].notna().any():
            a.metric("1코어 평균 분", round(dfc["first_core_item_min"].mean(), 2))
            fig1 = px.histogram(dfc.dropna(subset=["first_core_item_min"]),
                               x="first_core_item_min", nbins=24, title="1코어 시각 분포")
            fig1.update_layout(plot_bgcolor='#1e2328', paper_bgcolor='#1e2328', font_color='#f0e6d2')
            st.plotly_chart(fig1, use_container_width=True)
        
        if "second_core_item_min" in dfc.columns and dfc["second_core_item_min"].notna().any():
            b.metric("2코어 평균 분", round(dfc["second_core_item_min"].mean(), 2))
            fig2 = px.histogram(dfc.dropna(subset=["second_core_item_min"]),
                               x="second_core_item_min", nbins=24, title="2코어 시각 분포")
            fig2.update_layout(plot_bgcolor='#1e2328', paper_bgcolor='#1e2328', font_color='#f0e6d2')
            st.plotly_chart(fig2, use_container_width=True)
    
    if "gold_spike_min" in dfc.columns and dfc["gold_spike_min"].notna().any():
        fig3 = px.histogram(dfc, x="gold_spike_min", nbins=20, title="골드 스파이크 시각 분포(분)")
        fig3.update_layout(plot_bgcolor='#1e2328', paper_bgcolor='#1e2328', font_color='#f0e6d2')
        st.plotly_chart(fig3, use_container_width=True)

with tab4:
    st.subheader("📋 원본 데이터")
    show_cols = [c for c in dfc.columns if c not in ("team_champs","enemy_champs")]
    st.dataframe(dfc[show_cols], use_container_width=True)

st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 2rem; color: #a09b8c;">
    <p>CSV 자동탐색 + 업로드 지원 · 누락 컬럼은 자동으로 건너뜁니다.</p>
    <p style="font-size: 0.9rem; margin-top: 1rem;">Powered by Streamlit | Styled like LoL.ps</p>
</div>
""", unsafe_allow_html=True)
