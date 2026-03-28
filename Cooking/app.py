import pandas as pd
from flask import Flask, jsonify
from flask_cors import CORS
import os
import logging
import sys
from cachetools import TTLCache

app = Flask(__name__)
CORS(app)

# --- ログ設定の強化 ---
# Renderなどの環境で即座に出力されるよう、StreamHandlerを明示的に設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# 12時間キャッシュ
cache = TTLCache(maxsize=1, ttl=43200)

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRtQT_N7fhV5opDRkTin8EfZ9D6xbB6uHR5siCpryF7tfEy2rFoLbtXgE6o4xsyOXooRVm9WETZAuIV/pub?output=csv"

@app.route('/api/recipes')
def get_recipes():
    if "recipe_data" in cache:
        logger.info("Cache hit. Returning cached data.")
        return jsonify(cache["recipe_data"])

    logger.info("START: Fetching data from Google Sheets...")
    try:
        # スプレッドシート読み込み
        df = pd.read_csv(CSV_URL)
        recipes = df.fillna('').to_dict(orient='records')

        # キャッシュに保存
        cache["recipe_data"] = recipes

        logger.info(f"SUCCESS: Data fetched and cached. Total recipes: {len(recipes)}")
        return jsonify(recipes)
    except Exception as e:
        logger.error(f"Fetch failed: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/recipes/clear')
def clear_cache():
    cache.clear()
    logger.info("ACTION: Cache cleared by manual request.")
    return jsonify({"status": "cleared"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 54321))
    logger.info(f"Server starting on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)
