#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
退休计算器 - 完整版本
包含社保缴纳年限、退休时间等详细计算
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
import os

class RetirementCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("退休计算器")
        self.root.geometry("800x600")
        
        # 设置样式
        style = ttk.Style()
        style.theme_use('clam')
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置用户界面"""
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 标题
        title_label = ttk.Label(main_frame, text="🏖️ 退休计算器", 
                               font=("Arial", 18, "bold"))
        title_label.grid(row=0, column=0, columnspan=4, pady=(0, 20))
        
        # 输入区域
        input_frame = ttk.LabelFrame(main_frame, text="基本信息", padding="15")
        input_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # 出生日期
        ttk.Label(input_frame, text="出生日期:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.birth_year = tk.StringVar(value="1990")
        self.birth_month = tk.StringVar(value="1")
        self.birth_day = tk.StringVar(value="1")
        
        ttk.Entry(input_frame, textvariable=self.birth_year, width=6).grid(row=0, column=1, padx=2)
        ttk.Label(input_frame, text="年").grid(row=0, column=2, padx=2)
        ttk.Entry(input_frame, textvariable=self.birth_month, width=4).grid(row=0, column=3, padx=2)
        ttk.Label(input_frame, text="月").grid(row=0, column=4, padx=2)
        ttk.Entry(input_frame, textvariable=self.birth_day, width=4).grid(row=0, column=5, padx=2)
        ttk.Label(input_frame, text="日").grid(row=0, column=6, padx=2)
        
        # 性别
        ttk.Label(input_frame, text="性别:").grid(row=1, column=0, sticky=tk.W, pady=(10, 0), padx=(0, 10))
        self.gender = tk.StringVar(value="男")
        gender_frame = ttk.Frame(input_frame)
        gender_frame.grid(row=1, column=1, columnspan=3, sticky=tk.W, pady=(10, 0))
        ttk.Radiobutton(gender_frame, text="男", variable=self.gender, value="男").pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(gender_frame, text="女", variable=self.gender, value="女").pack(side=tk.LEFT)
        
        # 工作开始时间
        ttk.Label(input_frame, text="工作开始时间:").grid(row=2, column=0, sticky=tk.W, pady=(10, 0), padx=(0, 10))
        self.work_start_year = tk.StringVar(value="2012")
        self.work_start_month = tk.StringVar(value="1")
        ttk.Entry(input_frame, textvariable=self.work_start_year, width=6).grid(row=2, column=1, pady=(10, 0), padx=2)
        ttk.Label(input_frame, text="年").grid(row=2, column=2, pady=(10, 0), padx=2)
        ttk.Entry(input_frame, textvariable=self.work_start_month, width=4).grid(row=2, column=3, pady=(10, 0), padx=2)
        ttk.Label(input_frame, text="月").grid(row=2, column=4, pady=(10, 0), padx=2)
        
        # 社保开始缴纳时间
        ttk.Label(input_frame, text="社保开始时间:").grid(row=3, column=0, sticky=tk.W, pady=(10, 0), padx=(0, 10))
        self.social_start_year = tk.StringVar(value="2012")
        self.social_start_month = tk.StringVar(value="1")
        ttk.Entry(input_frame, textvariable=self.social_start_year, width=6).grid(row=3, column=1, pady=(10, 0), padx=2)
        ttk.Label(input_frame, text="年").grid(row=3, column=2, pady=(10, 0), padx=2)
        ttk.Entry(input_frame, textvariable=self.social_start_month, width=4).grid(row=3, column=3, pady=(10, 0), padx=2)
        ttk.Label(input_frame, text="月").grid(row=3, column=4, pady=(10, 0), padx=2)
        
        # 是否有中断缴费
        ttk.Label(input_frame, text="缴费中断:").grid(row=4, column=0, sticky=tk.W, pady=(10, 0), padx=(0, 10))
        self.has_interruption = tk.BooleanVar(value=False)
        ttk.Checkbutton(input_frame, text="有中断缴费", variable=self.has_interruption, 
                       command=self.toggle_interruption).grid(row=4, column=1, columnspan=2, sticky=tk.W, pady=(10, 0))
        
        # 中断时间输入框（默认隐藏）
        self.interruption_frame = ttk.Frame(input_frame)
        self.interruption_frame.grid(row=5, column=0, columnspan=7, sticky=(tk.W, tk.E), pady=(10, 0))
        
        ttk.Label(self.interruption_frame, text="中断月数:").pack(side=tk.LEFT, padx=(0, 10))
        self.interruption_months = tk.StringVar(value="0")
        ttk.Entry(self.interruption_frame, textvariable=self.interruption_months, width=6).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(self.interruption_frame, text="个月").pack(side=tk.LEFT)
        
        # 初始隐藏中断输入框
        self.interruption_frame.grid_remove()
        
        # 计算按钮
        calc_button = ttk.Button(input_frame, text="🧮 计算退休时间", command=self.calculate)
        calc_button.grid(row=6, column=0, columnspan=7, pady=(20, 0))
        
        # 结果显示区域
        result_frame = ttk.LabelFrame(main_frame, text="计算结果", padding="15")
        result_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 20))
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        
        # 结果文本框
        self.result_text = tk.Text(result_frame, height=15, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=scrollbar.set)
        
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 保存按钮
        save_button = ttk.Button(main_frame, text="💾 保存结果", command=self.save_results)
        save_button.grid(row=3, column=0, columnspan=4)
        
        # 配置权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
    
    def toggle_interruption(self):
        """切换中断缴费输入框的显示/隐藏"""
        if self.has_interruption.get():
            self.interruption_frame.grid()
        else:
            self.interruption_frame.grid_remove()
    
    def calculate(self):
        """计算退休时间和社保详情"""
        try:
            # 获取输入数据
            birth_year = int(self.birth_year.get())
            birth_month = int(self.birth_month.get())
            birth_day = int(self.birth_day.get())
            gender = self.gender.get()
            work_start_year = int(self.work_start_year.get())
            work_start_month = int(self.work_start_month.get())
            social_start_year = int(self.social_start_year.get())
            social_start_month = int(self.social_start_month.get())
            interruption_months = int(self.interruption_months.get()) if self.has_interruption.get() else 0
            
            # 计算关键日期
            birth_date = date(birth_year, birth_month, birth_day)
            work_start_date = date(work_start_year, work_start_month, 1)
            social_start_date = date(social_start_year, social_start_month, 1)
            today = date.today()
            
            # 计算当前年龄
            current_age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            
            # 退休年龄规则
            if gender == "男":
                retirement_age = 60
            else:
                retirement_age = 55
            
            # 计算退休日期
            retirement_date = date(birth_year + retirement_age, birth_month, birth_day)
            
            # 计算工作时间
            work_months_total = self._calculate_months_between(work_start_date, min(today, retirement_date))
            work_years_total = work_months_total / 12
            
            # 计算社保缴纳时间
            social_months_paid = self._calculate_months_between(social_start_date, min(today, retirement_date)) - interruption_months
            social_years_paid = social_months_paid / 12
            
            # 计算到退休还需缴纳的社保
            if today < retirement_date:
                remaining_months = self._calculate_months_between(today, retirement_date)
                remaining_years = remaining_months / 12
                
                # 到退休时的总社保缴费年限
                total_social_months_at_retirement = social_months_paid + remaining_months
                total_social_years_at_retirement = total_social_months_at_retirement / 12
            else:
                remaining_months = 0
                remaining_years = 0
                total_social_months_at_retirement = social_months_paid
                total_social_years_at_retirement = social_years_paid
            
            # 计算距离退休时间
            if today <= retirement_date:
                days_to_retirement = (retirement_date - today).days
                years_to_retirement = days_to_retirement / 365.25
                retirement_status = "未退休"
            else:
                days_to_retirement = 0
                years_to_retirement = 0
                retirement_status = "已退休"
            
            # 社保缴费状态评估
            min_social_years = 15  # 最低缴费年限
            social_status = "符合条件" if total_social_years_at_retirement >= min_social_years else "不足15年"
            
            # 生成详细结果
            result = f"""
