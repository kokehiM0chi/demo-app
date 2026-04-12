import React, { useState, useEffect, useMemo, useCallback } from 'react'
import './App.css'
import { Config } from './config';

function App() {
  const CACHE_KEY = 'my_cooking_cache';

  const [recipes, setRecipes] = useState(() => {
    try {
      const saved = localStorage.getItem(CACHE_KEY);
      return saved ? JSON.parse(saved) : [];
    } catch { return []; }
  });

  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("すべて");

  const categories = ["すべて", "ヘルシー", "肉", "魚", "野菜", "スイーツ", "主食"];

  const fetchRecipes = useCallback(async (isSilent = false) => {
    try {
      if (recipes.length === 0 && !isSilent) setLoading(true);
      const API_URL = Config?.API_BASE_URL || "http://localhost:54321";

      const response = await fetch(`${API_URL}/api/recipes`);
      if (!response.ok) throw new Error("Server response was not ok");

      const data = await response.json();
      if (Array.isArray(data)) {
        // --- データのズレを補正し、空文字を null 化する処理 ---
        const cleanedData = data.map(r => ({
          ...r,
          "作成者": (r["作成者"] && r["作成者"].length > 10) ? null : r["作成者"], // 10文字以上の長い文は作成者ではないと判断
          "コンテキスト": r["コンテキスト"] || (r["作成者"] && r["作成者"].length > 10 ? r["作成者"] : null)
        }));

        setRecipes(cleanedData);
        localStorage.setItem(CACHE_KEY, JSON.stringify(cleanedData));
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

  const filteredRecipes = useMemo(() => {
    if (!recipes) return [];
    return recipes.filter(recipe => {
      const rCat = recipe["カテゴリ"] || "";
      const rName = recipe["料理名"] || "";
      let categoryMatch = selectedCategory === "すべて" || rCat.includes(selectedCategory);
      if (selectedCategory === "スイーツ") {
        const targets = ["スイーツ", "デザート", "焼き菓子", "お菓子"];
        categoryMatch = targets.some(target => rCat.includes(target));
      }
      const searchMatch = searchQuery === "" || rName.toLowerCase().includes(searchQuery.toLowerCase());
      return categoryMatch && searchMatch;
    });
  }, [recipes, searchQuery, selectedCategory]);

return (
    <div className="container">
      <h1>My Cooking Book</h1>

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
                <span className="recipe-name">{recipe["料理名"] || "名称未設定"}</span>
                {recipe["カテゴリ"] && (
                  <span className="category">[{recipe["カテゴリ"]}]</span>
                )}
              </summary>

              <div className="recipe-content">
                {/* 1. 動画 (Video_ID) */}
                {recipe["Video_ID"] && (
                  <div className="thumbnail-container">
                    <a href={recipe["URL"]} target="_blank" rel="noopener noreferrer">
                      <img
                        src={`https://img.youtube.com/vi/${recipe["Video_ID"]}/mqdefault.jpg`}
                        alt={recipe["料理名"]}
                        className="recipe-thumbnail"
                        loading="lazy"
                      />
                      <div className="play-overlay">▶ 動画を再生</div>
                    </a>
                  </div>
                )}

                {/* 2. 材料と工程 */}
                {(recipe["材料"] || recipe["工程"]) && (
                  <div className="recipe-details-grid">
                    {recipe["材料"] && (
                      <div className="details-section">
                        <h4>■ 材料</h4>
                        <pre>{recipe["材料"]}</pre>
                      </div>
                    )}
                    {recipe["工程"] && (
                      <div className="details-section">
                        <h4>■ 工程</h4>
                        <pre>{recipe["工程"]}</pre>
                      </div>
                    )}
                  </div>
                )}

                {/* 3. コツ (🍀 はここだけに使用) */}
                {recipe["コツ"] && recipe["コツ"].trim() !== "" && (
                  <div className="context-box tips-area">
                    <strong>🍀 コツ:</strong>
                    <p><em>{recipe["コツ"]}</em></p>
                  </div>
                )}

                {/* 4. 作成者 (👩‍🍳 はここだけに使用) */}
                {recipe["作成者"] && recipe["作成者"].trim() !== "" && (
                  <div className="creator-tag">
                    👩‍🍳 <strong>作成者:</strong> {recipe["作成者"]}
                  </div>
                )}

                {/* 5. コンテキスト (背景・紹介文) */}
                {recipe["コンテキスト"] && recipe["コンテキスト"].trim() !== "" && (
                  <div className="context-box info-area">
                    <strong>コンテキスト:</strong>
                    <p>{recipe["コンテキスト"]}</p>
                  </div>
                )}
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
