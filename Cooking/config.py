import os
from dotenv import load_dotenv

# プロジェクトルートの .env ファイルを読み込む（ローカル開発用）
# Render環境ではファイルがなくても無視されるので安全です
load_dotenv()

class Config:
    # --- 1. 環境判別 ---
    # Render環境は 'RENDER' 変数が 'true' になる特性を利用
    IS_RENDER = os.environ.get("RENDER") == "true"
    ENV_NAME = "production" if IS_RENDER else "development"

    # --- 2. 共通設定（GitHubに載ってもOK） ---
    CSV_URL = os.environ.get("CSV_URL", "")
    CACHE_TTL = 43200  # 12時間

    # --- 3. 環境変数を優先する設定（本番URLはここから読み出す） ---
    # os.environ.get("変数名", "デフォルト値") の形式で書くのが堅牢さのコツです

    # フロントエンドのURL (CORS許可に使用)
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

    # バックエンドの自画自賛用URL (必要なら)
    BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:54321")

    # --- 4. モードによる挙動の切り替え ---
    DEBUG = not IS_RENDER

    # ログ出力用の文字列
    STARTUP_MSG = f"========== SERVER STARTING ({ENV_NAME} mode) =========="
    logger_level = "INFO"
