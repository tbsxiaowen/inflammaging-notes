#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
退休计算器 - 2025延迟退休新政版
支持2025年1月1日起实施的渐进式延迟退休政策

政策依据：国发〔2024〕30号
- 男职工：原60岁，每4个月延迟1个月，最终延迟至63岁
- 女干部/技术人员：原55岁，每4个月延迟1个月，最终延迟至58岁
- 女工人：原50岁，每2个月延迟1个月，最终延迟至55岁
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
import calendar
import os


def add_months(d, months):
    """给日期加上指定月数，处理月末溢出"""
    total = d.year * 12 + d.month - 1 + months
    year = total // 12
    month = total % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


# 延迟退休政策参数
POLICY_START = date(2025, 1, 1)
POLICY_RULES = {
    "男":      {"original_age": 60, "interval": 4, "max_delay": 36, "target_age": 63},
    "女干部55": {"original_age": 55, "interval": 4, "max_delay": 36, "target_age": 58},
    "女工人50": {"original_age": 50, "interval": 2, "max_delay": 60, "target_age": 55},
}


def calc_delayed_retirement(birth_date, policy_key):
    """
    根据渐进式延迟退休政策计算退休日期。

    算法：
    1. 计算原法定退休日期（出生日期 + 原退休年龄）
    2. 计算该日期距政策起始日（2025-01）的月数 N
    3. 延迟月数 = min(最大延迟, N // 间隔 + 1)，若 N < 0 则无延迟
    4. 实际退休日期 = 原退休日期 + 延迟月数
    """
    rule = POLICY_RULES[policy_key]
    original_age = rule["original_age"]
    interval = rule["interval"]
    max_delay = rule["max_delay"]

    orig_ret_year = birth_date.year + original_age
    orig_ret_month = birth_date.month
    orig_ret_day = min(birth_date.day, calendar.monthrange(orig_ret_year, orig_ret_month)[1])
    original_retirement_date = date(orig_ret_year, orig_ret_month, orig_ret_day)

    months_after_policy = (
        (original_retirement_date.year - POLICY_START.year) * 12
        + (original_retirement_date.month - POLICY_START.month)
    )

    if months_after_policy < 0:
        delay_months = 0
    else:
        delay_months = min(max_delay, months_after_policy // interval + 1)

    actual_retirement_date = add_months(original_retirement_date, delay_months)

    age_years = actual_retirement_date.year - birth_date.year
    age_months = actual_retirement_date.month - birth_date.month
    if actual_retirement_date.day < birth_date.day:
        age_months -= 1
    if age_months < 0:
        age_years -= 1
        age_months += 12

    return {
        "original_age": original_age,
        "delay_months": delay_months,
        "retirement_date": actual_retirement_date,
        "original_retirement_date": original_retirement_date,
        "age_years": age_years,
        "age_months": age_months,
    }


class RetirementCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("退休计算器 (2025新政版)")
        self.root.geometry("850x700")
        self.root.minsize(800, 650)

        style = ttk.Style()
        style.theme_use("clam")

        self._build_ui()

    # ────────────────── UI ──────────────────

    def _build_ui(self):
        main = ttk.Frame(self.root, padding="20")
        main.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(2, weight=1)

        ttk.Label(main, text="退休计算器 (2025延迟退休新政)",
                  font=("Arial", 18, "bold")).grid(row=0, column=0, pady=(0, 20))

        self._build_input(main)
        self._build_result(main)

        ttk.Button(main, text="💾 保存结果", command=self._save).grid(row=3, column=0, pady=(5, 0))

    def _build_input(self, parent):
        f = ttk.LabelFrame(parent, text="基本信息", padding="15")
        f.grid(row=1, column=0, sticky="ew", pady=(0, 15))

        # 出生日期
        r = 0
        ttk.Label(f, text="出生日期:").grid(row=r, column=0, sticky="w", padx=(0, 10))
        self.birth_year = tk.StringVar(value="1990")
        self.birth_month = tk.StringVar(value="1")
        self.birth_day = tk.StringVar(value="1")
        ttk.Entry(f, textvariable=self.birth_year, width=6).grid(row=r, column=1, padx=2)
        ttk.Label(f, text="年").grid(row=r, column=2, padx=2)
        ttk.Entry(f, textvariable=self.birth_month, width=4).grid(row=r, column=3, padx=2)
        ttk.Label(f, text="月").grid(row=r, column=4, padx=2)
        ttk.Entry(f, textvariable=self.birth_day, width=4).grid(row=r, column=5, padx=2)
        ttk.Label(f, text="日").grid(row=r, column=6, padx=2)

        # 性别
        r = 1
        ttk.Label(f, text="性别:").grid(row=r, column=0, sticky="w", pady=(10, 0), padx=(0, 10))
        self.gender = tk.StringVar(value="男")
        gf = ttk.Frame(f)
        gf.grid(row=r, column=1, columnspan=6, sticky="w", pady=(10, 0))
        ttk.Radiobutton(gf, text="男", variable=self.gender, value="男",
                        command=self._on_gender).pack(side="left", padx=(0, 20))
        ttk.Radiobutton(gf, text="女", variable=self.gender, value="女",
                        command=self._on_gender).pack(side="left")

        # 女性退休类型（默认隐藏）
        r = 2
        self._female_frame = ttk.Frame(f)
        self._female_frame.grid(row=r, column=0, columnspan=7, sticky="w", pady=(10, 0))
        ttk.Label(self._female_frame, text="退休类型:").pack(side="left", padx=(0, 10))
        self.female_type = tk.StringVar(value="女工人(原50岁退休)")
        ttk.Radiobutton(self._female_frame, text="女工人 (原50岁退休)",
                        variable=self.female_type,
                        value="女工人(原50岁退休)").pack(side="left", padx=(0, 15))
        ttk.Radiobutton(self._female_frame, text="女干部/技术人员 (原55岁退休)",
                        variable=self.female_type,
                        value="女干部(原55岁退休)").pack(side="left")
        self._female_frame.grid_remove()

        # 工作开始时间
        r = 3
        ttk.Label(f, text="工作开始时间:").grid(row=r, column=0, sticky="w", pady=(10, 0), padx=(0, 10))
        self.work_start_year = tk.StringVar(value="2012")
        self.work_start_month = tk.StringVar(value="1")
        ttk.Entry(f, textvariable=self.work_start_year, width=6).grid(row=r, column=1, pady=(10, 0), padx=2)
        ttk.Label(f, text="年").grid(row=r, column=2, pady=(10, 0), padx=2)
        ttk.Entry(f, textvariable=self.work_start_month, width=4).grid(row=r, column=3, pady=(10, 0), padx=2)
        ttk.Label(f, text="月").grid(row=r, column=4, pady=(10, 0), padx=2)

        # 社保开始时间
        r = 4
        ttk.Label(f, text="社保开始时间:").grid(row=r, column=0, sticky="w", pady=(10, 0), padx=(0, 10))
        self.social_start_year = tk.StringVar(value="2012")
        self.social_start_month = tk.StringVar(value="1")
        ttk.Entry(f, textvariable=self.social_start_year, width=6).grid(row=r, column=1, pady=(10, 0), padx=2)
        ttk.Label(f, text="年").grid(row=r, column=2, pady=(10, 0), padx=2)
        ttk.Entry(f, textvariable=self.social_start_month, width=4).grid(row=r, column=3, pady=(10, 0), padx=2)
        ttk.Label(f, text="月").grid(row=r, column=4, pady=(10, 0), padx=2)

        # 缴费中断
        r = 5
        ttk.Label(f, text="缴费中断:").grid(row=r, column=0, sticky="w", pady=(10, 0), padx=(0, 10))
        self.has_interruption = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="有中断缴费", variable=self.has_interruption,
                        command=self._toggle_interruption).grid(
            row=r, column=1, columnspan=2, sticky="w", pady=(10, 0))

        r = 6
        self._inter_frame = ttk.Frame(f)
        self._inter_frame.grid(row=r, column=0, columnspan=7, sticky="ew", pady=(10, 0))
        ttk.Label(self._inter_frame, text="中断月数:").pack(side="left", padx=(0, 10))
        self.interruption_months = tk.StringVar(value="0")
        ttk.Entry(self._inter_frame, textvariable=self.interruption_months, width=6).pack(side="left", padx=(0, 5))
        ttk.Label(self._inter_frame, text="个月").pack(side="left")
        self._inter_frame.grid_remove()

        # 计算按钮
        ttk.Button(f, text="🧮 计算退休时间", command=self._calculate).grid(
            row=7, column=0, columnspan=7, pady=(20, 0))

    def _build_result(self, parent):
        rf = ttk.LabelFrame(parent, text="计算结果", padding="15")
        rf.grid(row=2, column=0, sticky="nsew", pady=(0, 15))
        rf.columnconfigure(0, weight=1)
        rf.rowconfigure(0, weight=1)

        self.result_text = tk.Text(rf, height=15, wrap=tk.WORD, font=("Menlo", 12))
        sb = ttk.Scrollbar(rf, orient="vertical", command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=sb.set)
        self.result_text.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")

    # ────────────────── 事件 ──────────────────

    def _on_gender(self):
        if self.gender.get() == "女":
            self._female_frame.grid()
        else:
            self._female_frame.grid_remove()

    def _toggle_interruption(self):
        if self.has_interruption.get():
            self._inter_frame.grid()
        else:
            self._inter_frame.grid_remove()

    # ────────────────── 核心计算 ──────────────────

    def _policy_key(self):
        if self.gender.get() == "男":
            return "男"
        if self.female_type.get() == "女干部(原55岁退休)":
            return "女干部55"
        return "女工人50"

    @staticmethod
    def _months_between(d1, d2):
        if d2 <= d1:
            return 0
        return (d2.year - d1.year) * 12 + (d2.month - d1.month)

    def _calculate(self):
        try:
            birth_date = date(
                int(self.birth_year.get()),
                int(self.birth_month.get()),
                int(self.birth_day.get()),
            )
            work_start = date(int(self.work_start_year.get()), int(self.work_start_month.get()), 1)
            social_start = date(int(self.social_start_year.get()), int(self.social_start_month.get()), 1)
            gap = int(self.interruption_months.get()) if self.has_interruption.get() else 0
            today = date.today()

            current_age = today.year - birth_date.year - (
                (today.month, today.day) < (birth_date.month, birth_date.day)
            )

            ret = calc_delayed_retirement(birth_date, self._policy_key())
            ret_date = ret["retirement_date"]

            work_months = self._months_between(work_start, min(today, ret_date))
            social_paid = self._months_between(social_start, min(today, ret_date)) - gap

            remaining = self._months_between(today, ret_date) if today < ret_date else 0
            total_social = social_paid + remaining
            min_years = 15

            age_str = f"{ret['age_years']}岁"
            if ret["age_months"] > 0:
                age_str += f"{ret['age_months']}个月"

            if self.gender.get() == "男":
                type_label = "男职工"
            elif self._policy_key() == "女干部55":
                type_label = "女干部/技术人员"
            else:
                type_label = "女工人"

            lines = [
                f"退休计算详细结果 (2025延迟退休新政)",
                "=" * 55,
                "",
                "【基本信息】",
                f"  出生日期:     {birth_date.strftime('%Y年%m月%d日')}",
                f"  性别:         {self.gender.get()} ({type_label})",
                f"  当前年龄:     {current_age}岁",
                "",
                "【延迟退休政策计算】",
                f"  原法定退休年龄: {ret['original_age']}岁",
                f"  原退休日期:     {ret['original_retirement_date'].strftime('%Y年%m月%d日')}",
                f"  政策延迟:       {ret['delay_months']}个月",
                f"  实际退休年龄:   {age_str}",
                f"  实际退休日期:   {ret_date.strftime('%Y年%m月%d日')}",
                "",
                "【工作与社保】",
                f"  工作开始:   {work_start.strftime('%Y年%m月')}",
                f"  已工作:     {work_months / 12:.1f}年 ({work_months}个月)",
                f"  社保开始:   {social_start.strftime('%Y年%m月')}",
                f"  已缴社保:   {social_paid / 12:.1f}年 ({social_paid}个月)",
                f"  中断缴费:   {gap}个月",
            ]

            if today <= ret_date:
                days_left = (ret_date - today).days
                lines += [
                    "",
                    "【距离退休】",
                    f"  剩余天数:       {days_left}天 ({days_left / 365.25:.1f}年)",
                    f"  还需缴费:       {remaining}个月 ({remaining / 12:.1f}年)",
                    "",
                    "【退休时预计】",
                    f"  总工作年限:     {(work_months + remaining) / 12:.1f}年",
                    f"  总社保缴费:     {total_social / 12:.1f}年 ({total_social}个月)",
                ]
            else:
                days_past = (today - ret_date).days
                lines += [
                    "",
                    f"  已退休:         {days_past}天",
                    "",
                    "【退休时实际】",
                    f"  总工作年限:     {work_months / 12:.1f}年",
                    f"  总社保缴费:     {social_paid / 12:.1f}年 ({social_paid}个月)",
                ]

            ok = total_social / 12 >= min_years
            lines += [
                "",
                "【社保状态评估】",
                f"  最低缴费要求:   {min_years}年",
                f"  预计总缴费:     {total_social / 12:.1f}年",
                f"  状态:           {'✅ 符合退休条件' if ok else '❌ 不足15年，需继续缴费'}",
            ]

            if not ok:
                shortage = min_years * 12 - total_social
                lines += [
                    f"  还需缴费:       {shortage:.0f}个月 ({shortage / 12:.1f}年)",
                ]

            lines += [
                "",
                "【政策说明】",
                "  依据: 国发〔2024〕30号 (2025年1月1日起实施)",
                "  • 男职工:       原60岁，每4个月延迟1个月 → 最终63岁",
                "  • 女干部/技术:  原55岁，每4个月延迟1个月 → 最终58岁",
                "  • 女工人:       原50岁，每2个月延迟1个月 → 最终55岁",
                "  • 社保缴费满15年是领取养老金的最低条件",
                "",
                f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ]

            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, "\n".join(lines))

        except ValueError:
            messagebox.showerror("输入错误", "请检查日期和数字是否填写正确")
        except Exception as e:
            messagebox.showerror("计算出错", str(e))

    # ────────────────── 保存 ──────────────────

    def _save(self):
        content = self.result_text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("提示", "没有结果可保存")
            return
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(script_dir, f"退休计算结果_{ts}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("成功", f"已保存到:\n{path}")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))


def main():
    root = tk.Tk()
    RetirementCalculator(root)
    root.mainloop()


if __name__ == "__main__":
    main()
