import json
import uvicorn
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from daniels_engine import DanielsFormulaEngine
from typing import List, Optional
from datetime import datetime
import pandas as pd

app = FastAPI()
JSON_PATH = Path("races.json")

# --- 以前の定数とテーマを完全復元 ---
PHASE_COLORS = {
    "Phase_I":   {"bg": "#f0f7ff", "text": "#0056b3", "label": "基礎構築"},
    "Phase_II":  {"bg": "#fff9f0", "text": "#9a6300", "label": "導入期"},
    "Phase_III": {"bg": "#fff5f5", "text": "#b91c1c", "label": "最大負荷"},
    "Phase_IV":  {"bg": "#faf5ff", "text": "#6b21a8", "label": "調整・レース"}
}

MENU_THEMES = {
    "E": {"color": "#1b4332", "bg": "#d8f3dc", "label": "E (Easy Run)"},
    "L": {"color": "#0077b6", "bg": "#caf0f8", "label": "L (Long Run)"},
    "Q": {"color": "#e67e22", "bg": "#fef5e7", "label": "Q (Quality Sessions)"}
}


# --- 設定更新用のデータモデル ---
class UserStats(BaseModel):
    monthly_mileage: int
    weekly_mileage: int
    base_distance: str
    base_time: str
    # last_updated は自動付与するため Optional
    last_updated: Optional[str] = None

# --- 共通ナビゲーション生成関数 ---
def get_nav_html(active_page: str):
    # メニュー項目の定義（ここを一箇所変えれば全部変わる！）
    menu_items = [
        {"id": "plan", "href": "/", "label": "🏃 プラン"},
        {"id": "races", "href": "/races", "label": "📅 レース日程"},
        {"id": "analysis", "href": "/analysis", "label": "📈 疲労度分析"}, # 追加
        {"id": "profile", "href": "/settings", "label": "👤 Running Profile"},
    ]

    links = []
    for item in menu_items:
        # アクティブなページかどうかの判定
        is_active = item["id"] == active_page

        # デザインの変数化
        color = "#2d3748" if is_active else "#718096"
        bg = "transparent"
        border_bottom = "none"

        if is_active:
            if item["id"] == "plan":
                bg, border_bottom = "#ebf8ff", "3px solid #3182ce"
            elif item["id"] == "races":
                bg, border_bottom = "#fff5f5", "3px solid #32CD32"
            elif item["id"] == "analysis":
                bg, border_bottom = "#fefcbf", "3px solid #ecc94b" # 黄色系
            elif item["id"] == "profile":
                bg, border_bottom = "#f0fff4", "3px solid #48bb78"

        style = f"""
            text-decoration: none;
            color: {color};
            font-weight: bold;
            padding: 8px 16px;
            background: {bg};
            border-bottom: {border_bottom};
            border-radius: 6px 6px 0 0;
            transition: 0.3s;
        """
        links.append(f'<a href="{item["href"]}" style="{style}">{item["label"]}</a>')

    return f"""
    <nav style="margin-bottom: 25px; display: flex; gap: 15px; border-bottom: 2px solid #edf2f7; padding-bottom: 15px;">
        {"".join(links)}
    </nav>
    """


# --- API: 設定の保存 ---
@app.post("/api/settings")
async def save_settings(stats: UserStats):
    engine = DanielsFormulaEngine()
    new_data = stats.dict()
    # 最終変更日付を自動入力
    new_data["last_updated"] = datetime.now().strftime("%Y-%m-%d")

    # ファイルに保存
    with open(engine.base_path / "data/user_stats.json", "w", encoding="utf-8") as f:
        json.dump(new_data, f, indent=4, ensure_ascii=False)

    return {"status": "ok", "last_updated": new_data["last_updated"]}

