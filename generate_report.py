"""生成指定股票的核心指标分析报告（ECharts版本）"""
import sys
from final_report_generator_echarts import FinalReportGenerator


def main():
    ts_code = sys.argv[1] if len(sys.argv) > 1 else '000333.SZ'
    generator = FinalReportGenerator()
    report_path = generator.generate_report(ts_code)
    print(f"\n报告已生成: {report_path}")


if __name__ == '__main__':
    main()
