import React, { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [recipes, setRecipes] = useState([]);
  const [loading, setLoading] = useState(true);

  // Python APIからデータを取得する関数
  const fetchRecipes = async () => {
    try {
      setLoading(true); // 再取得する場合のために明示的にセット

      const API_URL = "https://recipe-api-gotu.onrender.com";

      // 1. サーバーにリクエストを送る
      const response = await fetch(`${API_URL}/api/recipes`);

      // 2. レスポンスを JSON 形式として解析する
      const data = await response.json();

      // 3. 取得したデータを状態（State）に保存する
      setRecipes(data);

    } catch (error) {
      console.error("APIの取得に失敗しました:", error);
    } finally {
      // 成功しても失敗してもローディングを終了する
      setLoading(false);
    }
  };
  
  // コンポーネントがマウントされた時に実行
  useEffect(() => {
    fetchRecipes();
  }, []);

  return (
    <div className="container">
      <h1>🍳 My Cooking Book</h1>
      <p className="subtitle">スプレッドシートから同期中</p>

      {loading ? (
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

      <button onClick={fetchRecipes} className="refresh-button">
        データを更新する
      </button>
    </div>
  )
}

export default App
