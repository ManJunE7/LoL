"""
Streamlit ARAM '롤 PS' 스타일 대시보드
File: streamlit_aram_ps_app.py

설명:
- 로컬에 저장된 전처리된 CSV 파일(aram_participants_clean_preprocessed.csv)을 읽어서
  챔피언/아이템/룬/스펠/팀 시너지 기반 승률 분석 및 시각화를 제공합니다.
- GitHub에 업로드하여 Streamlit Cloud 혹은 로컬에서 실행할 수 있습니다.

실행 방법 (로컬):
1) 가상환경 생성(선택)
   python -m venv .venv
   .\.venv\Scripts\activate   # Windows
   source .venv/bin/activate    # macOS / Linux

2) 필요한 패키지 설치
   pip install -r requirements.txt

requirements.txt 예시 내용:
streamlit
pandas
plotly

3) 실행
   streamlit run streamlit_aram_ps_app.py

파일 설명:
- 앱은 크게 4개 섹션을 제공합니다: 요약(Overview), 챔피언(Champion), 아이템(Items), 시너지(Synergy)
- CSV 컬럼명은 아래와 같은 것을 가정합니다:
  matchId, summonerName, riotIdGameName, riotIdTagline, teamId, champion, win, kills, deaths, assists,
  gold, damage_total, damage_magic, damage_physical, damage_true,
  item0,...,item6, team_champs, enemy_champs, spell1, spell2, rune_core, rune_sub, rune_shards

주의사항:
- 아이템 컬럼에 숫자 ID가 아닌 아이템 이름이 들어있는 경우 이름 기준으로 필터링합니다.
- 컬럼명이 다르면 상단 CSV_PATH를 수정하세요.

"""

import streamlit as st
import pandas as pd
import plotly.express as px
from typing import List

st.set_page_config(page_title="ARAM PS Dashboard", layout="wide")

# --- 설정: 로컬 CSV 경로 ---
CSV_PATH = "./aram_participants_clean_preprocessed.csv"

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # win 컬럼 정리: True/False, 'True'/'False', 1/0 등 가능한 케이스 처리
    if 'win' in df.columns:
        df['win_clean'] = df['win'].apply(lambda x: 1 if str(x).lower() in ('1','true','t','yes') else 0)
    else:
        df['win_clean'] = 0

    # item 컬럼명 리스트
    item_cols = [c for c in df.columns if c.startswith('item')]
    # item 컬럼 - NA 처리 및 스트립
    for c in item_cols:
        df[c] = df[c].fillna('')
        df[c] = df[c].astype(str).str.strip()
    return df

@st.cache_data
def compute_champion_stats(df: pd.DataFrame) -> pd.DataFrame:
    out = (df.groupby('champion')
           .agg(total_games=('matchId','count'), wins=('win_clean','sum'))
           .reset_index())
    out['win_rate'] = (out['wins'] / out['total_games'] * 100).round(2)
    out = out.sort_values('win_rate', ascending=False)
    return out

@st.cache_data
def compute_item_stats(df: pd.DataFrame, item_list: List[str]=None) -> pd.DataFrame:
    item_cols = [c for c in df.columns if c.startswith('item')]
    records = []
    for c in item_cols:
        tmp = df[[ 'matchId', 'win_clean', c]].rename(columns={c:'item'})
        records.append(tmp)
    union = pd.concat(records, axis=0, ignore_index=True)
    union = union[union['item'].astype(str) != '']
    if item_list:
        union = union[union['item'].isin(item_list)]
    stats = (union.groupby('item')
             .agg(total_picks=('matchId','count'), wins=('win_clean','sum'))
             .reset_index())
    stats['win_rate'] = (stats['wins'] / stats['total_picks'] * 100).round(2)
    stats = stats.sort_values('win_rate', ascending=False)
    return stats

@st.cache_data
def compute_core_combo_stats(df: pd.DataFrame, core_slots: List[str]=['item0','item1','item2']) -> pd.DataFrame:
    tmp = df[core_slots + ['matchId','win_clean']].copy()
    # 정렬하여 순서 무시 조합을 만들려면 빈값 제외 후 정렬
    def make_key(row):
        items = [str(row[c]).strip() for c in core_slots if str(row[c]).strip()!='']
        if not items:
            return ''
        items_sorted = sorted(items)
        return '|'.join(items_sorted)
    tmp['core_set'] = tmp.apply(make_key, axis=1)
    tmp = tmp[tmp['core_set']!='']
    stats = (tmp.groupby('core_set')
             .agg(total_games=('matchId','count'), wins=('win_clean','sum'))
             .reset_index())
    stats['win_rate'] = (stats['wins']/stats['total_games']*100).round(2)
    stats = stats.sort_values('win_rate', ascending=False)
    return stats

@st.cache_data
def compute_rune_stats(df: pd.DataFrame) -> pd.DataFrame:
    stats = (df.groupby(['rune_core','rune_sub'])
             .agg(total_games=('matchId','count'), wins=('win_clean','sum'))
             .reset_index())
    stats['win_rate'] = (stats['wins']/stats['total_games']*100).round(2)
    stats = stats.sort_values('win_rate', ascending=False)
    return stats

