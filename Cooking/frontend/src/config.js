// src/config.js

/**
 * Viteの環境変数 (import.meta.env) を安全に読み出すための司令塔
 */

// 1. 生の環境変数を取得（Viteのルールにより、VITE_で始まる変数のみ取得可能）
const rawApiUrl = import.meta.env.VITE_API_URL;

// 2. 現在のモード（development / production）をViteから取得
const mode = import.meta.env.MODE;

export const Config = {
  // 環境名
  ENV_NAME: mode,

  // 接続先バックエンドAPIのURL
  // 優先順位： 1.環境変数(VITE_API_URL)  2.開発用デフォルト
  API_BASE_URL: rawApiUrl || 'http://localhost:54321',

  // アプリ共通設定
  APP_TITLE: 'MyCooking',

  // デバッグ用：現在の設定がどこを見ているかコンソールに出すと開発が楽になります
  logStatus: () => {
    console.log(`[Config] Run Mode: ${mode}`);
    console.log(`[Config] API Endpoint: ${Config.API_BASE_URL}`);
  }
};