# --- 設定画面の表示 ---
@app.get("/settings", response_class=HTMLResponse)
async def view_settings():
    engine = DanielsFormulaEngine()
    stats = engine.stats

    nav_html = get_nav_html("profile") # 「profile」をアクティブにする

    return f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head><meta charset="UTF-8"><title>Settings</title></head>
    <body style="font-family: sans-serif; padding: 30px; background: #f4f7f6;">
        <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
            {nav_html}
            <h2 style="color: #2f855a; margin-top: 0;">ユーザー設定の編集</h2>
            <p style="font-size: 0.85em; color: #666;">最終更新日: <span id="display-last-updated">{stats.get('last_updated', '未設定')}</span></p>

            <div style="display: flex; flex-direction: column; gap: 15px; margin-top: 20px;">
                <label>
                    <span style="display:block; font-weight:bold; margin-bottom:5px;">月間走行距離 (km)</span>
                    <input type="number" id="monthly_mileage" value="{stats['monthly_mileage']}" style="width:100%; padding:10px; border:1px solid #ddd; border-radius:6px;">
                </label>
                <label>
                    <span style="display:block; font-weight:bold; margin-bottom:5px;">週間走行距離 (km)</span>
                    <input type="number" id="weekly_mileage" value="{stats['weekly_mileage']}" style="width:100%; padding:10px; border:1px solid #ddd; border-radius:6px;">
                </label>
                <label>
                    <span style="display:block; font-weight:bold; margin-bottom:5px;">基準距離 (VDOT用)</span>
                    <select id="base_distance" style="width:100%; padding:10px; border:1px solid #ddd; border-radius:6px;">
                        <option value="1.5km" {"selected" if stats['base_distance'] == "1.5km" else ""}>1.5km</option>
                        <option value="5km" {"selected" if stats['base_distance'] == "5km" else ""}>5km</option>
                        <option value="10km" {"selected" if stats['base_distance'] == "10km" else ""}>10km</option>
                    </select>
                </label>
                <label>
                    <span style="display:block; font-weight:bold; margin-bottom:5px;">基準タイム (hh:mm:ss または mm:ss)</span>
                    <input type="text" id="base_time" value="{stats['base_time']}" placeholder="22:15" style="width:100%; padding:10px; border:1px solid #ddd; border-radius:6px;">
                </label>

                <button onclick="saveSettings()" style="margin-top:10px; padding:15px; background:#48bb78; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:bold; font-size:1em;">
                    設定を保存して再計算
                </button>
            </div>
        </div>

        <script>
            async function saveSettings() {{
                const data = {{
                    monthly_mileage: parseInt(document.getElementById('monthly_mileage').value),
                    weekly_mileage: parseInt(document.getElementById('weekly_mileage').value),
                    base_distance: document.getElementById('base_distance').value,
                    base_time: document.getElementById('base_time').value
                }};

                const res = await fetch('/api/settings', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(data)
                }});

                if (res.ok) {{
                    const result = await res.json();
                    alert('設定を保存しました。プランを再計算します。');
                    location.href = "/"; // トップに戻って再計算されたプランを確認
                }} else {{
                    alert('保存に失敗しました。タイムの形式などを確認してください。');
                }}
            }}
        </script>
    </body>
    </html>
    """

import json
import pandas as pd
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/analysis", response_class=HTMLResponse)
async def view_analysis():
    csv_path = Path("data/Activities_2026-03-01-now.csv")
    if not csv_path.exists(): return "CSV not found"

    # CSV読み込み（'メモ'列があることを想定。なければ空文字で作成）
    df = pd.read_csv(csv_path)
    if 'メモ' not in df.columns:
        df['メモ'] = ""

    df['日付'] = pd.to_datetime(df['日付'])
    df = df.sort_values('日付')

    # --- データ処理 ---
    df['距離_km'] = pd.to_numeric(df['距離'], errors='coerce').fillna(0)

    def get_pace_seconds(row):
        try:
            t_str = str(row['タイム']).strip().lower()
            if not t_str or t_str in ['nan', 'none', '0', '0:00']: return None
            parts = t_str.split(':')
            if len(parts) == 3: sec = int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
            elif len(parts) == 2: sec = int(parts[0])*60 + int(parts[1])
            else: sec = int(float(parts[0]))
            return sec / float(row['距離']) if float(row['距離']) > 0 else None
        except: return None

    df['pace_sec'] = df.apply(get_pace_seconds, axis=1)
    df['pace_min_float'] = df['pace_sec'] / 60

    # 体感負荷補正
    def calculate_perceived_tss(row):
        dist = row['距離_km']
        if dist <= 0: return 0
        p_sec = row['pace_sec'] if row['pace_sec'] else 360
        weight = 1.8 if row['日付'] <= pd.Timestamp('2026-03-25') else (1.2 if row['日付'] <= pd.Timestamp('2026-04-10') else 0.8)
        return (dist * (360 / p_sec)) * weight * 5

    df['TSS'] = df.apply(calculate_perceived_tss, axis=1)
    df['ATL'] = df['TSS'].rolling(window=7, min_periods=1).mean()
    df['CTL'] = df['TSS'].rolling(window=42, min_periods=1).mean()
    df['TSB'] = df['CTL'] - df['ATL']

    # --- JS用データ変換 ---
    labels = df['日付'].dt.strftime('%m/%d').tolist()
    distance_data = df['距離_km'].tolist()
    pace_data = [round(m, 2) if (pd.notnull(m) and m > 0) else None for m in df['pace_min_float'].tolist()]
    atl_data = df['ATL'].round(1).tolist()
    tsb_data = df['TSB'].round(1).tolist()
    memo_data = df['メモ'].fillna("").tolist() # メモ列をリスト化

    return f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <title>Fatigue Analysis with Notes</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body {{ font-family: sans-serif; padding: 30px; background: #f4f7f6; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); position: relative; }}
                /* モーダル（編集画面）のスタイル */
                #editModal {{
                    display: none; position: fixed; z-index: 100; left: 0; top: 0; width: 100%; height: 100%;
                    background-color: rgba(0,0,0,0.4);
                }}
                .modal-content {{
                    background-color: white; margin: 10% auto; padding: 20px; border-radius: 12px; width: 400px;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.3);
                }}
                textarea {{ width: 100%; height: 100px; margin-top: 10px; padding: 10px; border: 1px solid #ddd; border-radius: 8px; }}
                .btn-group {{ margin-top: 15px; text-align: right; }}
                .save-btn {{ background: #3182ce; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2 style="color: #b7791f;">トレーニング分析 & デイリーメモ</h2>
                <div style="height: 500px;"><canvas id="fatigueChart"></canvas></div>

                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; margin-top: 20px;">
                    <div style="padding: 15px; border-radius: 8px; border-top: 4px solid #3182ce; background: #f8fafc;">
                        <h4 style="margin:0 0 8px 0; color: #3182ce;">ATL (短期疲労)</h4>
                        <p style="font-size: 0.85em; color: #4a5568; margin:0;">直近7日間の負荷。</p>
                    </div>
                    <div style="padding: 15px; border-radius: 8px; border-top: 4px solid #32CD32; background: #f8fafc;">
                        <h4 style="margin:0 0 8px 0; color: #32CD32;">TSB (コンディション)</h4>
                        <p style="font-size: 0.85em; color: #4a5568; margin:0;">余力。グラフの点をクリックするとメモを編集できます。</p>
                    </div>
                    <div style="padding: 15px; border-radius: 8px; border-top: 4px solid #e53e3e; background: #f8fafc;">
                        <h4 style="margin:0 0 8px 0; color: #e53e3e;">平均ペース</h4>
                        <p style="font-size: 0.85em; color: #4a5568; margin:0;">▲をホバーするとメモが表示されます。</p>
                    </div>
                </div>
            </div>

            <div id="editModal">
                <div class="modal-content">
                    <h3 id="modalDate" style="margin-top:0;"></h3>
                    <p style="font-size: 0.9em; color: #666;">この日の振り返り・反省点:</p>
                    <textarea id="memoInput"></textarea>
                    <div class="btn-group">
                        <button onclick="closeModal()" style="background: #eee; border:none; padding:8px 12px; border-radius:6px; margin-right:8px;">キャンセル</button>
                        <button class="save-btn" onclick="saveMemo()">保存</button>
                    </div>
                </div>
            </div>

            <script>
                const labels = {json.dumps(labels)};
                const memos = {json.dumps(memo_data)};
                let currentEditIndex = null;

                const ctx = document.getElementById('fatigueChart').getContext('2d');
                const chart = new Chart(ctx, {{
                    type: 'line',
                    data: {{
                        labels: labels,
                        datasets: [
                            {{
                                label: '平均ペース (min/km)',
                                data: {json.dumps(pace_data)},
                                borderColor: '#e53e3e',
                                backgroundColor: '#e53e3e',
                                type: 'line', showLine: false, pointStyle: 'triangle', pointRadius: 9,
                                yAxisID: 'y_pace', order: 1
                            }},
                            {{
                                label: 'ATL (短期疲労)',
                                data: {json.dumps(atl_data)},
                                borderColor: '#3182ce', borderWidth: 2, fill: false, tension: 0.3,
                                yAxisID: 'y_score', order: 2
                            }},
                            {{
                                label: 'TSB (コンディション)',
                                data: {json.dumps(tsb_data)},
                                borderColor: '#32CD32', borderDash: [5, 5], fill: false,
                                yAxisID: 'y_score', order: 3
                            }},
                            {{
                                label: '走行距離 (km)',
                                data: {json.dumps(distance_data)},
                                backgroundColor: 'rgba(54, 162, 235, 0.12)',
                                type: 'bar', yAxisID: 'y_dist', order: 4
                            }}
                        ]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        onClick: (e, elements) => {{
                            if (elements.length > 0) {{
                                const index = elements[0].index;
                                openModal(index);
                            }}
                        }},
                        scales: {{
                            y_score: {{ type: 'linear', position: 'left', title: {{ display: true, text: 'スコア' }} }},
                            y_pace: {{
                                type: 'linear', position: 'left', reverse: true, min: 4, max: 10,
                                title: {{ display: true, text: 'ペース' }},
                                grid: {{ drawOnChartArea: false }},
                                ticks: {{ callback: v => {{ let m=Math.floor(v), s=Math.round((v-m)*60); return m+":"+(s<10?"0":"")+s; }} }}
                            }},
                            y_dist: {{ type: 'linear', position: 'right', beginAtZero: true, grid: {{ drawOnChartArea: false }} }}
                        }},
                        plugins: {{
                            tooltip: {{
                                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                                padding: 12,
                                bodyFont: {{ size: 14 }},
                                callbacks: {{
                                    afterBody: function(items) {{
                                        const index = items[0].dataIndex;
                                        const memo = memos[index];
                                        return memo ? '\\n【メモ】\\n' + memo : '';
                                    }},
                                    label: function(context) {{
                                        let label = context.dataset.label || '';
                                        if (label.includes('ペース')) {{
                                            let v = context.parsed.y;
                                            let m=Math.floor(v), s=Math.round((v-m)*60);
                                            return label + ': ' + m + '分' + (s<10?'0':'') + s + '秒/km';
                                        }}
                                        return label + ': ' + context.parsed.y;
                                    }}
                                }}
                            }}
                        }}
                    }}
                }});

                function openModal(index) {{
                    currentEditIndex = index;
                    document.getElementById('modalDate').innerText = labels[index] + " の振り返り";
                    document.getElementById('memoInput').value = memos[index];
                    document.getElementById('editModal').style.display = 'block';
                }}

                function closeModal() {{
                    document.getElementById('editModal').style.display = 'none';
                }}

                async function saveMemo() {{
                    const newMemo = document.getElementById('memoInput').value;
                    const date = labels[currentEditIndex];

                    // ここでサーバー側のAPIを叩く
                    // 今回はフロント側のみの反映例
                    memos[currentEditIndex] = newMemo;
                    chart.update();
                    closeModal();

                    // 実際には以下のようなAPI呼び出しが必要です
                    // await fetch('/api/save_memo', {{
                    //     method: 'POST',
                    //     body: JSON.stringify({{ date, memo: newMemo }})
                    // }});
                }}
            </script>
        </body>
        </html>
    """


