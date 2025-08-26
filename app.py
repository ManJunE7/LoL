"""
Streamlit ARAM '롤 PS' 스타일 대시보드 (승률 + 픽률)
File: streamlit_aram_ps_app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from typing import List

st.set_page_config(page_title="ARAM PS Dashboard", layout="wide")

# --- 설정: 로컬 CSV 경로 ---
CSV_PATH = "./aram_participants_clean_preprocessed.csv"

# --- 데이터 로드 ---
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # win 컬럼 정리
    if 'win' in df.columns:
        df['win_clean'] = df['win'].apply(lambda x: 1 if str(x).lower() in ('1','true','t','yes') else 0)
    else:
        df['win_clean'] = 0

    # item 컬럼명 리스트
    item_cols = [c for c in df.columns if c.startswith('item')]
    for c in item_cols:
        df[c] = df[c].fillna('').astype(str).str.strip()
    return df

# --- 챔피언 통계 ---
@st.cache_data
def compute_champion_stats(df: pd.DataFrame) -> pd.DataFrame:
    out = (df.groupby('champion')
           .agg(total_games=('matchId','count'), wins=('win_clean','sum'))
           .reset_index())
    out['win_rate'] = (out['wins'] / out['total_games'] * 100).round(2)
    total_matches = df['matchId'].nunique()
    out['pick_rate'] = (out['total_games'] / total_matches * 100).round(2)
    out = out.sort_values('win_rate', ascending=False)
    return out

# --- 아이템 통계 ---
@st.cache_data
def compute_item_stats(df: pd.DataFrame, item_list: List[str]=None) -> pd.DataFrame:
    item_cols = [c for c in df.columns if c.startswith('item')]
    records = []
    for c in item_cols:
        tmp = df[['matchId','win_clean',c]].rename(columns={c:'item'})
        records.append(tmp)
    union = pd.concat(records, axis=0, ignore_index=True)
    union = union[union['item'].astype(str) != '']
    if item_list:
        union = union[union['item'].isin(item_list)]
    stats = (union.groupby('item')
             .agg(total_picks=('matchId','count'), wins=('win_clean','sum'))
             .reset_index())
    stats['win_rate'] = (stats['wins'] / stats['total_picks'] * 100).round(2)
    total_matches = df['matchId'].nunique()
    stats['pick_rate'] = (stats['total_picks'] / total_matches * 100).round(2)
    stats = stats.sort_values('win_rate', ascending=False)
    return stats

# --- 코어 아이템 조합 통계 ---
@st.cache_data
def compute_core_combo_stats(df: pd.DataFrame, core_slots: List[str]=['item0','item1','item2']) -> pd.DataFrame:
    tmp = df[core_slots + ['matchId','win_clean']].copy()
    def make_key(row):
        items = [str(row[c]).strip() for c in core_slots if str(row[c]).strip() != '']
        return '|'.join(sorted(items)) if items else ''
    tmp['core_set'] = tmp.apply(make_key, axis=1)
    tmp = tmp[tmp['core_set'] != '']
    stats = (tmp.groupby('core_set')
             .agg(total_games=('matchId','count'), wins=('win_clean','sum'))
             .reset_index())
    stats['win_rate'] = (stats['wins']/stats['total_games']*100).round(2)
    total_matches = df['matchId'].nunique()
    stats['pick_rate'] = (stats['total_games']/total_matches*100).round(2)
    stats = stats.sort_values('win_rate', ascending=False)
    return stats

# --- 룬 통계 ---
@st.cache_data
def compute_rune_stats(df: pd.DataFrame) -> pd.DataFrame:
    stats = (df.groupby(['rune_core','rune_sub'])
             .agg(total_games=('matchId','count'), wins=('win_clean','sum'))
             .reset_index())
    stats['win_rate'] = (stats['wins']/stats['total_games']*100).round(2)
    total_matches = df['matchId'].nunique()
    stats['pick_rate'] = (stats['total_games']/total_matches*100).round(2)
    stats = stats.sort_values('win_rate', ascending=False)
    return stats

# --- 팀 시너지 통계 ---
@st.cache_data
def compute_teammate_synergy(df: pd.DataFrame, champion: str, top_n:int=3) -> pd.DataFrame:
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

# --- 로드 ---
with st.spinner('Loading data...'):
    df = load_data(CSV_PATH)

# --- 사이드바 ---
st.sidebar.title('ARAM PS Controls')
view = st.sidebar.radio('View', ['Overview','Champion','Items','Synergy','Runes','Raw Data'])

# --- Overview ---
if view == 'Overview':
    st.title('ARAM PS — Overview')
    st.markdown('Dataset summary')
    col1, col2, col3 = st.columns(3)
    col1.metric('Matches', df['matchId'].nunique())
    col2.metric('Players', df['summonerName'].nunique())
    col3.metric('Rows', len(df))

    champ_stats = compute_champion_stats(df)
    st.subheader('Top 20 Champion Win Rate / Pick Rate')
    fig = px.bar(champ_stats.head(20), x='champion', y=['win_rate','pick_rate'], barmode='group')
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(champ_stats.head(50))

# --- Champion view ---
if view == 'Champion':
    st.title('Champion Stats')
    champ_stats = compute_champion_stats(df)
    c = st.selectbox('Champion', ['All'] + champ_stats['champion'].tolist())
    if c == 'All':
        st.dataframe(champ_stats)
        fig = px.bar(champ_stats.head(30), x='champion', y=['win_rate','pick_rate'], barmode='group')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.subheader(f'{c} 상세')
        sub = df[df['champion']==c]
        st.write('Games:', len(sub))
        st.write('Win rate:', round(sub['win_clean'].mean()*100,2))
        st.write('Pick rate:', round(len(sub)/df["matchId"].nunique()*100,2))
        # 아이템
        item_stats = compute_item_stats(sub)
        st.subheader('Item pick stats (All slots)')
        st.dataframe(item_stats.head(50))
        fig = px.bar(item_stats.head(20), x='item', y=['win_rate','pick_rate'], barmode='group')
        st.plotly_chart(fig, use_container_width=True)

# --- Items view ---
if view == 'Items':
    st.title('Item Stats')
    default_boots = ['광전사의 군화','마법사의 신발','닌자의 신발','헤르메스의 발걸음','신속의 장화','명석함의 아이오니아 장화','기동력의 장화']
    boots_input = st.text_area('Boots (one per line)', value='\n'.join(default_boots), height=120)
    boots = [b.strip() for b in boots_input.splitlines() if b.strip() != '']

    st.subheader('Selected boots stats')
    boot_stats = compute_item_stats(df, item_list=boots)
    st.dataframe(boot_stats)
    if not boot_stats.empty:
        fig = px.bar(boot_stats, x='item', y=['win_rate','pick_rate'], barmode='group')
        st.plotly_chart(fig, use_container_width=True)

    st.subheader('Core combos (1~3)')
    core_stats = compute_core_combo_stats(df)
    st.dataframe(core_stats.head(50))
    fig = px.bar(core_stats.head(20), x='core_set', y=['win_rate','pick_rate'], barmode='group')
    st.plotly_chart(fig, use_container_width=True)

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
    spell_stats = (df.groupby(['spell1','spell2'])
                   .agg(total_games=('matchId','count'), wins=('win_clean','sum'))
                   .reset_index())
    spell_stats['win_rate'] = (spell_stats['wins']/spell_stats['total_games']*100).round(2)
    total_matches = df['matchId'].nunique()
    spell_stats['pick_rate'] = (spell_stats['total_games']/total_matches*100).round(2)
    spell_stats = spell_stats.sort_values('win_rate', ascending=False)
    st.dataframe(spell_stats.head(50))

# --- Runes view ---
if view == 'Runes':
    st.title('Rune combos')
    rune_stats = compute_rune_stats(df)
    st.dataframe(rune_stats.head(50))
    fig = px.bar(rune_stats.head(20), x='rune_core', y=['win_rate','pick_rate'], barmode='group', color='rune_sub')
    st.plotly_chart(fig, use_container_width=True)

# --- Raw Data view ---
if view == 'Raw Data':
    st.title('Raw Data')
    st.dataframe(df)

st.markdown('---')
st.write('앱: 로컬 CSV를 기반으로 동작합니다. CSV 경로가 다르면 코드 상단 CSV_PATH를 수정하세요.')
