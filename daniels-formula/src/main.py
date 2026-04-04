import json
import pandas as pd
import webbrowser
from pathlib import Path

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
        """Qトレの距離制限"""
        if q_type == "R":
            limit = min(weekly_mileage * 0.05, 8.0)
            return f"R上限 {limit:.1f}km (200m×{int(limit/0.2)}本 / 400m×{int(limit/0.4)}本)"
        elif q_type == "I":
            limit = min(weekly_mileage * 0.08, 10.0)
            return f"I上限 {limit:.1f}km (1000m×{int(limit/1.0)}本 / 1200m×{int(limit/1.2)}本)"
        elif q_type == "T":
            limit = weekly_mileage * 0.10
            return f"T上限 {limit:.1f}km (20分持続走 / 1.6km×{int(limit/1.6)}本)"
        return "E-Run"

    def calculate_long_run_limit(self, weekly_mileage):
        """Lランニングの制限: 週間距離の30%"""
        return round(weekly_mileage * 0.30, 1)

    def generate_plan(self, target_weeks):
        vdot = self.get_current_vdot()
        weekly_mileage = self.stats["weekly_mileage"]
        l_run_dist = self.calculate_long_run_limit(weekly_mileage)

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
                    "long_run": f"{l_run_dist}km" # 30%ルール適用
                })
                week_count += 1
        return plan

def export_to_html(plan, stats):
    rows = ""
    for i, w in enumerate(plan):
        q_html = "".join([f"<div>・{m}</div>" for m in w['menus']]) if w['menus'] else "E-Runのみ"
        bg = "#ffffff" if i % 2 == 0 else "#f8f9fa"

        rows += f"""
        <tr style="background:{bg};">
            <td style="text-align:center; padding:12px; border-bottom:1px solid #ddd;">{w['week']}</td>
            <td style="padding:12px; border-bottom:1px solid #ddd;"><strong>{w['phase']}</strong></td>
            <td style="padding:12px; border-bottom:1px solid #ddd;">{w['focus']}</td>
            <td style="padding:12px; border-bottom:1px solid #ddd; color:#d32f2f;">{q_html}</td>
            <td style="padding:12px; border-bottom:1px solid #ddd; font-weight:bold; text-align:center; background:#fffde7;">{w['long_run']}</td>
        </tr>"""

    html = f"""
    <html>
    <head><meta charset="UTF-8"><style>
        body {{ font-family: sans-serif; padding:40px; color:#333; }}
        table {{ border-collapse: collapse; width: 100%; border-top: 3px solid #2c3e50; }}
        th {{ background:#f2f2f2; color:#2c3e50; padding:15px; text-align:left; border-bottom:2px solid #2c3e50; }}
        .stats-banner {{ background:#2c3e50; color:white; padding:20px; border-radius:4px; margin-bottom:20px; }}
    </style></head>
    <body>
        <div class="stats-banner">
            <h2 style="margin:0;">Daniels Training Plan (30% L-Run Rule Applied)</h2>
            <p style="margin:10px 0 0 0;">基準: {stats['base_distance']} {stats['base_time']} | 週間 {stats['weekly_mileage']}km (L-Run上限: {plan[0]['long_run']})</p>
        </div>
        <table>
            <thead>
                <tr><th>週</th><th>フェーズ</th><th>目的</th><th>Qトレ (距離制限)</th><th>Lラン (30%)</th></tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </body></html>"""

    with open("daniels_plan_30pct.html", "w", encoding="utf-8") as f: f.write(html)
    webbrowser.open(f"file://{Path('daniels_plan_30pct.html').absolute()}")

if __name__ == "__main__":
    engine = DanielsFormulaEngine()
    plan = engine.generate_plan(24)
    export_to_html(plan, engine.stats)