@st.cache_data
def compute_teammate_synergy(df: pd.DataFrame, champion: str, top_n:int=3) -> pd.DataFrame:
    # 같은 매치, 같은 팀의 다른 챔피언들과의 조합
    a = df[['matchId','teamId','champion','win_clean','summonerName']].copy()
    b = a.rename(columns={'champion':'teammate','summonerName':'teammateName'})
    merged = a.merge(b, on=['matchId','teamId'], how='inner')
    merged = merged[merged['champion'] != merged['teammate']]
    merged = merged[merged['champion'] == champion]
    stats = (merged.groupby('teammate')
             .agg(games_together=('matchId','count'), wins=('win_clean_x','sum'))
             .reset_index())
    stats['win_rate'] = (stats['wins']/stats['games_together']*100).round(2)
    stats = stats.sort_values('win_rate', ascending=False).head(top_n)
    return stats

# --- 로드 데이터 ---
with st.spinner('Loading data...'):
    df = load_data(CSV_PATH)

# --- 사이드바 ---
st.sidebar.title('ARAM PS Controls')
view = st.sidebar.radio('View', ['Overview','Champion','Items','Synergy','Raw Data'])

# --- Overview ---
if view == 'Overview':
    st.title('ARAM PS — Overview')
    st.markdown('Dataset summary')
    col1, col2, col3 = st.columns(3)
    total_matches = df['matchId'].nunique()
    total_players = df['summonerName'].nunique()
    total_games = len(df)
    col1.metric('Matches', total_matches)
    col2.metric('Players', total_players)
    col3.metric('Rows', total_games)

    champ_stats = compute_champion_stats(df)
    fig = px.bar(champ_stats.head(20), x='champion', y='win_rate', title='Top 20 Champion Win Rate')
    st.plotly_chart(fig, use_container_width=True)

# --- Champion view ---
if view == 'Champion':
    st.title('Champion Stats')
    champ_stats = compute_champion_stats(df)
    c = st.selectbox('Champion', ['All'] + champ_stats['champion'].tolist())
    if c == 'All':
        st.dataframe(champ_stats)
        fig = px.bar(champ_stats.head(30), x='champion', y='win_rate', title='Champion Win Rate')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.subheader(f'{c} 상세')
        sub = df[df['champion']==c]
        st.write('Games:', len(sub))
        st.write('Win rate:', sub['win_clean'].mean()*100)
        # 아이템 빈도
        item_stats = compute_item_stats(sub)
        st.subheader('Item pick stats (All slots)')
        st.dataframe(item_stats.head(50))
        fig = px.bar(item_stats.head(20), x='item', y='win_rate', title='Item Win Rate (top 20)')
        st.plotly_chart(fig, use_container_width=True)

# --- Items view ---
if view == 'Items':
    st.title('Item Stats')
    # 사용자 정의 신발 리스트 입력 가능
    default_boots = ['광전사의 군화','마법사의 신발','닌자의 신발','헤르메스의 발걸음','신속의 장화','명석함의 아이오니아 장화','기동력의 장화']
    boots_input = st.text_area('Boots (one per line)', value='\n'.join(default_boots), height=120)
    boots = [b.strip() for b in boots_input.splitlines() if b.strip()!='']

    st.subheader('Selected boots win rate')
    boot_stats = compute_item_stats(df, item_list=boots)
    st.dataframe(boot_stats)
    if not boot_stats.empty:
        fig = px.bar(boot_stats, x='item', y='win_rate', title='Boots Win Rate')
        st.plotly_chart(fig, use_container_width=True)

    st.subheader('Core combos (1~3)')
    core_stats = compute_core_combo_stats(df)
    st.dataframe(core_stats.head(50))

# --- Synergy view ---
if view == 'Synergy':
    st.title('Synergy & Spells')
    champ_list = sorted(df['champion'].unique().tolist())
    selected = st.selectbox('Champion', champ_list)
    topn = st.slider('Top N teammates', 1, 10, 3)
    if selected:
        st.subheader('Top teammates by win rate')
        syn = compute_teammate_synergy(df, selected, topn)
        st.dataframe(syn)

    st.subheader('Spell combos')
    spell_stats = (df.groupby(['spell1','spell2']).agg(total_games=('matchId','count'), wins=('win_clean','sum')).reset_index())
    spell_stats['win_rate'] = (spell_stats['wins']/spell_stats['total_games']*100).round(2)
    spell_stats = spell_stats.sort_values('win_rate', ascending=False)
    st.dataframe(spell_stats.head(50))

# --- Raw Data view ---
if view == 'Raw Data':
    st.title('Raw Data')
    st.dataframe(df)

# 하단 안내
st.markdown('---')
st.write('앱: 로컬 CSV를 기반으로 동작합니다. CSV 경로가 다르면 코드 상단의 CSV_PATH를 수정하세요.')
