"""
全A股财务数据分析器

功能：
1. 计算各指标在全A股中的分位数
2. 处理异常值
3. 生成市场分布数据
4. 更新指标的分位数排名
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime
from financial_data_manager import FinancialDataManager


class FinancialDataAnalyzer:
    """全A股财务数据分析器"""
    
    def __init__(self, db_manager: FinancialDataManager):
        """
        初始化分析器
        
        Args:
            db_manager: 数据库管理器实例
        """
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
        
        # 指标列名映射
        self.indicator_columns = {
            'ar_turnover_log': '应收账款周转率对数',
            'gross_margin': '毛利率',
            'lta_turnover_log': '长期经营资产周转率对数',
            'working_capital_ratio': '净营运资本比率',
            'ocf_ratio': '经营现金流比率'
        }
    
    def calculate_market_percentiles(
        self,
        end_date: str,
        exclude_outliers: bool = True,
        outlier_std: float = 3.0
    ) -> Dict[str, Dict]:
        """
        计算指定报告期全A股各指标的分位数
        
        Args:
            end_date: 报告期
            exclude_outliers: 是否排除异常值
            outlier_std: 异常值标准差倍数
            
        Returns:
            {
                'ar_turnover_log': {
                    'count': 统计数量,
                    'mean': 均值,
                    'std': 标准差,
                    'min': 最小值,
                    'p25': 25分位数,
                    'p50': 50分位数（中位数）,
                    'p75': 75分位数,
                    'max': 最大值,
                    'outliers_removed': 移除的异常值数量
                },
                ...
            }
        """
        self.logger.info(f"计算 {end_date} 的市场分位数...")
        
        # 获取所有股票的指标数据
        conn = self.db.get_connection()
        
        query = '''
            SELECT ts_code, ar_turnover_log, gross_margin, lta_turnover_log,
                   working_capital_ratio, ocf_ratio
            FROM core_indicators
            WHERE end_date = ?
        '''
        
        df = pd.read_sql_query(query, conn, params=(end_date,))
        
        if len(df) == 0:
            self.logger.warning(f"{end_date} 没有找到任何指标数据")
            return {}
        
        self.logger.info(f"找到 {len(df)} 只股票的数据")
        
        # 计算各指标的分位数
        results = {}
        
        for col_name, cn_name in self.indicator_columns.items():
            if col_name not in df.columns:
                continue
            
            # 获取有效数据
            data = df[col_name].dropna()
            
            if len(data) == 0:
                self.logger.warning(f"{cn_name} 没有有效数据")
                continue
            
            # 处理异常值
            outliers_removed = 0
            if exclude_outliers and len(data) > 10:
                mean = data.mean()
                std = data.std()
                
                # 使用均值±N倍标准差作为异常值阈值
                lower_bound = mean - outlier_std * std
                upper_bound = mean + outlier_std * std
                
                # 过滤异常值
                data_filtered = data[(data >= lower_bound) & (data <= upper_bound)]
                outliers_removed = len(data) - len(data_filtered)
                
                if outliers_removed > 0:
                    self.logger.info(f"{cn_name}: 移除 {outliers_removed} 个异常值")
                    data = data_filtered
            
            # 计算统计指标
            results[col_name] = {
                'count': len(data),
                'mean': float(data.mean()),
                'std': float(data.std()),
                'min': float(data.min()),
                'p25': float(data.quantile(0.25)),
                'p50': float(data.quantile(0.50)),
                'p75': float(data.quantile(0.75)),
                'max': float(data.max()),
                'outliers_removed': outliers_removed
            }
            
            self.logger.info(
                f"{cn_name}: "
                f"均值={results[col_name]['mean']:.2f}, "
                f"中位数={results[col_name]['p50']:.2f}, "
                f"样本数={results[col_name]['count']}"
            )
        
        return results
    
    def update_percentile_ranks(
        self,
        end_date: str,
        market_stats: Optional[Dict[str, Dict]] = None,
        is_ttm: bool = False
    ) -> int:
        """
        更新指定报告期所有股票的分位数排名（批量优化版）
        
        Args:
            end_date: 报告期
            market_stats: 市场统计数据（已废弃，保留参数以兼容旧代码）
            is_ttm: 是否更新 TTM 指标的分位数
            
        Returns:
            更新的股票数量
        """
        ttm_label = "TTM " if is_ttm else ""
        self.logger.info(f"更新 {end_date} 的{ttm_label}分位数排名...")
        
        # 获取所有股票的指标数据
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT id, ts_code, ar_turnover_log, gross_margin, lta_turnover_log,
                   working_capital_ratio, ocf_ratio
            FROM core_indicators
            WHERE end_date = ? AND is_ttm = ?
        '''
        
        df = pd.read_sql_query(query, conn, params=(end_date, 1 if is_ttm else 0))
        
        if len(df) == 0:
            return 0
        
        # 批量计算分位数（使用 pandas rank 函数）
        indicator_cols = ['ar_turnover_log', 'gross_margin', 'lta_turnover_log',
                         'working_capital_ratio', 'ocf_ratio']
        
        # 为每个指标计算分位数
        for col in indicator_cols:
            # 使用 rank(pct=True) 计算百分位数
            df[f'{col}_percentile'] = df[col].rank(pct=True) * 100
        
        # 批量更新数据库
        update_data = []
        for _, row in df.iterrows():
            update_data.append((
                row['ar_turnover_log_percentile'],
                row['gross_margin_percentile'],
                row['lta_turnover_log_percentile'],
                row['working_capital_ratio_percentile'],
                row['ocf_ratio_percentile'],
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                row['id']
            ))
        
        # 批量更新
        cursor.executemany('''
            UPDATE core_indicators
            SET ar_turnover_log_percentile = ?,
                gross_margin_percentile = ?,
                lta_turnover_log_percentile = ?,
                working_capital_ratio_percentile = ?,
                ocf_ratio_percentile = ?,
                update_time = ?
            WHERE id = ?
        ''', update_data)
        
        conn.commit()
        
        updated_count = len(update_data)
        self.logger.info(f"成功更新 {updated_count} 只股票的分位数排名")
        
        return updated_count
    
    def save_market_distribution(
        self,
        end_date: str,
        market_stats: Dict[str, Dict]
    ):
        """
        保存市场分布数据到数据库
        
        Args:
            end_date: 报告期
            market_stats: 市场统计数据
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('BEGIN IMMEDIATE')
            
            for indicator, stats in market_stats.items():
                cursor.execute('''
                    INSERT OR REPLACE INTO market_distribution
                    (end_date, indicator_name, count, mean, median, std, min, p25, p75, max,
                     update_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    end_date,
                    indicator,
                    stats['count'],
                    stats['mean'],
                    stats['p50'],  # median
                    stats['std'],
                    stats['min'],
                    stats['p25'],
                    stats['p75'],
                    stats['max'],
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
            
            conn.commit()
            self.logger.info(f"已保存 {end_date} 的市场分布数据")
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"保存市场分布数据失败: {str(e)}")
            raise
    
    def analyze_all_periods(
        self,
        exclude_outliers: bool = True,
        outlier_std: float = 3.0
    ) -> Dict[str, int]:
        """
        分析所有报告期的市场分布
        
        Args:
            exclude_outliers: 是否排除异常值
            outlier_std: 异常值标准差倍数
            
        Returns:
            {报告期: 更新的股票数量}
        """
        self.logger.info("开始分析所有报告期...")
        
        # 获取所有有指标数据的报告期
        conn = self.db.get_connection()
        
        query = '''
            SELECT DISTINCT end_date
            FROM core_indicators
            ORDER BY end_date
        '''
        
        periods = pd.read_sql_query(query, conn)['end_date'].tolist()
        
        if len(periods) == 0:
            self.logger.warning("没有找到任何报告期")
            return {}
        
        self.logger.info(f"找到 {len(periods)} 个报告期")
        
        results = {}
        
        for period in periods:
            try:
                # 计算市场分位数
                market_stats = self.calculate_market_percentiles(
                    period,
                    exclude_outliers=exclude_outliers,
                    outlier_std=outlier_std
                )
                
                if not market_stats:
                    continue
                
                # 保存市场分布数据
                self.save_market_distribution(period, market_stats)
                
                # 更新分位数排名
                updated_count = self.update_percentile_ranks(period, market_stats)
                
                results[period] = updated_count
                
            except Exception as e:
                self.logger.error(f"分析 {period} 失败: {str(e)}")
                continue
        
        self.logger.info(f"完成所有报告期分析，共处理 {len(results)} 个报告期")
        
        return results
    
    def get_stock_percentile_history(
        self,
        ts_code: str
    ) -> pd.DataFrame:
        """
        获取指定股票的历史分位数排名
        
        Args:
            ts_code: 股票代码
            
        Returns:
            包含历史分位数的DataFrame
        """
        conn = self.db.get_connection()
        
        query = '''
            SELECT end_date,
                   ar_turnover_log, ar_turnover_log_percentile,
                   gross_margin, gross_margin_percentile,
                   lta_turnover_log, lta_turnover_log_percentile,
                   working_capital_ratio, working_capital_ratio_percentile,
                   ocf_ratio, ocf_ratio_percentile
            FROM core_indicators
            WHERE ts_code = ?
            ORDER BY end_date
        '''
        
        df = pd.read_sql_query(query, conn, params=(ts_code,))
        
        return df
    
    def get_market_distribution_history(
        self,
        indicator: str
    ) -> pd.DataFrame:
        """
        获取指定指标的历史市场分布
        
        Args:
            indicator: 指标名称
            
        Returns:
            包含历史分布数据的DataFrame
        """
        conn = self.db.get_connection()
        
        query = '''
            SELECT end_date, count, mean, median as p50, std, min, p25, p75, max
            FROM market_distribution
            WHERE indicator_name = ?
            ORDER BY end_date
        '''
        
        df = pd.read_sql_query(query, conn, params=(indicator,))
        
        return df
