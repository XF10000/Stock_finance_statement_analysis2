"""
Excel格式化输出模块
用于生成格式化的财务报表Excel文件
"""

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
from openpyxl.utils.dataframe import dataframe_to_rows
from typing import List, Optional


def save_formatted_balance_sheet(df: pd.DataFrame, filename: str, 
                                 highlight_keywords: Optional[List[str]] = None):
    """
    保存格式化的资产负债表到Excel
    
    Args:
        df: 资产负债表DataFrame
        filename: 输出文件名
        highlight_keywords: 需要高亮的关键词列表（如"小计"、"合计"等）
    """
    if highlight_keywords is None:
        highlight_keywords = ['小计', '合计', '资产总计', '负债总计', '股东权益合计', 
                             '流动资产合计', '非流动资产合计', '流动负债合计', '非流动负债合计',
                             '资产总额', '资本总额']
    
    wb = Workbook()
    ws = wb.active
    ws.title = "资产负债表"
    
    # 写入数据
    for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), 1):
        for c_idx, value in enumerate(row, 1):
            cell = ws.cell(row=r_idx, column=c_idx, value=value)
            
            # 设置对齐方式
            if c_idx == 1:
                cell.alignment = Alignment(horizontal='left', vertical='center')
            else:
                cell.alignment = Alignment(horizontal='right', vertical='center')
            
            # 表头格式
            if r_idx == 1:
                cell.font = Font(bold=True, size=11)
                cell.fill = PatternFill(start_color='D3D3D3', end_color='D3D3D3', fill_type='solid')
                cell.alignment = Alignment(horizontal='center', vertical='center')
            else:
                # 检查是否需要高亮
                first_col_value = ws.cell(row=r_idx, column=1).value
                if first_col_value and any(keyword in str(first_col_value) for keyword in highlight_keywords):
                    cell.font = Font(bold=True, size=10)
                    cell.fill = PatternFill(start_color='FFFFCC', end_color='FFFFCC', fill_type='solid')
                
                # 数字格式：千分位分隔，无小数
                if c_idx > 1 and isinstance(value, (int, float)):
                    cell.number_format = '#,##0'
    
    # 设置列宽
    from openpyxl.utils import get_column_letter
    ws.column_dimensions['A'].width = 30
    for col in range(2, len(df.columns) + 2):
        col_letter = get_column_letter(col)
        ws.column_dimensions[col_letter].width = 15
    
    # 添加边框
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
        for cell in row:
            cell.border = thin_border
    
    # 冻结首行
    ws.freeze_panes = 'A2'
    
    wb.save(filename)


def save_formatted_income_statement(df: pd.DataFrame, filename: str,
                                   highlight_keywords: Optional[List[str]] = None):
    """
    保存格式化的利润表到Excel
    
    Args:
        df: 利润表DataFrame
        filename: 输出文件名
        highlight_keywords: 需要高亮的关键词列表
    """
    if highlight_keywords is None:
        highlight_keywords = ['小计', '合计', '营业利润', '利润总额', '净利润', 
                             '综合收益总额', '归属于母公司']
    
    save_formatted_balance_sheet(df, filename, highlight_keywords)


def save_formatted_cashflow_statement(df: pd.DataFrame, filename: str,
                                     highlight_keywords: Optional[List[str]] = None):
    """
    保存格式化的现金流量表到Excel
    
    Args:
        df: 现金流量表DataFrame
        filename: 输出文件名
        highlight_keywords: 需要高亮的关键词列表
    """
    if highlight_keywords is None:
        highlight_keywords = ['小计', '合计', '经营活动现金流量净额', '投资活动现金流量净额',
                             '筹资活动现金流量净额', '现金及现金等价物净增加额']
    
    save_formatted_balance_sheet(df, filename, highlight_keywords)
