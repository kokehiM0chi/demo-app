import webbrowser
from pathlib import Path
from daniels_engine import DanielsFormulaEngine

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

def export_to_html(plan, paces, details_db, stats):
    pace_html = f"""
    <div class="pace-container" style="display: flex; gap: 10px; margin-bottom: 20px;">
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
                <div style="margin-top:10px; border-top:1px dashed rgba(0,0,0,0.1); padding-top:8px;">
                    <div style="margin-top:5px; color:#444; font-size:0.82em; line-height:1.4;">{sched_html}</div>
                </div>
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
        <div style="text-align:right; margin-top:8px;"><a href="#" style="font-size:0.75em; color:#3498db;">↑ スケジュールに戻る</a></div>
    </div>""" for qid, d in details_db.items()])

    final_html = f"""
    <html><head><meta charset="UTF-8"></head>
    <body style="font-family:sans-serif; padding:30px; background:#f4f7f6; color:#333;">
        <div style="max-width:1000px; margin:0 auto; background:white; padding:25px; border-radius:12px; box-shadow:0 4px 15px rgba(0,0,0,0.1);">
            {pace_html}
            <div style="background:#34495e; color:white; padding:15px; border-radius:8px 8px 0 0; display:flex; justify-content:space-between; align-items:center;">
                <h2 style="margin:0; font-size:1.4em;">Daniels 24-Week Plan (VDOT: {plan[0]['vdot']})</h2>
                <div style="font-size:0.8em; background:rgba(255,255,255,0.1); padding:5px 10px; border-radius:4px;">Weekly Mileage: {stats['weekly_mileage']}km</div>
            </div>

            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 15px 0;">
                <div style="background:{MENU_THEMES['E']['bg']}; border-top:4px solid {MENU_THEMES['E']['color']}; padding:10px; font-size:0.8em; border-radius:0 0 4px 4px;">
                    <strong style="color:{MENU_THEMES['E']['color']};">{MENU_THEMES['E']['label']}</strong><br>
                    <strong>目的:</strong> 心筋強化・回復・基礎作り<br>
                    <strong>Note:</strong> 指定ペースを「超えない」余裕を持つことで、翌日のQセッションへ活力を繋げます。
                </div>
                <div style="background:{MENU_THEMES['L']['bg']}; border-top:4px solid {MENU_THEMES['L']['color']}; padding:10px; font-size:0.8em; border-radius:0 0 4px 4px;">
                    <strong style="color:{MENU_THEMES['L']['color']};">{MENU_THEMES['L']['label']}</strong><br>
                    <strong>目的:</strong> 持久力の向上・脂質代謝改善<br>
                    <strong>Note:</strong> 週の走行距離の25-30%を目安に、リズム良く走り切る力を養います。
                </div>
                <div style="background:{MENU_THEMES['Q']['bg']}; border-top:4px solid {MENU_THEMES['Q']['color']}; padding:10px; font-size:0.8em; border-radius:0 0 4px 4px;">
                    <strong style="color:{MENU_THEMES['Q']['color']};">{MENU_THEMES['Q']['label']}</strong><br>
                    <strong>目的:</strong> 強度別の走力向上(T/I/R)<br>
                    <strong>Note:</strong> 鮮度の高い脚で挑むことで、トレーニング効果を最大化させます。週末レースがない週はQ1・Q2・Q3を2日目・4日目・7日目に配置します。
                </div>
            </div>

            <table style="border-collapse:collapse; width:100%; border: 1px solid #ddd;">
                <thead><tr style="background:#f2f2f2;">
                    <th style="width:8%; padding:12px; text-align:left; border:1px solid #ddd;">週</th>
                    <th style="width:15%; padding:12px; text-align:left; border:1px solid #ddd;">フェーズ</th>
                    <th style="width:20%; padding:12px; text-align:left; border:1px solid #ddd;">今週の目的</th>
                    <th style="width:57%; padding:12px; text-align:left; border:1px solid #ddd;">トレーニング構成 (L / Q)</th>
                </tr></thead>
                <tbody>{rows}</tbody>
            </table>

            <h3 style="margin-top:40px; border-bottom:2px solid #34495e; padding-bottom:10px;">Qセッション詳細リファレンス</h3>
            {detail_html}
        </div>
    </body></html>"""

    out = Path("daniels_detail_plan.html").absolute()
    with open(out, "w", encoding="utf-8") as f: f.write(final_html)
    webbrowser.open(f"file://{out}")

if __name__ == "__main__":
    engine = DanielsFormulaEngine()
    plan, paces, details = engine.generate_plan(24)
    export_to_html(plan, paces, details, engine.stats)
