import streamlit as st
import pandas as pd
import os
import pathlib  # 추가: 더 안정적인 경로 처리용 (Streamlit Cloud 호환성 향상)

# ... (기존 import와 set_page_config 유지)

# CSV_PATH 설정: 리포지토리 루트 기준 상대 경로 (Streamlit Cloud에서 작동하도록)
CSV_PATH = "aram_participants_clean_preprocessed.csv"  # 파일명 맞게 확인 (리포지토리 루트에 업로드 필요)

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    # 동적 경로 구성: pathlib로 클라우드 환경에서 안정적으로 처리
    current_dir = pathlib.Path(__file__).parent.resolve()  # app.py의 디렉토리 기준
    full_path = current_dir / path  # 파일 경로 결합 (Streamlit Cloud에서 /app 기준으로 작동)
    
    # 파일 존재 확인 (디버깅용)
    if not os.path.exists(full_path):
        st.error(f"파일을 찾을 수 없음: {full_path}")
        st.write(f"현재 작업 디렉토리: {os.getcwd()}")
        st.info("Streamlit Cloud 사용 중이라면, GitHub 리포지토리 루트에 파일을 업로드하고 앱을 재배포하세요.")
        return pd.DataFrame()  # 빈 DataFrame 반환으로 앱 중단 방지
    
    df = pd.read_csv(full_path)
    # win 컬럼 정리 (기존 로직 유지)
    if 'win' in df.columns:
        df['win_clean'] = df['win'].apply(lambda x: 1 if str(x).lower() in ('1','true','t','yes') else 0)
    else:
        df['win_clean'] = 0
    item_cols = [c for c in df.columns if c.startswith('item')]
    for c in item_cols:
        df[c] = df[c].fillna('').astype(str).str.strip()
    return df

# ... (compute_champion_stats 등 기존 함수 유지)

# 로드 부분 (기존 with st.spinner 유지)
with st.spinner('Loading data...'):
    df = load_data(CSV_PATH)

# ... (사이드바, 챔피언 요약 등 기존 코드 유지)
