import pandas as pd
import matplotlib.pyplot as plt
import os
import glob
from datetime import timedelta
import matplotlib.patches as mpatches

# --- 設定 ---
DATA_DIR = "data"
OUTPUT_DIR = "output_best"
TARGET_TIME_LIMIT = 2820    # 47分以内
MIN_DISTANCE = 9.0
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

def analyze_best_patterns(df, target_sec, window):
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    targets = df[(df['タイム秒'] <= target_sec) & (df['距離'] >= MIN_DISTANCE)].copy()
    if targets.empty:
        print("❌ 条件に合う記録が見つかりませんでした。")
        return

    print(f"✅ {len(targets)} 件の好記録を解析中（画像＋詳細CSV出力）...")

    for _, row in targets.iterrows():
        target_date = row['日付']
        target_dow = WEEKDAYS_JP[target_date.weekday()]
        start_date = target_date - timedelta(days=window)
        
        pre_period = df[(df['日付'] >= start_date) & (df['日付'] < target_date)]
        all_days = pd.date_range(start=start_date, periods=window, freq='D')
        
        daily_summary = pre_period.groupby('日付').agg({'距離': 'sum', 'タイム秒': 'sum'})
        daily_summary['平均ペース'] = daily_summary['タイム秒'] / daily_summary['距離']
        
        daily_data = daily_summary.reindex(all_days)
        
        # --- CSVデータの作成 ---
        csv_data = daily_data.copy()
        csv_data.index.name = 'Date'
        csv_data['Day'] = [WEEKDAYS_JP[d.weekday()] for d in all_days]
        
        # 秒数を「分:秒」または「時:分:秒」に変換する関数
        def format_time(total_seconds):
            if pd.isna(total_seconds) or total_seconds == 0: return ""
            h = int(total_seconds // 3600)
            m = int((total_seconds % 3600) // 60)
            s = int(total_seconds % 60)
            if h > 0: return f"{h}:{m:02d}:{s:02d}"
            return f"{m}:{s:02d}"

        # 走行時間とペースをフォーマット
        csv_data['Time'] = csv_data['タイム秒'].apply(format_time)
        csv_data['Pace'] = csv_data['平均ペース'].apply(format_time)
        csv_data['Distance(km)'] = csv_data['距離'].fillna(0)

        # ファイル名の生成
        clean_time = str(row['タイム']).replace(':', 'm') + 's'
        base_name = f"{target_date.date()}_{clean_time}"
        
        # 1. CSV保存 (列の順番を指定: Day, Distance, Time, Pace)
        csv_path = os.path.join(OUTPUT_DIR, f"{base_name}.csv")
        csv_data[['Day', 'Distance(km)', 'Time', 'Pace']].to_csv(csv_path, encoding='utf-8-sig')

        # --- 2. グラフ描画 & 保存 ---
        dist_vals = daily_data['距離'].fillna(0).values
        pace_vals = daily_data['平均ペース'].values

        plt.figure(figsize=(15, 7))
        x_labels = [f"{d.strftime('%m/%d')}\n({WEEKDAYS_JP[d.weekday()]})" for d in all_days]
        
        colors = []
        for p in pace_vals:
            if pd.isna(p) or p == 0: colors.append('#f1f2f6')
            elif p <= 270: colors.append('#e74c3c')
            elif p <= 300: colors.append('#e67e22')
            elif p <= 360: colors.append('#f1c40f')
            elif p <= 420: colors.append('#3498db')
            else: colors.append('#9b59b6')

        plt.bar(x_labels, dist_vals, color=colors, edgecolor='#7f8c8d', alpha=0.85)
        plt.title(f"Target: {row['タイム']} ({row['距離']}km) on {target_date.date()} ({target_dow})", fontsize=15, fontweight='bold')
        plt.ylabel("Distance (km)")
        plt.tight_layout()
        
        png_path = os.path.join(OUTPUT_DIR, f"{base_name}.png")
        plt.savefig(png_path)
        plt.close()
        
        print(f"💾 保存完了: {base_name} (.png & .csv)")

if __name__ == "__main__":
    path = get_latest_csv()
    if path:
        data = load_and_clean_data(path)
        analyze_best_patterns(data, TARGET_TIME_LIMIT, ANALYSIS_WINDOW)
