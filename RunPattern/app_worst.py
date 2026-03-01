import pandas as pd
import matplotlib.pyplot as plt
import os
import glob
from datetime import timedelta
import matplotlib.patches as mpatches

# --- 設定 ---
DATA_DIR = "data"
BAD_TIME_LIMIT = 3000     # 50分超え
MIN_DISTANCE = 9.0
MAX_DISTANCE = 11.0
ANALYSIS_WINDOW = 21

WEEKDAYS_JP = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def get_latest_csv():
    if not os.path.exists(DATA_DIR): return None
    csv_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    return max(csv_files, key=os.path.getmtime) if csv_files else None

def load_and_clean_data(file_path):
    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig')
    except:
        df = pd.read_csv(file_path, encoding='cp932')
    
    df.columns = df.columns.str.strip()
    df['日付'] = pd.to_datetime(df['日付']).dt.normalize()
    
    def time_to_seconds(t_str):
        if pd.isna(t_str) or t_str == '--' or t_str == '': return None
        try:
            parts = list(map(float, str(t_str).split(':')))
            if len(parts) == 3: return parts[0] * 3600 + parts[1] * 60 + parts[2]
            elif len(parts) == 2: return parts[0] * 60 + parts[1]
        except: return None
        return None
    
    df['タイム秒'] = df['タイム'].apply(time_to_seconds)
    df['距離'] = pd.to_numeric(df['距離'].astype(str).str.replace(',', ''), errors='coerce')
    df['ペース秒'] = df['タイム秒'] / df['距離']
    df = df[df['アクティビティタイプ'].str.contains('ラン', na=False)].sort_values('日付')
    return df

def analyze_worst_patterns(df, bad_sec, window):
    # 府中・北区のフィルタリング
    mask = (
        (df['タイム秒'] > bad_sec) & 
        (df['距離'] >= MIN_DISTANCE) & 
        (df['距離'] <= MAX_DISTANCE) &
        (df['タイトル'].str.contains('府中|北区', na=False, case=False))
    )
    targets = df[mask].copy()
    
    if targets.empty:
        print("❌ 条件に合うワースト記録が見つかりませんでした。")
        return

    print(f"⚠️ {len(targets)} 件のワースト記録を発見。分析を開始。")

    for _, row in targets.iterrows():
        # --- 文字化け対策: 地名をローマ字に変換して表示 ---
        raw_title = str(row['タイトル'])
        display_location = "Unknown"
        if "府中" in raw_title: display_location = "Fuchu"
        elif "北区" in raw_title: display_location = "Kita-ku"
        else: display_location = "Other"

        target_date = row['日付']
        target_dow = WEEKDAYS_JP[target_date.weekday()]
        
        start_date = target_date - timedelta(days=window)
        pre_period = df[(df['日付'] >= start_date) & (df['日付'] < target_date)]
        all_days = pd.date_range(start=start_date, periods=window, freq='D')
        
        daily_summary = pre_period.groupby('日付').agg({'距離': 'sum', 'タイム秒': 'sum'})
        daily_summary['平均ペース'] = daily_summary['タイム秒'] / daily_summary['距離']
        
        daily_data = daily_summary.reindex(all_days)
        dist_vals = daily_data['距離'].fillna(0).values
        pace_vals = daily_data['平均ペース'].values

        # --- グラフ描画 ---
        plt.figure(figsize=(15, 7))
        x_labels = [f"{d.strftime('%m/%d')}\n({WEEKDAYS_JP[d.weekday()]})" for d in all_days]
        
        colors = []
        for p in pace_vals:
            if pd.isna(p) or p == 0: colors.append('#f1f2f6')
            elif p <= 270: colors.append('#c0392b')
            elif p <= 300: colors.append('#d35400')
            elif p <= 360: colors.append('#f39c12')
            elif p <= 420: colors.append('#2980b9')
            else: colors.append('#8e44ad')

        plt.bar(x_labels, dist_vals, color=colors, edgecolor='#7f8c8d', alpha=0.7)
        
        # タイトルから日本語を排除
        plt.title(f"WORST PATTERN: {row['タイム']} ({row['距離']}km) at {display_location}\n{target_date.date()} ({target_dow})", 
                  fontsize=15, fontweight='bold', color='#c0392b')
        
        plt.ylabel("Distance (km)")
        plt.grid(axis='y', linestyle='--', alpha=0.3)
        
        legend_elements = [
            mpatches.Patch(color='#c0392b', label='Fast (< 4:30)'),
            mpatches.Patch(color='#d35400', label='Steady (4:30-5:00)'),
            mpatches.Patch(color='#f39c12', label='Moderate (5:00-6:00)'),
            mpatches.Patch(color='#2980b9', label='Slow (6:00-7:00)'),
            mpatches.Patch(color='#8e44ad', label='Very Slow (> 7:00)'),
            mpatches.Patch(color='#f1f2f6', label='Rest')
        ]
        plt.legend(handles=legend_elements, loc='upper left', fontsize=9)

        total_vol = dist_vals.sum()
        plt.text(0.5, 0.95, f"3-Week Total Volume: {total_vol:.1f} km", 
                 transform=plt.gca().transAxes, ha='center', fontweight='bold', fontsize=12,
                 bbox=dict(facecolor='white', alpha=0.8, edgecolor='red'))

        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    path = get_latest_csv()
    if path:
        data = load_and_clean_data(path)
        analyze_worst_patterns(data, BAD_TIME_LIMIT, ANALYSIS_WINDOW)
