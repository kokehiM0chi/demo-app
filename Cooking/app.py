import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import logging
import sys
from cachetools import TTLCache
from config import Config
import pandas as pd
from flask import Flask, jsonify, request
from sentence_transformers import SentenceTransformer, util
import torch

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
    query = request.args.get('q', '')

    if "recipe_data" not in cache:
        get_recipes()
    all_recipes = cache.get("recipe_data", [])

    # レシピごとに「意味」を計算するための文章を作成
    # 例：「[カテゴリ] 料理名 材料」という文字列にする
    recipe_texts = [
        f"[{r.get('カテゴリ', '')}] {r.get('料理名', '')} {r.get('作成者', '')} {r.get('コンテキスト', '')} {r.get('材料', '')}"
        for r in all_recipes
    ]

    # 2. レシピ群をベクトル化（キャッシュしておくとより高速ですが、まずはシンプルに）
    recipe_embeddings = model.encode(recipe_texts, convert_to_tensor=True)

    # 3. 検索ワード（または選択されたカテゴリ）をベクトル化
    search_target = f"{category} {query}".strip()
    search_embedding = model.encode(search_target, convert_to_tensor=True)

    # 4. 類似度（コサイン類似度）を計算
    # 0.0 〜 1.0 で数値が出て、高いほど「意味が近い」
    cosine_scores = util.cos_sim(search_embedding, recipe_embeddings)[0]

    # 5. スコアをレシピデータに付与して、スコア順にソート
    results = []
    for i, r in enumerate(all_recipes):
        r_with_score = r.copy()
        r_with_score['score'] = float(cosine_scores[i])
        results.append(r_with_score)

    # スコアが高い順（似ている順）に並び替え
    # 閾値を設けて（例: 0.4以上）絞り込むことも可能
    sorted_results = sorted(results, key=lambda x: x['score'], reverse=True)

    return jsonify(sorted_results)

@app.route('/api/recipes/clear', strict_slashes=False)
def clear_cache():
    cache.clear()
    logger.info("ACTION: Cache cleared by manual request.")
    return jsonify({"status": "cleared"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 54321))
    logger.info(Config.STARTUP_MSG)
    app.run(host='0.0.0.0', port=port, debug=Config.DEBUG)
