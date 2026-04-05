import json
import pandas as pd
from pathlib import Path
from datetime import timedelta


class DanielsConstants:
    """Danielsランニングフォーミュラの定数"""
    RECOVERY_MIN_MINUTES = 30
    L_RUN_MAX_RATIO = 0.30
    I_RUN_MAX_RATIO = 0.08
    R_RUN_MAX_RATIO = 0.05
    E_LIMIT_RATIO = 1.25  # Tペースの約1.25倍


class DanielsFormulaEngine:
    """Danielsランニングフォーミュラの計算エンジン"""

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
        """MM:SS または HH:MM:SS 形式をセカンドに変換"""
        parts = str(time_str).split(':')
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return int(parts[0]) * 60 + int(parts[1])

    def seconds_to_str(self, seconds):
        """秒数をMM:SS形式に変換"""
        td = timedelta(seconds=int(seconds))
        minutes, seconds = divmod(td.seconds, 60)
        return f"{minutes}:{seconds:02d}"

    def get_vdot_row(self):
        """ユーザーの基準距離・時間からVDOTテーブルの行を取得"""
        dist = self.stats["base_distance"]
        time = self.stats["base_time"]
        return self.vdot_df.loc[self.vdot_df[dist] <= time].iloc[0]

    def calculate_paces(self, v_row):
            """
            VDOTテーブルから、ダニエルズ第4版の定義に基づき正確に算出。
            T: 30-40分維持可能な心地よいきつさ (p.103)
            I: 5kmレースペース (p.119)
            R: 1500mペース付近 (p.135)
            """
            try:
                # 各レースのベストペース（秒/km）を算出
                pace_1500m_sec_per_km = self.time_to_seconds(v_row['1.5km']) / 1.5
                pace_5km_sec_per_km = self.time_to_seconds(v_row['5km']) / 5
                pace_10km_sec_per_km = self.time_to_seconds(v_row['10km']) / 10

                # 1. T-Pace: 10kmペースより約2.2%遅い (VDOT 44で4:43)
                t_pace_sec = pace_10km_sec_per_km * 1.022

                # 2. I-Pace: 5kmペースそのもの (VDOT 44で4:27)
                i_pace_sec = pace_5km_sec_per_km * 1.00

                # 3. R-Pace: 1.5kmペースの約 1.015倍（VDOT 51で400m 86秒 / 200m 43秒に一致）
                # VDOT 44の場合: (363s / 1.5) * 1.015 = 245.6s/km -> 400m 98.2s / 200m 49.1s
                # ※書籍のVDOT 44のR設定は 200m 47秒なので、1.5kmペースそのものでも良い
                r_pace_sec_per_km = pace_1500m_sec_per_km * 1.00 # ここではシンプルに1500mペースを適用
                r_400_sec = (r_pace_sec_per_km / 1000) * 400
                r_200_sec = r_400_sec / 2

                # 4. E-Pace: Tペースの約1.25倍
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
        """目標週数のトレーニングプランを生成"""
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
        """週内の日別スケジュールをルールに基づいて生成"""
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
        """Q種別に応じたメニュー詳細文字列を生成"""
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
