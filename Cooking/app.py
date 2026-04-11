import pandas as pd
from flask import Flask, jsonify, request
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
    """全件取得用エンドポイント"""
    try:
        if "recipe_data" in cache:
            all_recipes = cache["recipe_data"]
        else:
            df = pd.read_csv(Config.CSV_URL)
            all_recipes = df.fillna('').to_dict(orient='records')
            cache["recipe_data"] = all_recipes
            logger.info("Fetched all recipes and cached.")

        return jsonify(all_recipes)
    except Exception as e:
        logger.error(f"Error in get_recipes: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/search', strict_slashes=False)
def search_recipes():
    category = request.args.get('category', '')
    query = request.args.get('q', '').lower()

    # --- 同義語マッピングの定義 ---
    # ユーザーが「スイーツ」を選んだ時、内部的に「デザート」「焼き菓子」「ケーキ」等もヒットさせる
    synonyms = {
        "スイーツ": ["デザート", "焼き菓子", "菓子", "ケーキ", "パフェ"],
        "肉": ["牛肉", "豚肉", "鶏肉", "ミンチ"],
    }

    if "recipe_data" not in cache:
        get_recipes()
    all_recipes = cache.get("recipe_data", [])

    filtered = []
    for r in all_recipes:
        cat_value = str(r.get('カテゴリ', ''))
        name_value = str(r.get('料理名', '')).lower()

        # カテゴリ検索のロジック強化
        match_cat = False
        if not category or category == "すべて":
            match_cat = True
        elif category == "スイーツ":
            # スイーツを選んだ場合、同義語のどれかがカテゴリに含まれていればOK
            search_targets = synonyms.get("スイーツ", []) + ["スイーツ"]
            match_cat = any(target in cat_value for target in search_targets)
        else:
            match_cat = category in cat_value

        # キーワード検索
        match_query = not query or query in name_value

        if match_cat and match_query:
            filtered.append(r)

    return jsonify(filtered)

@app.route('/api/recipes/clear', strict_slashes=False)
def clear_cache():
    cache.clear()
    logger.info("ACTION: Cache cleared by manual request.")
    return jsonify({"status": "cleared"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 54321))
    logger.info(Config.STARTUP_MSG)
    app.run(host='0.0.0.0', port=port, debug=Config.DEBUG)
