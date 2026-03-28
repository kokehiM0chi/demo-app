import pandas as pd
from flask import Flask, jsonify
from flask_cors import CORS
import os
from cachetools import TTLCache  # 追加

app = Flask(__name__)
# React(通常はport 5173など)からのアクセスを許可
CORS(app)

# キャッシュの設定: 最大1つのデータセットを保持、有効期限(ttl)は43200秒（12時間）
# cache = TTLCache(maxsize=1, ttl=300)
cache = TTLCache(maxsize=1, ttl=43200)

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRtQT_N7fhV5opDRkTin8EfZ9D6xbB6uHR5siCpryF7tfEy2rFoLbtXgE6o4xsyOXooRVm9WETZAuIV/pub?output=csv"

@app.route('/api/recipes')
def get_recipes():
    # 1. キャッシュに有効なデータがあるか確認
    if "recipe_data" in cache:
        return jsonify(cache["recipe_data"])

    # 2. キャッシュがない（または期限切れ）場合はGoogle Sheetsへ
    try:
        df = pd.read_csv(CSV_URL)
        # NaN（空のセル）を空文字に置き換えてリスト形式の辞書にする
        recipes = df.fillna('').to_dict(orient='records')

        # 3. 取得したデータをキャッシュに保存
        cache["recipe_data"] = recipes

        return jsonify(recipes)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 54321))
    print(f"API Server running on http://localhost:{port}/api/recipes")
    app.run(host='0.0.0.0', port=port, debug=True)
