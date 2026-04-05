import json
import pandas as pd
from pathlib import Path
from datetime import timedelta

class DanielsConstants:
    """Danielsランニングフォーミュラの定数"""
    L_RUN_MAX_RATIO = 0.30
    I_RUN_MAX_RATIO = 0.08
    T_LIMIT_RATIO = 0.10
    R_RUN_MAX_RATIO = 0.05
    E_LIMIT_RATIO = 1.25
    T_COEFF = 1.022

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
        td = timedelta(seconds=int(round(seconds)))
        minutes, seconds = divmod(td.seconds, 60)
        return f"{minutes}:{seconds:02d}"

    def get_vdot_row(self):
        dist = self.stats["base_distance"]
        time = self.stats["base_time"]
        return self.vdot_df.loc[self.vdot_df[dist] <= time].iloc[0]

    def calculate_paces(self, v_row):
        p_1500_sec = self.time_to_seconds(v_row['1.5km']) / 1.5
        p_5km_sec = self.time_to_seconds(v_row['5km']) / 5
        p_10km_sec = self.time_to_seconds(v_row['10km']) / 10

        t_sec = p_10km_sec * DanielsConstants.T_COEFF
        i_sec = p_5km_sec * 1.00
        r_km_str = self.seconds_to_str(p_1500_sec)

        return {
            "T": self.seconds_to_str(t_sec),
            "I": self.seconds_to_str(i_sec),
            "R_400": f"{self.seconds_to_str(p_1500_sec * 0.4)} ({r_km_str}/km)",
            "R_200": f"{self.seconds_to_str(p_1500_sec * 0.2)} ({r_km_str}/km)",
            "E_limit": self.seconds_to_str(t_sec * DanielsConstants.E_LIMIT_RATIO),
            "raw_r_sec": p_1500_sec
        }

    def generate_plan(self, target_weeks):
        v_row = self.get_vdot_row()
        paces = self.calculate_paces(v_row)
        l_max = round(self.stats["weekly_mileage"] * DanielsConstants.L_RUN_MAX_RATIO, 1)

        allocation = {p: len([n for n in d["priority_numbers"] if n <= target_weeks])
                      for p, d in self.priority["phases"].items()}

        plan = []
        details_db = {}
        week_count = 1

        for phase_id in ["Phase_I", "Phase_II", "Phase_III", "Phase_IV"]:
            weeks = allocation[phase_id]
            char = self.chars["phase_rules"][phase_id]
            for _ in range(weeks):
                week_menus = []
                for idx, q in enumerate(char["q_sessions"]):
                    q_id = f"W{week_count}_Q{idx+1}"
                    # 詳細情報の生成
                    detail = self.create_detail_obj(q["type"], paces, self.stats["weekly_mileage"])
                    details_db[q_id] = detail
                    # スケジュール表示用
                    week_menus.append({"id": q_id, "summary": detail["summary"]})

                plan.append({
                    "week": week_count, "phase": phase_id, "vdot": v_row['Vdot'],
                    "focus": char["main_focus"], "menus": week_menus, "l_run_max": l_max,
                    "weekly_schedule": self.generate_weekly_schedule(week_menus, l_max)
                })
                week_count += 1
        return plan, paces, details_db

    def create_detail_obj(self, q_type, paces, weekly_km):
            if q_type == "R":
                # 1. 上限距離の算出 (8km or 週間5%)
                limit = min(weekly_km * DanielsConstants.R_RUN_MAX_RATIO, 8.0)

                # --- パターンA: ミックス (400m + 200m) ---
                mix_n400 = int((limit * 0.6) // 0.4)
                mix_n200 = int((limit - (mix_n400 * 0.4)) // 0.2)

                # --- パターンB: 400mのみ ---
                only_n400 = int(limit // 0.4)

                # --- パターンC: 200mのみ ---
                only_n200 = int(limit // 0.2)

                # 休息時間の計算 (走行時間の3倍)
                r400_s = paces["raw_r_sec"] * 0.4
                y_m, y_s = divmod(int(r400_s * 3), 60)
                r200_s = paces["raw_r_sec"] * 0.2
                x_m, x_s = divmod(int(r200_s * 3), 60)

                # HTML/表示用のテキスト構成
                menu_options = (
                    f"① ミックス: 400m × {mix_n400}本 + 200m × {mix_n200}本<br>"
                    f"② 400mのみ: 400m × {only_n400}本<br>"
                    f"③ 200mのみ: 200m × {only_n200}本"
                )

                return {
                    "type": "Repetition (R)",
                    "summary": f"R 合計 {limit:.1f}km (選択制)",
                    "sets": menu_options,
                    "pace": f"400m: {paces['R_400']} / 200m: {paces['R_200']}",
                    "rest": f"400m後は {y_m}分{y_s:02d}秒 / 200m後は {x_m}分{x_s:02d}秒",
                    "note": f"全パターン合計で {limit:.1f}km 以内。フォームが崩れない方を優先してください。"
                }

            elif q_type == "T":
                limit = weekly_km * DanielsConstants.T_LIMIT_RATIO
                return {
                    "type": "Threshold (T)",
                    "summary": f"T持続走 {limit:.1f}km (Pace: {paces['T']})",
                    "sets": f"{limit:.1f}km 持続走",
                    "pace": f"{paces['T']} /km",
                    "rest": "なし",
                    "note": "乳酸閾値の向上。心地よいきつさを維持。"
                }

            elif q_type == "I":
                limit = min(weekly_km * DanielsConstants.I_RUN_MAX_RATIO, 10.0)
                n1000 = int(limit // 1.0)
                return {
                    "type": "Interval (I)",
                    "summary": f"I 1000m × {n1000}本",
                    "sets": f"1000m × {n1000}本",
                    "pace": f"{paces['I']} /km",
                    "rest": "走行時間と同程度",
                    "note": "VO2max向上。非常にハードなセッション。"
                }

            return {"type": "E", "summary": "E-Run", "sets": "-", "pace": paces.get("E_limit", "N/A"), "rest": "-", "note": "リカバリー"}

    def generate_weekly_schedule(self, menus, l_max):
        rule = self.schedule_rules["weekly_training_rules"]["no_weekend_race"]
        day_plan = {day: rule["default_easy_label"] for day in range(1, 8)}
        for idx, m in enumerate(menus):
            day = rule["q_day_slots"][idx]
            day_plan[day] = f"<a href='#{m['id']}' style='text-decoration:none; color:inherit;'>Q{idx+1}: {m['summary']}</a>"
        day_plan[rule["long_run_day"]] = f"L-Run: max {l_max}km"
        return [f"Day {d}: {day_plan[d]}" for d in range(1, 8)]
