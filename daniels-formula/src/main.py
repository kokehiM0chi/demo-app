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

    def get_vdot(self, time_str):
        # 5kmのタイムからVDOTを特定（22:15なら44.5付近）
        target = self.vdot_df.loc[self.vdot_df['5km'] <= time_str].iloc[0]
        return target['Vdot']

    def generate_plan(self, target_weeks, weekly_mileage, time_str):
        vdot = self.get_vdot(time_str)

        # フェーズごとの週数計算（24週なら各6週になるはず）
        allocation = {}
        for p_key, details in self.priority["phases"].items():
            count = len([n for n in details["priority_numbers"] if n <= target_weeks])
            allocation[p_key] = count

        plan = []
        week_count = 1
        # I -> II -> III -> IV の順で生成
        for phase_id in ["Phase_I", "Phase_II", "Phase_III", "Phase_IV"]:
            weeks = allocation[phase_id]
            char = self.chars["phase_rules"][phase_id]

            for _ in range(weeks):
                plan.append({
                    "week": week_count,
                    "phase": phase_id,
                    "vdot": vdot,
                    "focus": char["main_focus"],
                    "q_sessions": char["q_sessions"],
                    "long_run": f"{weekly_mileage * 0.25:.1f}km"
                })
                week_count += 1
        return plan

def export_to_html(plan):
    rows = ""
    for w in plan:
        # Qトレの内容を整形
        q_types = [q['type'] for q in w['q_sessions']] if w['q_sessions'] else ["E-Easy"]
        q_text = " + ".join(q_types)

        # フェーズごとに色分け
        colors = {"Phase_I": "#e3f2fd", "Phase_II": "#fff3e0", "Phase_III": "#fce4ec", "Phase_IV": "#e8f5e9"}
        bg_color = colors.get(w['phase'], "white")

        rows += f"""
        <tr style="background-color: {bg_color};">
            <td style="text-align:center;">{w['week']}</td>
            <td><strong>{w['phase']}</strong></td>
            <td>VDOT {w['vdot']}</td>
            <td>{w['focus']}</td>
            <td>{q_text}</td>
            <td>{w['long_run']}</td>
        </tr>"""

    html = f"""
    <html>
    <head><meta charset="UTF-8"><title>Daniels 24-Week Plan</title></head>
    <body style="font-family:sans-serif; padding:40px; color:#333;">
        <h1>The Daniels Formula: 24週間トレーニング計画</h1>
        <p>設定ベース: 5km {plan[0]['vdot']}相当のタイム</p>
        <table border="1" style="border-collapse:collapse; width:100%;">
            <thead style="background:#333; color:white;">
                <tr><th>週</th><th>フェーズ</th><th>VDOT</th><th>主な目的</th><th>Qトレーニング</th><th>Lラン</th></tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </body>
    </html>"""

    output_path = Path("daniels_menu_24weeks.html").absolute()
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    webbrowser.open(f"file://{output_path}")

def main():
    engine = DanielsFormulaEngine()
    # 24週間、週間走行距離45km、5km 22:15の実績で生成
    plan = engine.generate_plan(target_weeks=24, weekly_mileage=45, time_str="22:15")
    export_to_html(plan)

if __name__ == "__main__":
    main()
