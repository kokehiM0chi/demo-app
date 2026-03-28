import React, { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [recipes, setRecipes] = useState([]);
  const [loading, setLoading] = useState(true);

  // Python APIからデータを取得する関数
  const fetchRecipes = async () => {
    try {
      const response = await fetch('http://localhost:54321/api/recipes');
      const data = await response.json();
      setRecipes(data);
      setLoading(false);
    } catch (error) {
      console.error("APIの取得に失敗しました:", error);
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
