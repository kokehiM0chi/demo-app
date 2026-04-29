import json

# 1. JSON形式のファイルを読み込む
with open('hoge.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    gpx_content = data['gpx']

# 2. 純粋なGPX（XML形式）として保存し直す
with open('cleaned_route.gpx', 'w', encoding='utf-8') as f:
    f.write(gpx_content)

print("✅ Googleマップ用の cleaned_route.gpx を作成しました。")
