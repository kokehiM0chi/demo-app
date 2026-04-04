import json
import pandas as pd
import webbrowser
from pathlib import Path
from datetime import timedelta

class DanielsConstants:
    RECOVERY_MIN_MINUTES = 30
    L_RUN_MAX_RATIO = 0.30
    I_RUN_MAX_RATIO = 0.08
    R_RUN_MAX_RATIO = 0.05
    E_LIMIT_RATIO = 1.22

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

    def time_to_seconds(self, time_str):
        parts = str(time_str).split(':')
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return int(parts[0]) * 60 + int(parts[1])

    def seconds_to_str(self, seconds):
        td = timedelta(seconds=int(seconds))
        minutes, seconds = divmod(td.seconds, 60)
        return f"{minutes}:{seconds:02d}"

    def get_vdot_row(self):
        dist = self.stats["base_distance"]
        time = self.stats["base_time"]
        return self.vdot_df.loc[self.vdot_df[dist] <= time].iloc[0]

    def calculate_paces(self, v_row):
        try:
            sec_5k = self.time_to_seconds(v_row['5km'])
            i_pace_sec = sec_5k / 5
            sec_10k = self.time_to_seconds(v_row['10km'])
            t_pace_sec = (sec_10k / 10) * 1.07
            e_limit_sec = t_pace_sec * DanielsConstants.E_LIMIT_RATIO
            sec_1500 = self.time_to_seconds(v_row['1.5km'])
            r_base_per_m = sec_1500 / 1500
            r_400_sec = (r_base_per_m * 400) * 0.95
            r_200_sec = r_400_sec / 2

            return {
                "T": self.seconds_to_str(t_pace_sec),
                "I": self.seconds_to_str(i_pace_sec),
                "R_400": self.seconds_to_str(r_400_sec),
                "R_200": self.seconds_to_str(r_200_sec),
                "E_limit": self.seconds_to_str(e_limit_sec)
            }
        except Exception:
            return {"T": "N/A", "I": "N/A", "R_400": "N/A", "R_200": "N/A", "E_limit": "N/A"}

    def generate_plan(self, target_weeks):
        v_row = self.get_vdot_row()
        pace_summary = self.calculate_paces(v_row)
        l_run_max = round(self.stats["weekly_mileage"] * DanielsConstants.L_RUN_MAX_RATIO, 1)

        allocation = {p: len([n for n in d["priority_numbers"] if n <= target_weeks])
                      for p, d in self.priority["phases"].items()}

        plan = []
        week_count = 1
        for phase_id in ["Phase_I", "Phase_II", "Phase_III", "Phase_IV"]:
            weeks = allocation[phase_id]
            char = self.chars["phase_rules"][phase_id]
            for _ in range(weeks):
                menus = [self.calculate_menu_details(q["type"], self.stats["weekly_mileage"]) for q in char["q_sessions"]]
                plan.append({
                    "week": week_count, "phase": phase_id, "vdot": v_row['Vdot'],
                    "focus": char["main_focus"], "menus": menus, "l_run_max": l_run_max
                })
                week_count += 1
        return plan, pace_summary

    def calculate_menu_details(self, q_type, weekly_mileage):
        if q_type == "R":
            limit = min(weekly_mileage * DanielsConstants.R_RUN_MAX_RATIO, 8.0)
            return f"R上限 {limit:.1f}km (200m/400m)"
        elif q_type == "I":
            limit = min(weekly_mileage * DanielsConstants.I_RUN_MAX_RATIO, 10.0)
            return f"I上限 {limit:.1f}km (1000m/1200m)"
        elif q_type == "T":
            limit = weekly_mileage * 0.10
            return f"T上限 {limit:.1f}km (持続走/1.6km)"
        return "E-Run"

