import json
import uvicorn
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from daniels_engine import DanielsFormulaEngine

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

class RaceEntry(BaseModel):
    date: str
    name: str

def load_races():
    if not JSON_PATH.exists(): return []
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        try: return json.load(f)
        except: return []

def save_races(races):
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(races, f, indent=4, ensure_ascii=False)

# --- API ---
@app.post("/api/races")
async def add_race(race: RaceEntry):
    races = load_races()
    races.append({"date": race.date, "name": race.name, "status": "エントリー済", "source": "Web UI"})
    save_races(races)
    return {"status": "ok"}

# --- 1. トレーニングプラン画面 (以前のリッチなレイアウトを復元) ---
@app.get("/", response_class=HTMLResponse)
async def view_training_plan():
    engine = DanielsFormulaEngine()
    plan, paces, details_db = engine.generate_plan(24)
    stats = engine.stats

    nav_html = """
    <nav style="margin-bottom: 25px; display: flex; gap: 15px; border-bottom: 2px solid #edf2f7; padding-bottom: 15px;">
        <a href="/" style="text-decoration: none; color: #2d3748; font-weight: bold; border-bottom: 3px solid #3182ce; padding: 8px 16px; background: #ebf8ff; border-radius: 6px 6px 0 0;">🏃 トレーニングプラン</a>
        <a href="/races" style="text-decoration: none; color: #718096; font-weight: bold; padding: 8px 16px; transition: 0.3s;">📅 レース日程一覧</a>
    </nav>
    """

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

    return f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head><meta charset="UTF-8"><title>Marathon Training Dashboard</title></head>
    <body style="font-family:'Helvetica Neue', Arial, sans-serif; padding:30px; background:#f4f7f6; color:#333;">
        <div style="max-width:1000px; margin:0 auto; background:white; padding:25px; border-radius:12px; box-shadow:0 4px 15px rgba(0,0,0,0.1);">
            {nav_html} {pace_html}
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
@app.get("/races", response_class=HTMLResponse)
async def view_race_schedule():
    races = load_races()

    nav_html = """
    <nav style="margin-bottom: 25px; display: flex; gap: 15px; border-bottom: 2px solid #edf2f7; padding-bottom: 15px;">
        <a href="/" style="text-decoration: none; color: #718096; font-weight: bold; padding: 8px 16px;">🏃 トレーニングプラン</a>
        <a href="/races" style="text-decoration: none; color: #2d3748; font-weight: bold; border-bottom: 3px solid #e53e3e; padding: 8px 16px; background: #fff5f5; border-radius: 6px 6px 0 0;">📅 レース日程一覧</a>
    </nav>
    """

    race_rows = "".join([f"""
        <tr style="border-bottom: 1px solid #eee;">
            <td style="padding: 15px;">{r['date']}</td>
            <td style="padding: 15px; font-weight: bold;">{r['name']}</td>
            <td style="padding: 15px;"><span style="background: #ebf8ff; color: #3182ce; padding: 4px 10px; border-radius: 20px; font-size: 0.85em;">{r['status']}</span></td>
        </tr>
    """ for r in races])

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Race Schedule</title></head>
    <body style="font-family: sans-serif; padding: 30px; background: #f4f7f6;">
        <div style="max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.05);">
            {nav_html}
            <div style="background: #fff5f5; padding: 20px; border-radius: 12px; border: 1px solid #feb2b2; margin-bottom: 30px;">
                <h3 style="margin-top:0; color:#c53030;">新規レース登録</h3>
                <div style="display: flex; gap: 10px;">
                    <input type="text" id="name" placeholder="大会名" style="flex:2; padding:10px; border:1px solid #ddd; border-radius:6px;">
                    <input type="text" id="date" placeholder="2026/05/02" style="flex:1; padding:10px; border:1px solid #ddd; border-radius:6px;">
                    <button onclick="addRace()" style="padding:10px 20px; background:#e53e3e; color:white; border:none; border-radius:6px; cursor:pointer; font-weight:bold;">追加保存</button>
                </div>
            </div>
            <table style="width: 100%; border-collapse: collapse;">
                <thead style="background: #f8fafc; text-align: left;">
                    <tr><th style="padding: 15px;">日付</th><th style="padding: 15px;">大会名</th><th style="padding: 15px;">状態</th></tr>
                </thead>
                <tbody>{race_rows if race_rows else '<tr><td colspan="3" style="text-align:center; padding:20px;">予定はありません</td></tr>'}</tbody>
            </table>
        </div>
        <script>
            async function addRace() {{
                const name = document.getElementById('name').value;
                const date = document.getElementById('date').value;
                if(!name || !date) return alert('入力してください');
                const res = await fetch('/api/races', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ name, date }})
                }});
                if(res.ok) location.reload();
            }}
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
