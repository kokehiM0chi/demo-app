import json
import pandas as pd
import webbrowser
from pathlib import Path
from datetime import timedelta

# フェーズごとの配色（背景用：非常に淡いパステルカラー）
PHASE_COLORS = {
    "Phase_I":   {"bg": "#f0f7ff", "text": "#0056b3", "label": "基礎構築"},
    "Phase_II":  {"bg": "#fff9f0", "text": "#9a6300", "label": "導入期"},
    "Phase_III": {"bg": "#fff5f5", "text": "#b91c1c", "label": "最大負荷"},
    "Phase_IV":  {"bg": "#faf5ff", "text": "#6b21a8", "label": "調整・レース"}
}

# トレーニング種別ごとの配色（右二つを水色・オレンジ系に調整）
MENU_THEMES = {
    "E": {"color": "#1b4332", "bg": "#d8f3dc", "label": "E (Easy Run)"},
    "L": {"color": "#0077b6", "bg": "#caf0f8", "label": "L (Long Run)"},  # 水色系
    "Q": {"color": "#e67e22", "bg": "#fef5e7", "label": "Q (Quality Sessions)"} # オレンジ系
}

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
        with open(self.base_path / "data/training_schedule_rules.json", "r") as f:
            self.schedule_rules = json.load(f)

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
                # 入力された基準が 5km か 10km かを判定して基準ペース(秒/km)を出す
                if self.stats["base_distance"] == "5km":
                    base_sec_per_km = self.time_to_seconds(v_row['5km']) / 5
                else:
                    base_sec_per_km = self.time_to_seconds(v_row['10km']) / 10

                # 1. Tペース (閾値): 10kmペースの約1.022倍 (VDOT 44で4:43を狙う)
                # 5kmペースから計算する場合は 約1.06倍
                if self.stats["base_distance"] == "10km":
                    t_pace_sec = base_sec_per_km * 1.022
                else:
                    t_pace_sec = base_sec_per_km * 1.06

                # 2. Iペース (インターバル): 5kmのレースペースそのもの
                i_pace_sec = self.time_to_seconds(v_row['5km']) / 5

                # 3. Rペース (レペティション):
                # 200mはTペース(秒/km)の約16.5%、400mはその2倍
                # VDOT 44: T(283秒) * 0.165 = 46.7秒 (約47秒)
                r_200_sec = t_pace_sec * 0.166
                r_400_sec = r_200_sec * 2

                # 4. Eペース上限: Tペースの約1.25倍
                e_limit_sec = t_pace_sec * 1.25

                return {
                    "T": self.seconds_to_str(t_pace_sec),
                    "I": self.seconds_to_str(i_pace_sec),
                    "R_400": self.seconds_to_str(r_400_sec),
                    "R_200": self.seconds_to_str(r_200_sec),
                    "E_limit": self.seconds_to_str(e_limit_sec)
                }
            except Exception as e:
                print(f"Pace calculation error: {e}")
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
                weekly_schedule = self.generate_weekly_schedule(
                    menus=menus,
                    l_run_max=l_run_max,
                    has_weekend_race=False
                )
                plan.append({
                    "week": week_count, "phase": phase_id, "vdot": v_row['Vdot'],
                    "focus": char["main_focus"], "menus": menus, "l_run_max": l_run_max,
                    "weekly_schedule": weekly_schedule
                })
                week_count += 1
        return plan, pace_summary

    def generate_weekly_schedule(self, menus, l_run_max, has_weekend_race=False):
        profile_key = "with_weekend_race" if has_weekend_race else "no_weekend_race"
        rule = self.schedule_rules["weekly_training_rules"][profile_key]

        default_easy = rule.get("default_easy_label", "E-Run / Recovery")
        day_plan = {day: default_easy for day in range(1, 8)}
        q_days = rule.get("q_day_slots", [])

        for idx, menu in enumerate(menus):
            day = q_days[idx] if idx < len(q_days) else None
            if day is None or day not in day_plan:
                continue
            day_plan[day] = f"Q{idx + 1}: {menu}"

        if has_weekend_race:
            race_day = rule.get("race_day", 7)
            race_label = rule.get("race_label", "Race (Weekend)")
            if race_day in day_plan:
                day_plan[race_day] = race_label
        else:
            long_run_day = rule.get("long_run_day", 7)
            l_run_label = f"L-Run: max {l_run_max}km"
            if long_run_day in day_plan:
                if day_plan[long_run_day].startswith("Q"):
                    day_plan[long_run_day] = f"{day_plan[long_run_day]} / {l_run_label}"
                else:
                    day_plan[long_run_day] = l_run_label

        return [f"Day {day}: {day_plan[day]}" for day in range(1, 8)]

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
    # パースサマリー
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
        <div style="flex:1; background:#ffffff; color:{MENU_THEMES['E']['color']}; padding:12px; border-radius:8px; text-align:center; border: 2px solid {MENU_THEMES['E']['color']};">
            <strong style="font-size:0.75em; opacity:0.8;">E Pace Guide (Upper)</strong><br>
            <span style="font-size:1.1em; font-weight:bold;">{pace_summary['E_limit']}</span><span style="font-size:0.8em;"> /km</span>
        </div>
    </div>
    """

    rows = ""
    for w in plan:
        q_sessions_html = "".join([f"<div style='margin-bottom: 3px;'>・{m}</div>" for m in w['menus']])
        weekly_schedule_html = "".join([f"<div style='margin-bottom: 3px;'>- {d}</div>" for d in w.get('weekly_schedule', [])])
        p_style = PHASE_COLORS.get(w['phase'], {"bg": "#ffffff", "text": "#333", "label": "不明"})

        rows += f"""
        <tr style="background:{p_style['bg']};">
            <td style="padding:15px; border:1px solid #ddd; text-align:center; font-weight:bold;">{w['week']}</td>
            <td style="padding:15px; border:1px solid #ddd;">
                <span style="background:{p_style['text']}; color:white; padding:3px 8px; border-radius:12px; font-size:0.8em; font-weight:bold; display:block; text-align:center; margin-bottom:4px;">
                    {w['phase']}
                </span>
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
                    <div style="margin-top:5px; padding-left:5px; color:{MENU_THEMES['Q']['color']}; font-size:0.95em; font-weight:bold;">{q_sessions_html if w['menus'] else 'E-Runのみ'}</div>
                </div>
                <div style="margin-top:10px; border-top:1px dashed rgba(0,0,0,0.1); padding-top:8px;">
                    <span style="font-size:0.75em; font-weight:bold; color:#2c3e50;">Day Plan (Rule Based)</span>
                    <div style="margin-top:5px; color:#444; font-size:0.82em; line-height:1.4;">{weekly_schedule_html}</div>
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

            <table style="border-collapse:collapse; width:100%; table-layout: fixed; border: 1px solid #ddd;">
                <thead>
                    <tr style="background:#f2f2f2;">
                        <th style="width: 8%; padding:12px; text-align:left; border:1px solid #ddd;">週</th>
                        <th style="width: 15%; padding:12px; text-align:left; border:1px solid #ddd;">フェーズ</th>
                        <th style="width: 20%; padding:12px; text-align:left; border:1px solid #ddd;">今週の目的</th>
                        <th style="width: 57%; padding:12px; text-align:left; border:1px solid #ddd;">トレーニング構成 (L / Q)</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
    </body></html>"""

    output_path = Path("daniels_custom_color_plan.html").absolute()
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    webbrowser.open(f"file://{output_path}")

if __name__ == "__main__":
    try:
        engine = DanielsFormulaEngine()
        plan, paces = engine.generate_plan(24)
        export_to_html(plan, paces, engine.stats)
        print("HTMLプランの作成が完了しました。")
    except Exception as e:
        print(f"エラーが発生しました: {e}")
