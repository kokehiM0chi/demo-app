import React, { useState, useEffect, useMemo, useCallback } from 'react'
import './App.css'
import { Config } from './config';

function App() {
  const CACHE_KEY = 'my_cooking_cache';

  // 初期値：キャッシュ読み込みを安全に
  const [recipes, setRecipes] = useState(() => {
    try {
      const saved = localStorage.getItem(CACHE_KEY);
      return saved ? JSON.parse(saved) : [];
    } catch { return []; }
  });

  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("すべて");

  // カテゴリ選択肢
  const categories = ["すべて", "肉", "魚", "野菜", "デザート", "主食"];

  // データ取得
  const fetchRecipes = useCallback(async (isSilent = false) => {
    try {
      if (recipes.length === 0 && !isSilent) setLoading(true);
      const API_URL = Config?.API_BASE_URL || "http://localhost:54321";

      const response = await fetch(`${API_URL}/api/recipes`);
      if (!response.ok) throw new Error("Server response was not ok");

      const data = await response.json();
      if (Array.isArray(data)) {
        setRecipes(data);
        localStorage.setItem(CACHE_KEY, JSON.stringify(data));
      }
    } catch (error) {
      console.error("API Fetch Error:", error);
    } finally {
      setLoading(false);
    }
  }, [recipes.length]);

  useEffect(() => {
    fetchRecipes();
  }, [fetchRecipes]);

  // フィルタリング（ヌルチェックを強化）
  const filteredRecipes = useMemo(() => {
    if (!Array.isArray(recipes)) return [];

    return recipes.filter(recipe => {
      if (!recipe) return false;

      // キー名はスプレッドシートの1行目に合わせる必要があります
      const rName = String(recipe["料理名"] || "");
      const rCat = String(recipe["カテゴリ"] || "");

      const categoryMatch = selectedCategory === "すべて" || rCat.includes(selectedCategory);
      const searchMatch = searchQuery === "" || rName.toLowerCase().includes(searchQuery.toLowerCase());

      return categoryMatch && searchMatch;
    });
  }, [recipes, searchQuery, selectedCategory]);

  return (
    <div className="container">
      <h1>🍳 My Cooking Book</h1>

      <div className="search-controls">
        <input
          type="text"
          placeholder="料理名で検索..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="search-input"
        />
        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          className="category-select"
        >
          {categories.map(cat => <option key={cat} value={cat}>{cat}</option>)}
        </select>
      </div>

      <div className="recipe-list">
        {loading && filteredRecipes.length === 0 ? (
          <p style={{textAlign: "center"}}>読み込み中...</p>
        ) : filteredRecipes.length > 0 ? (
          filteredRecipes.map((recipe, index) => (
            <details key={index} className="recipe-card">
              <summary className="recipe-title">
                {recipe["料理名"] || "名称未設定"}
                <span className="category">[{recipe["カテゴリ"] || "未分類"}]</span>
              </summary>
              <div className="recipe-content">
                <h4>■ 材料</h4>
                <pre>{recipe["材料"] || "データなし"}</pre>
                <h4>■ 工程</h4>
                <pre>{recipe["工程"] || "データなし"}</pre>
              </div>
            </details>
          ))
        ) : (
          <p style={{textAlign: "center", padding: "20px"}}>
            レシピが見つかりません。
          </p>
        )}
      </div>

      <button onClick={() => fetchRecipes(false)} className="refresh-button">
        最新の情報に更新
      </button>
    </div>
  )
}

export default App