class RaceEntry(BaseModel):
    date: str
    name: str

def load_races() -> List[dict]:
    if not JSON_PATH.exists(): return []
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            # --- 重要：古いデータ（idがない）にIDを動的に付与してエラーを回避 ---
            updated = False
            for i, r in enumerate(data):
                if "id" not in r:
                    r["id"] = i
                    updated = True
            if updated:
                save_races(data) # 形式を整えて保存し直す
            return data
        except (json.JSONDecodeError, TypeError):
            return []

def save_races(races):
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(races, f, indent=4, ensure_ascii=False)



# データモデルにIDを追加
class RaceEntry(BaseModel):
    id: Optional[int] = None
    date: str
    name: str
    url: str = ""

# --- API ---
@app.post("/api/races")
async def upsert_race(race: RaceEntry):
    races = load_races()
    # IDを確実に数値として扱う（JSからの文字列化対策）
    target_id = int(race.id) if race.id is not None else None

    if target_id is not None:
        # 【更新モード】
        found = False
        for r in races:
            if r.get("id") == target_id:
                r.update({"date": race.date, "name": race.name, "url": race.url})
                found = True
                break
        # もしID指定で更新対象が見つからなかった場合は新規として扱う（安全策）
        if not found:
            target_id = None

    if target_id is None:
        # 【新規登録モード】
        new_id = max([r.get("id", -1) for r in races] + [-1]) + 1
        races.append({
            "id": new_id,
            "date": race.date,
            "name": race.name,
            "url": race.url,
            "status": "エントリー済",
            "source": "Web UI"
        })

    save_races(races)
    return {"status": "ok"}


