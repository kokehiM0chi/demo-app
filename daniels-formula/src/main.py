import json
import pandas as pd
import webbrowser
from pathlib import Path

# ダニエルズ理論の不変のルールを定義（ドメイン定数）
class DanielsConstants:
    RECOVERY_MIN_MINUTES = 30
    E_PACE_HR_MAX = 79 # 最大心拍数の79%
    E_PACE_HR_MIN = 65 # 最大心拍数の65%
    L_RUN_MAX_RATIO = 0.30 # 週間距離の30%
    I_RUN_MAX_RATIO = 0.08 # 週間距離の8%
    R_RUN_MAX_RATIO = 0.05 # 週間距離の5%

class DanielsFormulaEngine:
    def __init__(self):
        self.base_path = Path(__file__).parent.parent
        self.vdot_df = pd.read_csv(self.base_path / "data/vdot_table.csv")

        with open(self.base_path / "data/phase_priority.json", "r") as f:
            self.priority = json.load(f)
        with open(self.base_path / "data/phase_characteristics.json", "r") as f:
            self.chars = json.load(f)
        with open(self.base_path / "data/user_stats.json", "r") as f:
            self.stats = json.load(f)

    def get_current_vdot(self):
        dist = self.stats["base_distance"]
        time = self.stats["base_time"]
        target_row = self.vdot_df.loc[self.vdot_df[dist] <= time].iloc[0]
        return target_row['Vdot']

    def calculate_menu_details(self, q_type, weekly_mileage):
        if q_type == "R":
            limit = min(weekly_mileage * DanielsConstants.R_RUN_MAX_RATIO, 8.0)
            return f"R上限 {limit:.1f}km (200m×{int(limit/0.2)}本 / 400m×{int(limit/0.4)}本)"
        elif q_type == "I":
            limit = min(weekly_mileage * DanielsConstants.I_RUN_MAX_RATIO, 10.0)
            return f"I上限 {limit:.1f}km (1000m×{int(limit/1.0)}本 / 1200m×{int(limit/1.2)}本)"
        elif q_type == "T":
            limit = weekly_mileage * 0.10
            return f"T上限 {limit:.1f}km (20分持続走 / 1.6km×{int(limit/1.6)}本)"
        return "E-Run"

    def generate_plan(self, target_weeks):
        vdot = self.get_current_vdot()
        weekly_mileage = self.stats["weekly_mileage"]
        l_run_max = round(weekly_mileage * DanielsConstants.L_RUN_MAX_RATIO, 1)

        allocation = {p: len([n for n in d["priority_numbers"] if n <= target_weeks])
                      for p, d in self.priority["phases"].items()}

        plan = []
        week_count = 1
        for phase_id in ["Phase_I", "Phase_II", "Phase_III", "Phase_IV"]:
            weeks = allocation[phase_id]
            char = self.chars["phase_rules"][phase_id]
            for _ in range(weeks):
                menus = [self.calculate_menu_details(q["type"], weekly_mileage) for q in char["q_sessions"]]
                plan.append({
                    "week": week_count,
                    "phase": phase_id,
                    "vdot": vdot,
                    "focus": char["main_focus"],
                    "menus": menus,
                    "l_run_max": f"{l_run_max}km"
                })
                week_count += 1
        return plan

