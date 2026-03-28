# 🍳 My Cooking Book (Recipe API & React Frontend)

Google スプレッドシートをデータソースとした、モダンなレシピ管理アプリです。
Backend は **Python (Flask)**、Frontend は **React (Vite)** で構成され、**uv** を使用してパッケージ管理を行っています。

## 🏗 システム構成

* **Backend**: Python 3.12+ / Flask (Port: `54321`)
* **Frontend**: React / Vite (Port: `5173`)
* **Data Source**: Google Sheets (CSV Export URL)
* **Infrastructure**: Render (Web Service & Static Site)

---

## 🚀 ローカルでの起動方法

リポジトリをクローンした後、以下の手順で Backend と Frontend をそれぞれ起動します。

### 1. Backend (Python API)

`uv` を使用して環境を構築し、サーバーを起動します。

```bash
# 依存関係のインストール
uv pip install -r requirements.txt

# サーバー起動
python app.py
```
* API Endpoint: `http://localhost:54321/api/recipes`

### 2. Frontend (React)

別ターミナルで `frontend` ディレクトリに移動して起動します。

```bash
cd frontend

# 初回のみインストール
npm install

# 開発サーバー起動
npm run dev
```

* Local URL: `http://localhost:5173`

---

## ☁️ デプロイ設定 (Render)

### Backend (Web Service)

* **Runtime**: `Python 3`
* **Build Command**: `pip install -r requirements.txt`
* **Start Command**: `gunicorn app:app`
* **Env Vars**: `PORT=10000`

### Frontend (Static Site)

* **Build Command**: `npm run build`
* **Publish Directory**: `frontend/dist`
* **Root Directory**: `frontend`

---

## 🛠 開発者向けメモ

### ポート番号について

macOS の AirPlay Receiver との競合を避けるため、バックエンドのポートは **`54321`** に固定しています。

### 依存関係の更新 (uv)

新しいライブラリを追加した場合は、必ず `requirements.txt` を更新してプッシュしてください。

```bash
uv pip compile pyproject.toml -o requirements.txt
```

---

## 📱 スマホでの利用

Render にデプロイ後、発行された URL を iPhone の Safari で開き、**「ホーム画面に追加」** することで、ネイティブアプリのように利用可能です。
