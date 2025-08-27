import pandas as pd
import os

def analyze_and_save_data(df, selected_champion):
    """아이템과 스펠 데이터를 분석하고 CSV로 저장"""
    
    # 선택된 챔피언 데이터만 필터링
    champion_data = df[df["champion"] == selected_champion].copy()
    
    print(f"=== {selected_champion} 데이터 분석 ===")
    print(f"총 게임 수: {len(champion_data)}")
    
    # 1. 아이템 데이터 추출 및 저장
    item_cols = [c for c in champion_data.columns if c.startswith("item")]
    print(f"아이템 컬럼들: {item_cols}")
    
    items_data = []
    for idx, row in champion_data.iterrows():
        for col in item_cols:
            item_value = row[col]
            # 다양한 형태의 빈 값들 체크
            if pd.notna(item_value) and str(item_value).strip() not in ["", "0", "nan", "None"]:
                items_data.append({
                    "matchId": row.get("matchId", idx),
                    "gameIndex": idx,
                    "win_clean": row.get("win_clean", 0),
                    "item": str(item_value).strip(),
                    "item_slot": col,
                    "champion": selected_champion
                })
    
    if items_data:
        items_df = pd.DataFrame(items_data)
        items_filename = f"{selected_champion}_items_analysis.csv"
        items_df.to_csv(items_filename, index=False, encoding='utf-8')
        
        # 아이템 통계
        item_stats = (items_df.groupby("item")
                     .agg(
                         total_games=("matchId", "count"),
                         wins=("win_clean", "sum")
                     )
                     .assign(win_rate=lambda d: (d.wins/d.total_games*100).round(2))
                     .sort_values(["total_games", "win_rate"], ascending=[False, False]))
        
        stats_filename = f"{selected_champion}_item_stats.csv" 
        item_stats.to_csv(stats_filename, encoding='utf-8')
        
        print(f"✅ 아이템 데이터 저장: {items_filename}")
        print(f"✅ 아이템 통계 저장: {stats_filename}")
        print(f"고유 아이템 수: {len(item_stats)}")
        print("상위 5개 아이템:")
        print(item_stats.head())
    else:
        print("❌ 아이템 데이터를 찾을 수 없습니다")
    
    # 2. 스펠 데이터 추출 및 저장
    spell_cols = []
    for col in ["spell1", "spell2", "spell1_name", "spell2_name"]:
        if col in champion_data.columns:
            spell_cols.append(col)
    
    print(f"스펠 컬럼들: {spell_cols}")
    
    spells_data = []
    for idx, row in champion_data.iterrows():
        # spell1, spell2 처리
        s1_col = "spell1_name" if "spell1_name" in champion_data.columns else "spell1"
        s2_col = "spell2_name" if "spell2_name" in champion_data.columns else "spell2"
        
        spell1 = str(row.get(s1_col, "")).strip()
        spell2 = str(row.get(s2_col, "")).strip()
        
        if spell1 and spell1 not in ["", "nan", "None"]:
            spells_data.append({
                "matchId": row.get("matchId", idx),
                "gameIndex": idx,
                "win_clean": row.get("win_clean", 0),
                "spell": spell1,
                "spell_slot": "spell1",
                "spell_combo": f"{spell1} + {spell2}",
                "champion": selected_champion
            })
        
        if spell2 and spell2 not in ["", "nan", "None"]:
            spells_data.append({
                "matchId": row.get("matchId", idx),
                "gameIndex": idx,
                "win_clean": row.get("win_clean", 0),
                "spell": spell2,
                "spell_slot": "spell2", 
                "spell_combo": f"{spell1} + {spell2}",
                "champion": selected_champion
            })
    
    if spells_data:
        spells_df = pd.DataFrame(spells_data)
        spells_filename = f"{selected_champion}_spells_analysis.csv"
        spells_df.to_csv(spells_filename, index=False, encoding='utf-8')
        
        # 스펠 조합 통계
        combo_stats = (spells_df.drop_duplicates(["matchId", "spell_combo"])
                      .groupby("spell_combo")
                      .agg(
                          total_games=("matchId", "count"),
                          wins=("win_clean", "sum")
                      )
                      .assign(win_rate=lambda d: (d.wins/d.total_games*100).round(2))
                      .sort_values(["total_games", "win_rate"], ascending=[False, False]))
        
        combo_filename = f"{selected_champion}_spell_combo_stats.csv"
        combo_stats.to_csv(combo_filename, encoding='utf-8')
        
        print(f"✅ 스펠 데이터 저장: {spells_filename}")
        print(f"✅ 스펠 조합 통계 저장: {combo_filename}")
        print(f"고유 스펠 조합 수: {len(combo_stats)}")
        print("상위 5개 스펠 조합:")
        print(combo_stats.head())
    else:
        print("❌ 스펠 데이터를 찾을 수 없습니다")
    
    # 3. 원본 데이터 구조 분석
    structure_filename = f"{selected_champion}_data_structure.txt"
    with open(structure_filename, 'w', encoding='utf-8') as f:
        f.write(f"=== {selected_champion} 데이터 구조 분석 ===\n\n")
        f.write(f"총 게임 수: {len(champion_data)}\n")
        f.write(f"컬럼 수: {len(champion_data.columns)}\n\n")
        
        f.write("=== 컬럼 정보 ===\n")
        for col in champion_data.columns:
            f.write(f"{col}: {champion_data[col].dtype}\n")
        
        f.write(f"\n=== 아이템 컬럼 샘플 ===\n")
        for col in item_cols[:3]:  # 처음 3개만
            sample_values = champion_data[col].dropna().unique()[:5]
            f.write(f"{col}: {list(sample_values)}\n")
        
        f.write(f"\n=== 스펠 컬럼 샘플 ===\n")
        for col in spell_cols:
            sample_values = champion_data[col].dropna().unique()[:5]
            f.write(f"{col}: {list(sample_values)}\n")
    
    print(f"✅ 데이터 구조 분석 저장: {structure_filename}")
    
    return {
        "items_file": items_filename if items_data else None,
        "spells_file": spells_filename if spells_data else None,
        "structure_file": structure_filename
    }

# Streamlit 앱에 추가할 버튼
def add_data_export_button(df, selected_champion):
    """데이터 분석 및 내보내기 버튼을 Streamlit에 추가"""
    
    if st.button("📊 데이터 분석 & CSV 저장"):
        with st.spinner("데이터 분석 중..."):
            result = analyze_and_save_data(df, selected_champion)
            
            st.success("✅ 데이터 분석 완료!")
            
            # 다운로드 링크 생성
            if result["items_file"] and os.path.exists(result["items_file"]):
                with open(result["items_file"], "rb") as f:
                    st.download_button(
                        label="📦 아이템 데이터 다운로드",
                        data=f.read(),
                        file_name=result["items_file"],
                        mime="text/csv"
                    )
            
            if result["spells_file"] and os.path.exists(result["spells_file"]):
                with open(result["spells_file"], "rb") as f:
                    st.download_button(
                        label="✨ 스펠 데이터 다운로드", 
                        data=f.read(),
                        file_name=result["spells_file"],
                        mime="text/csv"
                    )
            
            if result["structure_file"] and os.path.exists(result["structure_file"]):
                with open(result["structure_file"], "rb") as f:
                    st.download_button(
                        label="📋 데이터 구조 분석 다운로드",
                        data=f.read(),
                        file_name=result["structure_file"],
                        mime="text/plain"
                    )