def export_to_html(plan, stats):
    caution_html = f"""
    <div class="caution-box">
        <h3 style="margin-top:0; color:#e65100; border-bottom: 1px solid #ffcc80; padding-bottom: 5px;">⚠️ ダニエルズ流：リカバリーとトレーニング原則</h3>
        <ul style="margin-bottom: 0;">
            <li><strong>リカバリージョグの切り替え:</strong> 疲労時はQトレを中止。最低<strong>{DanielsConstants.RECOVERY_MIN_MINUTES}分以上</strong>走ること。</li>
            <li><strong>ペースの厳守:</strong> Eペースは最大心拍数の{DanielsConstants.E_PACE_HR_MIN}%〜{DanielsConstants.E_PACE_HR_MAX}%。</li>
            <li><strong>フォームの維持:</strong> 「どれだけ遅くても良い」が、フォームが崩れない範囲で。</li>
        </ul>
    </div>
    """

    rows = ""
    for i, w in enumerate(plan):
        q_html = "".join([f"<div style='margin-bottom: 5px;'>・{m}</div>" for m in w['menus']]) if w['menus'] else "E-Runのみ"
        bg = "#ffffff" if i % 2 == 0 else "#fcfcfc"

        rows += f"""
        <tr style="background:{bg};">
            <td class="cell-week">{w['week']}</td>
            <td class="cell-phase"><strong>{w['phase']}</strong></td>
            <td class="cell-focus">{w['focus']}</td>
            <td class="cell-q">{q_html}</td>
            <td class="cell-l">
                <span class="l-label">Max</span><br>{w['l_run_max']}
            </td>
        </tr>"""

    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding:40px; color:#333; background-color: #f4f7f6; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
            .caution-box {{ background:#fff8e1; border: 1px solid #ffe082; padding:20px; border-radius:8px; margin-bottom:30px; line-height: 1.6; }}
            .stats-banner {{ background:#2c3e50; color:white; padding:25px; border-radius:8px 8px 0 0; margin-bottom: 0; }}
            .stats-banner h2 {{ margin:0; font-size: 1.8em; }}
            .stats-banner p {{ margin:8px 0 0 0; opacity: 0.9; font-size: 1.1em; }}

            table {{ border-collapse: collapse; width: 100%; border: 2px solid #2c3e50; background: white; table-layout: fixed; }}
            th {{ background:#34495e; color:white; padding:18px 12px; text-align:left; font-size: 0.95em; border: 1px solid #2c3e50; }}
            th.l-run-header {{ background:#27ae60; border-color: #1e8449; }}

            td {{ padding: 18px 12px; border: 1px solid #ecf0f1; vertical-align: top; word-wrap: break-word; }}
            .cell-week {{ text-align: center; width: 50px; font-weight: bold; }}
            .cell-phase {{ width: 140px; }}
            .cell-focus {{ width: 180px; font-size: 0.9em; }}
            .cell-q {{ color:#c0392b; font-size: 0.95em; }}
            .cell-l {{ text-align: center; width: 110px; font-weight: bold; background-color: #f9fffb; border-left: 2px solid #27ae60; }}
            .l-label {{ font-size: 0.75em; color: #27ae60; text-transform: uppercase; letter-spacing: 1px; }}

            tr:hover {{ background-color: #f1f4f6 !important; }}
        </style>
    </head>
    <body>
        <div class="container">
            {caution_html}
            <div class="stats-banner">
                <h2>Daniels 24-Week Plan (VDOT: {plan[0]['vdot']})</h2>
                <p>基準: {stats['base_distance']} {stats['base_time']} | 週間 {stats['weekly_mileage']}km想定</p>
            </div>
            <table>
                <thead>
                    <tr>
                        <th style="width: 6%;">週</th>
                        <th style="width: 15%;">フェーズ</th>
                        <th style="width: 20%;">主な目的</th>
                        <th style="width: 44%;">Qセッション (距離制限適用)</th>
                        <th class="l-run-header" style="width: 15%;">Lラン上限 (30%)</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
            <p style="margin-top: 15px; color: #7f8c8d; font-size: 0.85em;">※ Lラン上限を超えない範囲で、自身の疲労度に合わせて距離を調整してください。</p>
        </div>
    </body></html>"""

    output_path = Path("daniels_plan_final.html").absolute()
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    webbrowser.open(f"file://{output_path}")

if __name__ == "__main__":
    engine = DanielsFormulaEngine()
    plan = engine.generate_plan(24)
    export_to_html(plan, engine.stats)