def export_to_html(plan, pace_summary, stats):
    pace_html = f"""
    <div class="pace-container" style="display: flex; gap: 10px; margin-bottom: 20px;">
        <div style="flex:1; background:#2c3e50; color:white; padding:12px; border-radius:8px; text-align:center;">
            <strong style="font-size:0.75em; opacity:0.8;">T Pace (閾値)</strong><br>
            <span style="font-size:1.1em;">{pace_summary['T']}</span><span style="font-size:0.8em;"> /km</span>
        </div>
        <div style="flex:1; background:#2c3e50; color:white; padding:12px; border-radius:8px; text-align:center;">
            <strong style="font-size:0.75em; opacity:0.8;">I Pace (インターバル)</strong><br>
            <span style="font-size:1.1em;">{pace_summary['I']}</span><span style="font-size:0.8em;"> /km</span>
        </div>
        <div style="flex:1; background:#2c3e50; color:white; padding:12px; border-radius:8px; text-align:center;">
            <strong style="font-size:0.75em; opacity:0.8;">R (400m / 200m)</strong><br>
            <span style="font-size:1.1em;">{pace_summary['R_400']}</span><span style="font-size:0.8em;"> / </span>
            <span style="font-size:1.1em;">{pace_summary['R_200']}</span>
        </div>
        <div style="flex:1; background:#27ae60; color:white; padding:12px; border-radius:8px; text-align:center; border: 2px solid #2ecc71;">
            <strong style="font-size:0.75em; color: #d1f2eb;">E Pace Guide (Upper)</strong><br>
            <span style="font-size:1.1em; font-weight:bold;">{pace_summary['E_limit']}</span><span style="font-size:0.8em;"> /km</span>
        </div>
    </div>
    """

    rows = ""
    for i, w in enumerate(plan):
        q_sessions_html = "".join([f"<div style='margin-bottom: 3px;'>・{m}</div>" for m in w['menus']])
        bg = "#ffffff" if i % 2 == 0 else "#fcfcfc"
        rows += f"""
        <tr style="background:{bg};">
            <td style="padding:15px; border:1px solid #eee; text-align:center; font-weight:bold;">{w['week']}</td>
            <td style="padding:15px; border:1px solid #eee;"><strong>{w['phase']}</strong></td>
            <td style="padding:15px; border:1px solid #eee; font-size:0.85em; color:#555;">{w['focus']}</td>
            <td style="padding:15px; border:1px solid #eee;">
                <div style="margin-bottom:10px; border-bottom:1px dashed #eee; padding-bottom:8px;">
                    <span style="background:#e8f5e9; color:#27ae60; padding:2px 6px; border-radius:4px; font-size:0.75em; font-weight:bold; margin-right:8px;">L (Long Run)</span>
                    <strong style="color:#2c3e50;">最大 {w['l_run_max']} km</strong>
                </div>
                <div>
                    <span style="background:#fff1f0; color:#c0392b; padding:2px 6px; border-radius:4px; font-size:0.75em; font-weight:bold; margin-right:8px;">Q (Quality Sessions)</span>
                    <div style="margin-top:5px; padding-left:5px; color:#c0392b; font-size:0.95em;">{q_sessions_html if w['menus'] else 'E-Runのみ'}</div>
                </div>
            </td>
        </tr>"""

    html = f"""
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="font-family:-apple-system, sans-serif; padding:30px; background:#f4f7f6; color:#333; line-height:1.5;">
        <div style="max-width:1000px; margin:0 auto; background:white; padding:25px; border-radius:12px; box-shadow:0 4px 15px rgba(0,0,0,0.1);">
            {pace_html}

            <div style="background:#34495e; color:white; padding:15px; border-radius:8px 8px 0 0; display:flex; justify-content:space-between; align-items:center;">
                <h2 style="margin:0; font-size:1.4em;">Daniels 24-Week Plan (VDOT: {plan[0]['vdot']})</h2>
                <div style="font-size:0.8em; background:rgba(255,255,255,0.1); padding:5px 10px; border-radius:4px;">Weekly Mileage: {stats['weekly_mileage']}km</div>
            </div>

            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 15px 0;">
                <div style="background:#f1f8ff; border-left:4px solid #0366d6; padding:10px; font-size:0.8em;">
                    <strong style="color:#0366d6;">E (Easy Run)</strong><br>
                    <strong>目的:</strong> 心筋強化・回復・基礎作り<br>
                    <strong>Note:</strong> 指定ペースを「超えない」余裕を持つことで、翌日のQセッションへ活力を繋げます。
                </div>
                <div style="background:#f6ffed; border-left:4px solid #52c41a; padding:10px; font-size:0.8em;">
                    <strong style="color:#52c41a;">L (Long Run)</strong><br>
                    <strong>目的:</strong> 持久力の向上・脂質代謝改善<br>
                    <strong>Note:</strong> 週の走行距離の25-30%を目安に、リズム良く走り切る力を養います。
                </div>
                <div style="background:#fff7f6; border-left:4px solid #f5222d; padding:10px; font-size:0.8em;">
                    <strong style="color:#f5222d;">Q (Quality Sessions)</strong><br>
                    <strong>目的:</strong> 強度別の走力向上(T/I/R)<br>
                    <strong>Note:</strong> 鮮度の高い脚で挑むことで、トレーニング効果を最大化させます。
                </div>
            </div>

            <table style="border-collapse:collapse; width:100%; border:1px solid #ddd; table-layout: fixed;">
                <thead>
                    <tr style="background:#f2f2f2;">
                        <th style="width: 8%; padding:12px; text-align:left;">週</th>
                        <th style="width: 15%; padding:12px; text-align:left;">フェーズ</th>
                        <th style="width: 20%; padding:12px; text-align:left;">今週の目的</th>
                        <th style="width: 57%; padding:12px; text-align:left;">トレーニング構成 (L / Q)</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
    </body></html>"""

    output_path = Path("daniels_final_fix.html").absolute()
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    webbrowser.open(f"file://{output_path}")

if __name__ == "__main__":
    engine = DanielsFormulaEngine()
    plan, paces = engine.generate_plan(24)
    export_to_html(plan, paces, engine.stats)