🏖️ 退休计算详细结果
{'='*60}

📅 基本信息:
   出生日期: {birth_date.strftime('%Y年%m月%d日')}
   性别: {gender}
   当前年龄: {current_age}岁
   退休状态: {retirement_status}

💼 工作信息:
   工作开始时间: {work_start_date.strftime('%Y年%m月')}
   已工作时间: {work_years_total:.1f}年 ({work_months_total}个月)
   
📋 社保缴纳详情:
   社保开始时间: {social_start_date.strftime('%Y年%m月')}
   已缴纳时间: {social_years_paid:.1f}年 ({social_months_paid}个月)
   中断缴费: {interruption_months}个月
   
🎯 退休信息:
   法定退休年龄: {retirement_age}岁
   退休日期: {retirement_date.strftime('%Y年%m月%d日')}
"""

            if today <= retirement_date:
                result += f"""   
⏰ 距离退休:
   还有: {days_to_retirement}天 ({years_to_retirement:.1f}年)
   还需缴费: {remaining_months}个月 ({remaining_years:.1f}年)
   
📊 退休时预计:
   总工作年限: {(work_months_total + remaining_months)/12:.1f}年
   总社保缴费: {total_social_years_at_retirement:.1f}年 ({total_social_months_at_retirement}个月)
"""
            else:
                result += f"""
   已退休: {(today - retirement_date).days}天
   
