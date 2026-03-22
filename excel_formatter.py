"""
Excel格式化输出模块
用于生成格式化的财务报表Excel文件
"""

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.utils import get_column_letter
from typing import List, Optional


# 比率类型项目的关键词列表（这些项目的值将显示为百分比格式）
RATIO_KEYWORDS = [
    '率', '比例', '占比',
    '营业成本率',
    '毛利率',
    '销售费用率',
    '管理费用率',
    '研发费用率',
    '资产减值损失率',
    '营业外收支及其他占营业收入的比例',
    '息税前经营利润率',
    '实际所得税税率',
    '口径一收入现金含量',
    '成本费用付现率',
    '净利润现金含量',
    '非付现成本费用比经营活动产生的现金流量净额',
    '长期经营资产扩张性资本支出比例',
    '扩张性资本支出占长期资产期初净额的比例',
    '现金含量',
    '付现率',
    '营业收入占比',
    '费用率',
    '损失率',
    '税率',
    '利润率',
    '周转率',
]


def is_ratio_item(item_name: str) -> bool:
    """
    判断项目名称是否为比率类型
    
    Args:
        item_name: 项目名称
        
    Returns:
        是否为比率类型
    """
    if not item_name:
        return False
    item_name = str(item_name)
    return any(keyword in item_name for keyword in RATIO_KEYWORDS)


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
        # 获取第一列的值（项目名称）
        item_name = row[0] if len(row) > 0 else None
        is_ratio = is_ratio_item(item_name) if r_idx > 1 else False
        
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
                if item_name and any(keyword in str(item_name) for keyword in highlight_keywords):
                    cell.font = Font(bold=True, size=10)
                    cell.fill = PatternFill(start_color='FFFFCC', end_color='FFFFCC', fill_type='solid')
                
                # 数字格式
                if c_idx > 1 and isinstance(value, (int, float)):
                    if is_ratio:
                        # 比率类型：显示为百分比，1位小数
                        cell.number_format = '0.0%'
                    else:
                        # 金额类型：千分位分隔，无小数
                        cell.number_format = '#,##0'
    
    # 设置列宽
    ws.column_dimensions['A'].width = 35
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
