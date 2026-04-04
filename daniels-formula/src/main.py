import json
import pandas as pd
import webbrowser
from pathlib import Path
from datetime import timedelta  # 必須: タイム計算用

class DanielsConstants:
    RECOVERY_MIN_MINUTES = 30
    L_RUN_MAX_RATIO = 0.30
    I_RUN_MAX_RATIO = 0.08
    R_RUN_MAX_RATIO = 0.05

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
        """'MM:SS' または 'H:MM:SS' を秒に変換"""
        parts = str(time_str).split(':')
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return int(parts[0]) * 60 + int(parts[1])

    def seconds_to_str(self, seconds):
        """秒を 'M:SS' 形式に変換"""
        td = timedelta(seconds=int(seconds))
        minutes, seconds = divmod(td.seconds, 60)
        return f"{minutes}:{seconds:02d}"

    def get_vdot_row(self):
        dist = self.stats["base_distance"]
        time = self.stats["base_time"]
        # 現在のタイムに基づき、該当するVDOT行を取得
        return self.vdot_df.loc[self.vdot_df[dist] <= time].iloc[0]

    def calculate_paces(self, v_row):
        """
        提供されたレースタイムからダニエルズの強度を逆算
        """
        try:
            # Iペース: 5kmタイムの平均1km (ダニエルズのインターバル強度の目安)
            sec_5k = self.time_to_seconds(v_row['5km'])
            i_pace_sec = sec_5k / 5

            # Tペース: 10kmタイムの平均1kmに約1.06〜1.08倍の時間をかける
            # (10kmタイムより少し遅い、1時間程度維持できるペース)
            sec_10k = self.time_to_seconds(v_row['10km'])
            t_pace_sec = (sec_10k / 10) * 1.07

            # Rペース: 1.5km(1500m)の平均よりさらに速いペース
            sec_1500 = self.time_to_seconds(v_row['1.5km'])
            r_base_per_m = sec_1500 / 1500

            # R(400m)は1500mの平均ペースの約94-95%程度の時間
            r_400_sec = (r_base_per_m * 400) * 0.95
            r_200_sec = r_400_sec / 2

            return {
                "T": self.seconds_to_str(t_pace_sec),
                "I": self.seconds_to_str(i_pace_sec),
                "R_400": self.seconds_to_str(r_400_sec),
                "R_200": self.seconds_to_str(r_200_sec)
            }
        except Exception as e:
            print(f"Error calculating paces: {e}")
            return {"T": "N/A", "I": "N/A", "R_400": "N/A", "R_200": "N/A"}

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
                    "focus": char["main_focus"], "menus": menus, "l_run_max": f"{l_run_max}km"
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
        <div style="flex:1; background:#2c3e50; color:white; padding:15px; border-radius:8px; text-align:center; box-shadow: 0 2px 5px rgba(0,0,0,0.2);">
            <strong style="font-size:0.8em; opacity:0.8;">T Pace (閾値)</strong><br>
            <span style="font-size:1.2em;">{pace_summary['T']}</span> /km
        </div>
        <div style="flex:1; background:#2c3e50; color:white; padding:15px; border-radius:8px; text-align:center; box-shadow: 0 2px 5px rgba(0,0,0,0.2);">
            <strong style="font-size:0.8em; opacity:0.8;">I Pace (インターバル)</strong><br>
            <span style="font-size:1.2em;">{pace_summary['I']}</span> /km
        </div>
        <div style="flex:1; background:#2c3e50; color:white; padding:15px; border-radius:8px; text-align:center; box-shadow: 0 2px 5px rgba(0,0,0,0.2);">
            <strong style="font-size:0.8em; opacity:0.8;">R Pace (400m)</strong><br>
            <span style="font-size:1.2em;">{pace_summary['R_400']}</span>
        </div>
        <div style="flex:1; background:#2c3e50; color:white; padding:15px; border-radius:8px; text-align:center; box-shadow: 0 2px 5px rgba(0,0,0,0.2);">
            <strong style="font-size:0.8em; opacity:0.8;">R Pace (200m)</strong><br>
            <span style="font-size:1.2em;">{pace_summary['R_200']}</span>
        </div>
    </div>
    """

    rows = ""
    for i, w in enumerate(plan):
        q_html = "".join([f"<div style='margin-bottom: 5px;'>・{m}</div>" for m in w['menus']]) if w['menus'] else "E-Runのみ"
        bg = "#ffffff" if i % 2 == 0 else "#fcfcfc"
        rows += f"""
        <tr style="background:{bg};">
            <td style="padding:15px; border:1px solid #eee; text-align:center; font-weight:bold;">{w['week']}</td>
            <td style="padding:15px; border:1px solid #eee;"><strong>{w['phase']}</strong></td>
            <td style="padding:15px; border:1px solid #eee; font-size:0.9em;">{w['focus']}</td>
            <td style="padding:15px; border:1px solid #eee; color:#c0392b;">{q_html}</td>
            <td style="padding:15px; border:1px solid #eee; text-align:center; background:#f9fffb; border-left:2px solid #27ae60;">
                <span style="font-size:0.7em; color:#27ae60; font-weight:bold; letter-spacing:1px;">MAX</span><br><strong>{w['l_run_max']}</strong>
            </td>
        </tr>"""

    html = f"""
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="font-family:-apple-system, sans-serif; padding:30px; background:#f4f7f6;">
        <div style="max-width:1000px; margin:0 auto; background:white; padding:25px; border-radius:12px; box-shadow:0 4px 15px rgba(0,0,0,0.1);">
            {pace_html}
            <div style="background:#34495e; color:white; padding:15px; border-radius:8px 8px 0 0;">
                <h2 style="margin:0;">Daniels 24-Week Plan (VDOT: {plan[0]['vdot']})</h2>
            </div>
            <table style="border-collapse:collapse; width:100%; border:1px solid #ddd; table-layout: fixed;">
                <thead>
                    <tr style="background:#f2f2f2;">
                        <th style="width: 8%; padding:12px; text-align:left;">週</th>
                        <th style="width: 15%; padding:12px; text-align:left;">フェーズ</th>
                        <th style="width: 20%; padding:12px; text-align:left;">目的</th>
                        <th style="width: 42%; padding:12px; text-align:left;">Qセッション (上限距離)</th>
                        <th style="width: 15%; padding:12px; text-align:center; background:#e8f5e9;">Lラン上限</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
            <p style="margin-top:15px; font-size:0.8em; color:#666;">※ ペースは提供されたレースタイムテーブルからダニエルズの公式に基づき逆算した推定値です。</p>
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
