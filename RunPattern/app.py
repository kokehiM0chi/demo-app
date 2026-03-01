import pandas as pd
import matplotlib.pyplot as plt
import os
import glob
from datetime import timedelta
import matplotlib.patches as mpatches

# --- 設定 ---
DATA_DIR = "data"
TARGET_TIME_LIMIT = 2820  # 47分以内
MIN_DISTANCE = 9.0        # 9km以上
ANALYSIS_WINDOW = 21      # 直前3週間

# 曜日リストの定義
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

def analyze_best_patterns(df, target_sec, window):
    targets = df[(df['タイム秒'] <= target_sec) & (df['距離'] >= MIN_DISTANCE)].copy()
    
    if targets.empty:
        print("❌ 条件に合う記録が見つかりませんでした。")
        return

    print(f"✅ {len(targets)} 件の好記録を発見。分析を開始。")

    for _, row in targets.iterrows():
        target_date = row['日付']
        # ★ターゲット日の曜日を取得
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
        
        # X軸ラベルに曜日を挿入
        x_labels = [f"{d.strftime('%m/%d')}\n({WEEKDAYS_JP[d.weekday()]})" for d in all_days]
        
        colors = []
        for p in pace_vals:
            if pd.isna(p) or p == 0:
                colors.append('#f1f2f6') # Rest
            elif p <= 270: colors.append('#e74c3c') # Fast
            elif p <= 300: colors.append('#e67e22') # Steady
            elif p <= 360: colors.append('#f1c40f') # Mid (5分台)
            elif p <= 420: colors.append('#3498db') # Slow (6分台)
            else: colors.append('#9b59b6') # Very Slow

        plt.bar(x_labels, dist_vals, color=colors, edgecolor='#7f8c8d', alpha=0.85)
        
        # ★タイトルに曜日を追加
        plt.title(f"Target: {row['タイム']} ({row['距離']}km) on {target_date.date()} ({target_dow})", fontsize=15, fontweight='bold')
        plt.ylabel("Distance (km)")
        plt.grid(axis='y', linestyle='--', alpha=0.3)
        
        legend_elements = [
            mpatches.Patch(color='#e74c3c', label='Fast (< 4:30)'),
            mpatches.Patch(color='#e67e22', label='Steady (4:30-5:00)'),
            mpatches.Patch(color='#f1c40f', label='Moderate (5:00-6:00)'),
            mpatches.Patch(color='#3498db', label='Slow (6:00-7:00)'),
            mpatches.Patch(color='#9b59b6', label='Very Slow (> 7:00)'),
            mpatches.Patch(color='#f1f2f6', label='Rest')
        ]
        plt.legend(handles=legend_elements, loc='upper left', fontsize=9, framealpha=0.9)

        total_vol = dist_vals.sum()
        plt.text(0.5, 0.95, f"3-Week Total: {total_vol:.1f} km", 
                 transform=plt.gca().transAxes, ha='center', fontweight='bold', fontsize=12,
                 bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))

        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    path = get_latest_csv()
    if path:
        data = load_and_clean_data(path)
        analyze_best_patterns(data, TARGET_TIME_LIMIT, ANALYSIS_WINDOW)