@app.delete("/api/races/{race_id}")
async def delete_race(race_id: int):
    races = load_races()
    races = [r for r in races if r.get("id") != race_id]
    save_races(races)
    return {"status": "ok"}


# --- 1. トレーニングプラン画面 (以前のリッチなレイアウトを復元) ---
@app.get("/", response_class=HTMLResponse)
async def view_training_plan():
    engine = DanielsFormulaEngine()
    plan, paces, details_db = engine.generate_plan(24)
    stats = engine.stats

    nav_html = get_nav_html("plan")  # 「plan」をアクティブにする

    pace_html = f"""
    <div style="display: flex; gap: 10px; margin-bottom: 20px;">
        <div style="flex:1; background:#2c3e50; color:white; padding:12px; border-radius:8px; text-align:center;">
            <strong style="font-size:0.75em; opacity:0.8;">T Pace (閾値)</strong><br>
            <span style="font-size:1.1em;">{paces['T']}</span><span style="font-size:0.8em;"> /km</span>
        </div>
        <div style="flex:1; background:#2c3e50; color:white; padding:12px; border-radius:8px; text-align:center;">
            <strong style="font-size:0.75em; opacity:0.8;">I Pace (インターバル)</strong><br>
            <span style="font-size:1.1em;">{paces['I']}</span><span style="font-size:0.8em;"> /km</span>
        </div>
        <div style="flex:1; background:#2c3e50; color:white; padding:12px; border-radius:8px; text-align:center;">
            <strong style="font-size:0.75em; opacity:0.8;">R (400m / 200m)</strong><br>
            <span style="font-size:1.1em;">{paces['R_400']}</span> / <span style="font-size:1.1em;">{paces['R_200']}</span>
        </div>
        <div style="flex:1; background:#ffffff; color:{MENU_THEMES['E']['color']}; padding:12px; border-radius:8px; text-align:center; border: 2px solid {MENU_THEMES['E']['color']};">
            <strong style="font-size:0.75em; opacity:0.8;">E Pace Guide (Upper)</strong><br>
            <span style="font-size:1.1em; font-weight:bold;">{paces['E_limit']}</span><span style="font-size:0.8em;"> /km</span>
        </div>
    </div>
    """

    rows = ""
    for w in plan:
        q_html = "".join([f"<div style='margin-bottom:3px;'>・<a href='#{m['id']}' style='color:inherit; font-weight:bold;'>{m['summary']}</a></div>" for m in w['menus']])
        sched_html = "".join([f"<div style='margin-bottom:3px;'>- {d}</div>" for d in w['weekly_schedule']])
        p_style = PHASE_COLORS.get(w['phase'])
        rows += f"""
        <tr style="background:{p_style['bg']};">
            <td style="padding:15px; border:1px solid #ddd; text-align:center; font-weight:bold;">{w['week']}</td>
            <td style="padding:15px; border:1px solid #ddd;">
                <span style="background:{p_style['text']}; color:white; padding:3px 8px; border-radius:12px; font-size:0.8em; font-weight:bold; display:block; text-align:center; margin-bottom:4px;">{w['phase']}</span>
                <div style="text-align:center; font-size:0.75em; color:{p_style['text']}; font-weight:bold;">{p_style['label']}</div>
            </td>
            <td style="padding:15px; border:1px solid #ddd; font-size:0.85em; color:#444;">{w['focus']}</td>
            <td style="padding:15px; border:1px solid #ddd;">
                <div style="margin-bottom:10px; border-bottom:1px dashed rgba(0,0,0,0.1); padding-bottom:8px;">
                    <span style="background:{MENU_THEMES['L']['bg']}; color:{MENU_THEMES['L']['color']}; padding:2px 6px; border-radius:4px; font-size:0.75em; font-weight:bold; margin-right:8px; border:1px solid {MENU_THEMES['L']['color']};">L</span>
                    <strong style="color:#2c3e50;">最大 {w['l_run_max']} km</strong>
                </div>
                <div>
                    <span style="background:{MENU_THEMES['Q']['bg']}; color:{MENU_THEMES['Q']['color']}; padding:2px 6px; border-radius:4px; font-size:0.75em; font-weight:bold; margin-right:8px; border:1px solid {MENU_THEMES['Q']['color']};">Q</span>
                    <div style="margin-top:5px; padding-left:5px; color:{MENU_THEMES['Q']['color']}; font-size:0.95em; font-weight:bold;">{q_html if w['menus'] else 'E-Runのみ'}</div>
                </div>
                <div style="margin-top:10px; border-top:1px dashed rgba(0,0,0,0.1); padding-top:8px;">{sched_html}</div>
            </td>
        </tr>"""

    detail_html = "".join([f"""
    <div id="{qid}" style="margin-bottom:15px; padding:15px; border-radius:8px; background:#fff; border-left:6px solid {MENU_THEMES['Q']['color']}; box-shadow:0 2px 4px rgba(0,0,0,0.05);">
        <h4 style="margin:0 0 10px 0; color:#2c3e50;">{qid}: {d['type']}</h4>
        <div style="font-size:0.9em; display:grid; grid-template-columns: 100px 1fr; gap:5px;">
            <strong>メニュー:</strong> <span>{d['sets']}</span>
            <strong>ペース:</strong> <span style="color:#b91c1c; font-weight:bold;">{d['pace']}</span>
            <strong>休息:</strong> <span>{d['rest']}</span>
            <strong>備考:</strong> <span style="font-style:italic; color:#666;">{d['note']}</span>
        </div>
    </div>""" for qid, d in details_db.items()])

    # 2. 【ダニエルズ理論に基づく5つの強度解説】
    # 変数名を intensity_summary_html に統一し、クォートのミスを修正
    intensity_summary_html = """
    <div style="display: flex; gap: 8px; margin-bottom: 25px; font-size: 0.72em; line-height: 1.3;">
        <div style="flex:1; padding:10px; background:#d8f3dc; border-radius:6px; border-top:3px solid #1b4332; color:#1b4332;">
            <strong>E (Easy)</strong><br>心筋の発達・毛細血管の増加・怪我への耐性構築。
        </div>
        <div style="flex:1; padding:10px; background:#ebf8ff; border-radius:6px; border-top:3px solid #3182ce; color:#2c5282;">
            <strong>M (Marathon)</strong><br>マラソン特有の生理的適応。目標ペースでの脚作りとエネルギー消費効率の確認。
        </div>
        <div style="flex:1; padding:10px; background:#fff9f0; border-radius:6px; border-top:3px solid #9a6300; color:#9a6300;">
            <strong>T (Threshold)</strong><br>乳酸閾値の向上。血中の乳酸を再利用・除去する能力を高める。
        </div>
        <div style="flex:1; padding:10px; background:#fff5f5; border-radius:6px; border-top:3px solid #b91c1c; color:#b91c1c;">
            <strong>I (Interval)</strong><br>VO2maxの向上。有酸素能力の限界値を引き上げる。
        </div>
        <div style="flex:1; padding:10px; background:#faf5ff; border-radius:6px; border-top:3px solid #6b21a8; color:#6b21a8;">
            <strong>R (Repetition)</strong><br>無酸素性作業能とランニング効率（経済性）の向上。
        </div>
    </div>
    """

    return f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head><meta charset="UTF-8"><title>Marathon Training Dashboard</title></head>
    <body style="font-family:'Helvetica Neue', Arial, sans-serif; padding:30px; background:#f4f7f6; color:#333;">
        <div style="max-width:1000px; margin:0 auto; background:white; padding:25px; border-radius:12px; box-shadow:0 4px 15px rgba(0,0,0,0.1);">
            {nav_html} {pace_html} {intensity_summary_html}
            <div style="background:#34495e; color:white; padding:15px; border-radius:8px 8px 0 0; display:flex; justify-content:space-between; align-items:center;">
                <h2 style="margin:0; font-size:1.4em;">Daniels 24-Week Plan (VDOT: {plan[0]['vdot']})</h2>
                <div style="font-size:0.8em; background:rgba(255,255,255,0.1); padding:5px 10px; border-radius:4px;">Weekly Mileage: {stats['weekly_mileage']}km</div>
            </div>
            <table style="border-collapse:collapse; width:100%; border: 1px solid #ddd;">
                <thead><tr style="background:#f2f2f2;">
                    <th style="width:8%; padding:12px; border:1px solid #ddd;">週</th>
                    <th style="width:15%; padding:12px; border:1px solid #ddd;">フェーズ</th>
                    <th style="width:20%; padding:12px; border:1px solid #ddd;">今週の目的</th>
                    <th style="width:57%; padding:12px; border:1px solid #ddd;">トレーニング構成 (L / Q)</th>
                </tr></thead>
                <tbody>{rows}</tbody>
            </table>
            <h3 style="margin-top:40px; border-bottom:2px solid #34495e; padding-bottom:10px;">Qセッション詳細</h3>
            {detail_html}
        </div>
    </body>
    </html>
    """

# --- 2. レース日程画面 (API連携あり) ---
# --- 2. レース日程画面 (URL対応版) ---
# --- 2. レース日程画面 (編集・削除・日時対応版) ---
@app.get("/races", response_class=HTMLResponse)
async def view_race_schedule():
    races = load_races()
    # 日付順にソート
    races.sort(key=lambda x: x['date'])

    nav_html = get_nav_html("races") # 「races」をアクティブにする

    race_rows = ""
    for r in races:
        display_name = f'<a href="{r.get("url")}" target="_blank" style="color: #3182ce; text-decoration: none; font-weight: bold;">{r["name"]} 🔗</a>' if r.get("url") else r["name"]
        race_rows += f"""
        <tr style="border-bottom: 1px solid #eee;">
            <td style="padding: 12px;">{r['date']}</td>
            <td style="padding: 12px;">{display_name}</td>
            <td style="padding: 12px; text-align: right;">
                <button onclick='editRace({json.dumps(r)})' style="padding: 4px 8px; font-size: 0.8em; cursor:pointer;">編集</button>
                <button onclick='deleteRace({r["id"]})' style="padding: 4px 8px; font-size: 0.8em; color: red; cursor:pointer;">削除</button>
            </td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Race Manager</title></head>
    <body style="font-family: sans-serif; padding: 30px; background: #f4f7f6;">
        <div style="max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.05);">
            {nav_html}
            <div id="form-container" style="background: #fdf2f2; padding: 20px; border-radius: 12px; border: 1px solid #feb2b2; margin-bottom: 30px;">
                <h3 id="form-title" style="margin-top:0; color:#c53030;">新規レース登録</h3>
                <input type="hidden" id="race-id">
                <div style="display: grid; grid-template-columns: 2fr 1.5fr 2fr auto; gap: 10px; margin-bottom:10px;">
                    <input type="text" id="name" placeholder="大会名" style="padding:10px; border:1px solid #ddd; border-radius:6px;">
                    <input type="text" id="date" placeholder="2026/05/02 10:30" style="padding:10px; border:1px solid #ddd; border-radius:6px;">
                    <input type="text" id="url" placeholder="エントリーURL" style="padding:10px; border:1px solid #ddd; border-radius:6px;">
                    <button id="save-btn" onclick="saveRace()" style="padding:10px 20px; background:#32CD32; color:white; border:none; border-radius:6px; cursor:pointer; font-weight:bold;">保存</button>
                </div>
                <button id="cancel-btn" onclick="resetForm()" style="display:none; font-size:0.8em;">キャンセル</button>
            </div>
            <table style="width: 100%; border-collapse: collapse;">
                <thead style="background: #f8fafc; text-align: left;">
                    <tr><th style="padding: 12px;">日時</th><th style="padding: 12px;">大会名</th><th style="padding: 12px; text-align: right;">アクション</th></tr>
                </thead>
                <tbody>{race_rows if race_rows else '<tr><td colspan="3" style="text-align:center; padding:20px;">予定はありません</td></tr>'}</tbody>
            </table>
        </div>
        <script>
            async function saveRace() {{
                const id = document.getElementById('race-id').value;
                const name = document.getElementById('name').value;
                const date = document.getElementById('date').value;
                const url = document.getElementById('url').value;
                if(!name || !date) return alert('入力してください');

                await fetch('/api/races', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ id: id ? parseInt(id) : null, name, date, url }})
                }});
                location.reload();
            }}

            async function deleteRace(id) {{
                if(!confirm('本当に削除しますか？')) return;
                await fetch(`/api/races/${{id}}`, {{ method: 'DELETE' }});
                location.reload();
            }}

            function editRace(race) {{
                document.getElementById('form-title').innerText = "レース情報を編集";
                document.getElementById('race-id').value = race.id;
                document.getElementById('name').value = race.name;
                document.getElementById('date').value = race.date;
                document.getElementById('url').value = race.url || '';
                document.getElementById('save-btn').innerText = "更新する";
                document.getElementById('cancel-btn').style.display = "inline";
                window.scrollTo(0, 0);
            }}

            function resetForm() {{
                document.getElementById('form-title').innerText = "新規レース登録";
                document.getElementById('race-id').value = '';
                document.getElementById('name').value = '';
                document.getElementById('date').value = '';
                document.getElementById('url').value = '';
                document.getElementById('save-btn').innerText = "保存";
                document.getElementById('cancel-btn').style.display = "none";
            }}
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
