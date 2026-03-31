import React, { useState, useEffect } from 'react'
import './App.css'
import { Config } from './config'; // パスは環境に合わせて調整してください

function App() {
  const CACHE_KEY = 'my_cooking_cache'; // 保存庫の鍵の名前

  // 【変更1】初期値を「保存庫」から読み出す
  const [recipes, setRecipes] = useState(() => {
    const saved = localStorage.getItem(CACHE_KEY);
    return saved ? JSON.parse(saved) : [];
  });


  const [loading, setLoading] = useState(false);

  // Python APIからデータを取得する関数
  // isSilent が true の場合は画面に「読み込み中...」を出さない
  const fetchRecipes = async (isSilent = false) => {
    try {
      // レシピがまだ無い（初回）かつサイレント指定がない時だけローディングを表示
      if (recipes.length === 0 && !isSilent) {
        setLoading(true);
      }

      const API_URL = Config.API_BASE_URL;

      // 1. サーバーにリクエストを送る
      const response = await fetch(`${API_URL}/api/recipes`);

      // 2. レスポンスを JSON 形式として解析する
      const data = await response.json();

      // 【変更2】取得したデータを状態に保存し、同時に「保存庫」にも書き込む
      setRecipes(data);
      localStorage.setItem(CACHE_KEY, JSON.stringify(data));

    } catch (error) {
      console.error("APIの取得に失敗しました:", error);
    } finally {
      setLoading(false);
    }
  };

  // 「データを更新する」ボタンが押された時の処理
  const handleRefresh = async () => {
    try {
      // 画面全体を「読み込み中」にせず、裏側で処理を開始
      const API_URL = Config.API_BASE_URL;

      // 1. まずサーバー側のキャッシュを消す命令を送る
      await fetch(`${API_URL}/api/recipes/clear`);

      // 2. 最新データを取得し直す（サイレントモードをtrueにする）
      await fetchRecipes(true);

      alert("最新のデータを取得しました！");
    } catch (error) {
      console.error("更新に失敗しました:", error);
      alert("更新に失敗しました。");
    }
  };

  // コンポーネントがマウントされた時に実行
  useEffect(() => {
    fetchRecipes();
  }, []);

  return (
    <div className="container">
      <h1>🍳 My Cooking Book</h1>
      {/* 【変更3】データがある時は「同期中」を出さない、または控えめにする */}
      <p className="subtitle">
        {loading && recipes.length === 0 ? "スプレッドシートから同期中..." : "最新のレシピを表示中"}
      </p>
      {/* recipesが空、かつloading中の時（初回のみ）表示 */}
      {loading && recipes.length === 0 ? (
        <p>読み込み中...</p>
      ) : (
        <div className="recipe-list">
          {recipes.map((recipe, index) => (
            <details key={index} className="recipe-card">
              <summary className="recipe-title">
                {recipe.料理名} <span className="category">[{recipe.カテゴリ}]</span>
              </summary>
              <div className="recipe-content">
                <h4>■ 材料</h4>
                <pre>{recipe.材料}</pre>
                <h4>■ 工程</h4>
                <pre>{recipe.工程}</pre>
                {recipe['コツ・メモ'] && (
                  <div className="memo">
                    <strong>💡 コツ・メモ:</strong>
                    <p>{recipe['コツ・メモ']}</p>
                  </div>
                )}
              </div>
            </details>
          ))}
        </div>
      )}

      <button onClick={handleRefresh} className="refresh-button">
        最新の情報に更新
      </button>
    </div>
  )
}

export default App