📊 退休时实际:
   总工作年限: {work_years_total:.1f}年
   总社保缴费: {social_years_paid:.1f}年 ({social_months_paid}个月)
"""

            result += f"""
✅ 社保状态评估:
   最低缴费要求: {min_social_years}年
   当前状态: {social_status}
   {"✅ 符合退休条件" if total_social_years_at_retirement >= min_social_years else "❌ 需继续缴费"}
"""

            if total_social_years_at_retirement < min_social_years:
                shortage_months = (min_social_years * 12) - total_social_months_at_retirement
                result += f"""
⚠️  缴费不足提醒:
   还需缴费: {shortage_months:.0f}个月 ({shortage_months/12:.1f}年)
   建议延长缴费至符合条件
"""

            result += f"""
💡 重要提醒:
   • 社保缴费满15年是享受养老金的最低条件
   • 缴费年限越长，退休待遇越高
   • 如有中断缴费，可考虑补缴
   • 请关注社保政策变化

📈 工作进度:
   工作完成度: {min(100, (work_months_total / ((retirement_age - (work_start_year - birth_year)) * 12)) * 100):.1f}%
   社保进度: {min(100, (social_months_paid / (min_social_years * 12)) * 100):.1f}%

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            # 显示结果
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, result)
            
        except ValueError as e:
            messagebox.showerror("错误", "请输入正确的数字")
        except Exception as e:
            messagebox.showerror("错误", f"计算出错: {str(e)}")
    
    def _calculate_months_between(self, start_date, end_date):
        """计算两个日期之间的月份数"""
        if end_date <= start_date:
            return 0
        
        months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
        return months
    
    def save_results(self):
        """保存结果"""
        try:
            content = self.result_text.get(1.0, tk.END)
            if not content.strip():
                messagebox.showwarning("警告", "没有结果可保存")
                return
            
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"退休计算结果_{timestamp}.txt"
            
            # 保存文件
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            messagebox.showinfo("成功", f"结果已保存到: {filename}")
            
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")

def main():
    root = tk.Tk()
    app = RetirementCalculator(root)
    root.mainloop()

if __name__ == "__main__":
    main()
