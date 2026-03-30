import pandas as pd
from flask import Flask, jsonify
from flask_cors import CORS
import os
import logging
import sys
from cachetools import TTLCache
from config import Config

app = Flask(__name__)
# CORSの許可ドメインをConfigから取得
CORS(app, resources={r"/api/*": {"origins": Config.FRONTEND_URL}})

# --- ログ設定の強化 ---
# Renderなどの環境で即座に出力されるよう、StreamHandlerを明示的に設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# 12時間キャッシュ
# キャッシュ時間もConfigから取得
cache = TTLCache(maxsize=1, ttl=Config.CACHE_TTL)

@app.route('/api/recipes', strict_slashes=False)
def get_recipes():
    if "recipe_data" in cache:
        logger.info("Cache hit. Returning cached data.")
        return jsonify(cache["recipe_data"])

    logger.info("START: Fetching data from Google Sheets...")
    try:
        # スプレッドシート読み込み
        df = pd.read_csv(Config.CSV_URL)
        recipes = df.fillna('').to_dict(orient='records')

        # キャッシュに保存
        cache["recipe_data"] = recipes

        logger.info(f"SUCCESS: Data fetched and cached. Total recipes: {len(recipes)}")
        return jsonify(recipes)
    except Exception as e:
        logger.error(f"Fetch failed: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/recipes/clear', strict_slashes=False)
def clear_cache():
    cache.clear()
    logger.info("ACTION: Cache cleared by manual request.")
    return jsonify({"status": "cleared"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 54321))
    logger.info(Config.STARTUP_MSG)
    app.run(host='0.0.0.0', port=port, debug=Config.DEBUG)
