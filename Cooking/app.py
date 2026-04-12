import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import logging
import sys
from cachetools import TTLCache
from config import Config
from sentence_transformers import SentenceTransformer, util
import torch

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": Config.FRONTEND_URL}})

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# モデルの初期化（関数外で行う）
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

cache = TTLCache(maxsize=1, ttl=Config.CACHE_TTL)

# あなたが決めた正しいカラムリスト
COLUMN_NAMES = ["料理名", "カテゴリ", "材料", "工程", "コツ", "作成者", "コンテキスト", "URL", "Video_ID"]

@app.route('/api/recipes', strict_slashes=False)
def get_recipes():
    try:
        if "recipe_data" in cache:
            all_recipes = cache["recipe_data"]
        else:
            # CSV読み込み時にカラム名を指定・制限する
            df = pd.read_csv(Config.CSV_URL)

            # もしCSVの列名がズレている場合、ここで強制的にリネームするか
            # あるいは期待する列だけを抽出して欠損を補完します
            for col in COLUMN_NAMES:
                if col not in df.columns:
                    df[col] = "" # 足りない列は空で作成

            # 指定した順番の列だけを抽出（これでズレを防止）
            df = df[COLUMN_NAMES]

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

    if not all_recipes:
        return jsonify([])

    # 検索用テキストの作成（コツも含めるように修正）
    recipe_texts = [
        f"[{r.get('カテゴリ', '')}] {r.get('料理名', '')} {r.get('コツ', '')} {r.get('コンテキスト', '')} {r.get('材料', '')}"
        for r in all_recipes
    ]

    recipe_embeddings = model.encode(recipe_texts, convert_to_tensor=True)
    search_target = f"{category} {query}".strip()
    search_embedding = model.encode(search_target, convert_to_tensor=True)

    cosine_scores = util.cos_sim(search_embedding, recipe_embeddings)[0]

    results = []
    for i, r in enumerate(all_recipes):
        r_with_score = r.copy()
        r_with_score['score'] = float(cosine_scores[i])
        results.append(r_with_score)

    sorted_results = sorted(results, key=lambda x: x['score'], reverse=True)
    return jsonify(sorted_results)

@app.route('/api/recipes/clear', strict_slashes=False)
def clear_cache():
    cache.clear()
    return jsonify({"status": "cleared"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 54321))
    app.run(host='0.0.0.0', port=port, debug=Config.DEBUG)
