import gpxpy
import pandas as pd
import os

def convert_gpx_to_csv(input_file='cleaned_route.gpx', output_file='route.csv'):
    if not os.path.exists(input_file):
        print(f"❌ {input_file} が見つかりません。")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        gpx = gpxpy.parse(f)

    data = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                data.append({
                    'latitude': point.latitude,
                    'longitude': point.longitude,
                    'elevation': point.elevation
                })

    if not data:
        print("⚠️ 座標データがありません。")
        return

    # pandasを使ってCSV出力（uv環境なら pandas を入れてください）
    df = pd.DataFrame(data)
    # 点が多すぎると線にならない場合があるため、ここでも少し間引きます
    df_sampled = df.iloc[::3] 
    
    df_sampled.to_csv(output_file, index=False)
    print(f"✅ {output_file} を作成しました。({len(df_sampled)} points)")

if __name__ == "__main__":
    # pandasがない場合は uv pip install pandas してください
    convert_gpx_to_csv()
