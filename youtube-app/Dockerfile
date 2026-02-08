# 軽量なPythonイメージを使用
FROM python:3.10-slim

# OSのアップデートと必要なツールのインストール
RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# yt-dlpのインストール
RUN curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp \
    && chmod a+rx /usr/local/bin/yt-dlp

# 作業ディレクトリの設定
WORKDIR /app

# 依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードをコピー
COPY . .

# Renderが指定するポート（デフォルト10000）で起動
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]