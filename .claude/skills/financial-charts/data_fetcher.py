"""
A 股财报数据获取模块 - Data Fetcher for A-Share Financial Reports
主方案：Baostock（自有服务器，稳定可靠）
次方案：akshare（降级备选）
"""

import sys
import json
import argparse
import os
import time

# ========== 缓存配置 ==========
_CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")
_STOCK_CACHE_FILE = os.path.join(_CACHE_DIR, "stock_basic.json")
_CACHE_TTL = 86400  # 1 天


def _ensure_cache_dir():
    os.makedirs(_CACHE_DIR, exist_ok=True)


def _yuan_to_yi(val):
    """将元转换为亿元"""
    if val is None or val == '' or val == '-':
        return 0.0
    try:
        return round(float(val) / 1e8, 2)
    except (ValueError, TypeError):
        return 0.0


def _pct(val):
    """转换为百分比（保留2位）"""
    if val is None or val == '' or val == '-':
        return 0.0
    try:
        return round(float(val) * 100, 2)
    except (ValueError, TypeError):
        return 0.0


def _safe_float(val, default=0.0):
    if val is None or val == '' or val == '-':
        return default
    try:
        return round(float(val), 4)
    except (ValueError, TypeError):
        return default


# ========== 代码格式转换 ==========

def _to_baostock_code(code):
    """纯数字代码 → baostock 格式（sh.600519 / sz.000858）"""
    code = str(code).strip()
    if '.' in code:
        return code
    if code.startswith('6') or code.startswith('9'):
        return f'sh.{code}'
    return f'sz.{code}'


def _strip_code(bs_code):
    """baostock 格式 → 纯数字"""
    return bs_code.split('.')[-1] if '.' in str(bs_code) else str(bs_code)


# ========== Baostock 主方案 ==========

def _bs_login():
    import baostock as bs
    import io
    # Suppress baostock login/logout print output
    _old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        lg = bs.login()
    finally:
        sys.stdout = _old_stdout
    if lg.error_code != '0':
        raise RuntimeError(f"Baostock login failed: {lg.error_msg}")
    return bs


def _bs_logout(bs):
    import io
    _old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        bs.logout()
    except Exception:
        pass
    finally:
        sys.stdout = _old_stdout


def _load_stock_cache():
    """加载本地股票列表缓存"""
    if not os.path.exists(_STOCK_CACHE_FILE):
        return None
    try:
        with open(_STOCK_CACHE_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        if time.time() - cache.get('ts', 0) < _CACHE_TTL:
            return cache.get('data', [])
    except Exception:
        pass
    return None


def _save_stock_cache(data):
    """保存股票列表缓存"""
    _ensure_cache_dir()
    try:
        with open(_STOCK_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump({'ts': time.time(), 'data': data}, f, ensure_ascii=False)
    except Exception:
        pass


def _search_baostock(keyword):
    """Baostock 搜索股票"""
    stocks = _load_stock_cache()
    if stocks is None:
        import baostock as bs
        import pandas as pd
        bs = _bs_login()
        try:
            rs = bs.query_stock_basic()
            df = pd.DataFrame(rs.get_data())
            stocks = []
            for _, row in df.iterrows():
                stocks.append({
                    'code': _strip_code(row['code']),
                    'name': row['code_name'],
                    'bs_code': row['code'],
                    'type': str(row.get('type', '')),
                })
            _save_stock_cache(stocks)
        finally:
            _bs_logout(bs)

    # Filter: only type=1 (stock), match keyword in name
    results = [s for s in stocks if keyword in s['name'] and s.get('type', '1') == '1']
    return results[:10]


def _get_baostock_data(code, years=5):
    """Baostock 获取财务数据"""
    import baostock as bs
    import pandas as pd

    bs_code = _to_baostock_code(code)
    bs = _bs_login()

    try:
        result = {
            'code': _strip_code(code),
            'company': '',
            'source': 'baostock',
            'years': [],
            'revenue': [],
            'net_profit': [],
            'gross_margin': [],
            'roe': [],
            'np_margin': [],
            'eps': [],
            'revenue_yoy': [],
            'profit_yoy': [],
            # 季度数据
            'quarters': [],
            'q_revenue': [],
            'q_gross_margin': [],
            'q_net_profit': [],
        }

        # 获取公司名 (prefer type=1 stocks, not indices/ETFs)
        stocks = _load_stock_cache()
        if stocks:
            matches = [s for s in stocks if s['code'] == _strip_code(code)]
            # Prefer type=1 (actual stock) over index/ETF
            stock_matches = [s for s in matches if s.get('type', '1') == '1']
            if stock_matches:
                result['company'] = stock_matches[0]['name']
            elif matches:
                result['company'] = matches[0]['name']

        # 盈利能力（多年年报）
        profit_rows = []
        growth_rows = []
        for y in range(2025, 2004, -1):
            rs = bs.query_profit_data(code=bs_code, year=y, quarter=4)
            while rs.next():
                row = rs.get_row_data()
                if row and _safe_float(row[3]) != 0:  # roeAvg 非空
                    profit_rows.append(dict(zip(rs.fields, row)))

            rs = bs.query_growth_data(code=bs_code, year=y, quarter=4)
            while rs.next():
                row = rs.get_row_data()
                if row and _safe_float(row[3]) != 0:
                    growth_rows.append(dict(zip(rs.fields, row)))

            if len(profit_rows) >= years:
                break

        # 按年份排序（旧→新）
        profit_rows.sort(key=lambda r: r.get('statDate', ''))
        growth_rows.sort(key=lambda r: r.get('statDate', ''))

        for row in profit_rows[-years:]:
            year = str(row.get('statDate', ''))[:4]
            if year:
                result['years'].append(year)
                result['revenue'].append(_yuan_to_yi(row.get('MBRevenue', 0)))
                result['net_profit'].append(_yuan_to_yi(row.get('netProfit', 0)))
                result['gross_margin'].append(_pct(row.get('gpMargin', 0)))
                result['roe'].append(_pct(row.get('roeAvg', 0)))
                result['np_margin'].append(_pct(row.get('npMargin', 0)))
                result['eps'].append(_safe_float(row.get('epsTTM', 0)))

        # 成长能力
        growth_map = {}
        for row in growth_rows:
            y = str(row.get('statDate', ''))[:4]
            if y:
                growth_map[y] = row

        result['revenue_yoy'] = []
        result['profit_yoy'] = []
        for y in result['years']:
            g = growth_map.get(y, {})
            result['revenue_yoy'].append(_pct(g.get('YOYNI', 0)))
            result['profit_yoy'].append(_pct(g.get('YOYPNI', 0)))

        # 季度数据（最近4个季度）
        base_year = int(result['years'][-1]) if result['years'] else 2024
        q_rows = []
        for y in range(base_year, base_year - 2, -1):
            for q in range(4, 0, -1):
                rs = bs.query_profit_data(code=bs_code, year=y, quarter=q)
                while rs.next():
                    row = rs.get_row_data()
                    if row:
                        q_rows.append(dict(zip(rs.fields, row)))

        # 取最近 4 条，按时间排序
        q_rows.sort(key=lambda r: r.get('statDate', ''))
        q_rows = q_rows[-4:]

        for row in q_rows:
            label = str(row.get('statDate', ''))
            if label:
                q_label = label[:7].replace('-12', ' Q4').replace('-09', ' Q3').replace('-06', ' Q2').replace('-03', ' Q1')
                result['quarters'].append(q_label)
                result['q_revenue'].append(_yuan_to_yi(row.get('MBRevenue', 0)))
                result['q_gross_margin'].append(_pct(row.get('gpMargin', 0)))
                result['q_net_profit'].append(_yuan_to_yi(row.get('netProfit', 0)))

        return result

    finally:
        _bs_logout(bs)


def _get_baostock_peer(codes, years=5):
    """Baostock 获取多家公司对比数据"""
    results = {}
    for code in codes:
        data = _get_baostock_data(code, years)
        if data['company']:
            results[data['company']] = data
    return results


def _get_baostock_kline(code, start_date, end_date, frequency='d'):
    """Baostock K线数据"""
    import baostock as bs
    import pandas as pd

    bs_code = _to_baostock_code(code)
    bs = _bs_login()
    try:
        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,open,high,low,close,volume,amount",
            start_date=start_date, end_date=end_date,
            frequency=frequency, adjustflag="3"
        )
        df = pd.DataFrame(rs.get_data())
        if df.empty:
            return []
        records = df.to_dict('records')
        # 转换数值
        for r in records:
            for k in ['open', 'high', 'low', 'close', 'volume', 'amount']:
                r[k] = _safe_float(r.get(k, 0))
        return records
    finally:
        _bs_logout(bs)


# ========== akshare 次方案（降级） ==========

def _search_akshare(keyword):
    """akshare 搜索（降级方案）"""
    try:
        import akshare as ak
        df = ak.stock_zh_a_spot_em()
        matches = df[df['名称'].str.contains(keyword, na=False)]
        if matches.empty:
            return []
        results = []
        for _, row in matches.head(10).iterrows():
            results.append({
                'code': row['代码'],
                'name': row['名称'],
                'bs_code': _to_baostock_code(row['代码']),
            })
        return results
    except Exception as e:
        print(f"[akshare fallback] 搜索失败: {e}", file=sys.stderr)
        return []


def _get_akshare_data(code, years=5):
    """akshare 获取数据（降级方案）"""
    try:
        import akshare as ak
        result = {
            'code': code,
            'company': '',
            'source': 'akshare',
            'years': [],
            'revenue': [],
            'net_profit': [],
            'gross_margin': [],
            'roe': [],
            'np_margin': [],
            'eps': [],
            'revenue_yoy': [],
            'profit_yoy': [],
            'quarters': [],
            'q_revenue': [],
            'q_gross_margin': [],
            'q_net_profit': [],
        }

        # 获取公司名
        try:
            spot = ak.stock_zh_a_spot_em()
            row = spot[spot['代码'] == code]
            if not row.empty:
                result['company'] = row.iloc[0]['名称']
        except Exception:
            result['company'] = code

        try:
            prefix = "sh" if code.startswith('6') else "sz"
            df = ak.stock_financial_report_sina(stock=f"{prefix}{code}", symbol="利润表")
            if df is not None and not df.empty:
                recent = df.head(years)
                for _, row in recent.iterrows():
                    year = str(row.get('报告日', row.get('日期', '')))[:4]
                    if year and year.isdigit():
                        result['years'].append(year)
                        result['revenue'].append(_safe_float(row.get('营业收入', 0)))
                        result['net_profit'].append(_safe_float(row.get('净利润', 0)))
        except Exception as e:
            print(f"[akshare fallback] 数据获取失败: {e}", file=sys.stderr)

        return result
    except Exception as e:
        print(f"[akshare fallback] 失败: {e}", file=sys.stderr)
        return {'code': code, 'company': '', 'source': 'akshare-failed',
                'years': [], 'revenue': [], 'net_profit': [], 'gross_margin': [],
                'roe': [], 'np_margin': [], 'eps': [], 'revenue_yoy': [], 'profit_yoy': [],
                'quarters': [], 'q_revenue': [], 'q_gross_margin': [], 'q_net_profit': []}


# ========== 统一入口（主方案 → 次方案自动降级） ==========

def search_stock(keyword):
    """搜索股票：baostock → akshare"""
    try:
        result = _search_baostock(keyword)
        if result:
            return result
    except Exception as e:
        print(f"[baostock] 搜索失败，降级到 akshare: {e}", file=sys.stderr)

    return _search_akshare(keyword)


def get_financial_data(code, report_type='annual', years=5):
    """获取财务数据：baostock → akshare"""
    try:
        result = _get_baostock_data(code, years)
        if result['years']:
            return result
        print(f"[baostock] {code} 无数据，降级到 akshare", file=sys.stderr)
    except Exception as e:
        print(f"[baostock] 获取失败，降级到 akshare: {e}", file=sys.stderr)

    return _get_akshare_data(code, years)


def get_peer_data(codes, metrics=None):
    """获取同行数据：baostock → akshare"""
    try:
        result = _get_baostock_peer(codes, years=5)
        if result:
            return result
    except Exception as e:
        print(f"[baostock] 同行获取失败，降级到 akshare: {e}", file=sys.stderr)

    results = {}
    for code in codes:
        data = _get_akshare_data(code, years=5)
        if data['company']:
            results[data['company']] = data
    return results


def get_kline(code, start_date, end_date, frequency='d'):
    """获取K线数据：baostock → 返回空"""
    try:
        return _get_baostock_kline(code, start_date, end_date, frequency)
    except Exception as e:
        print(f"[baostock] K线获取失败: {e}", file=sys.stderr)
        return []


# ========== CLI ==========

def main():
    parser = argparse.ArgumentParser(description='A 股财报数据获取（Baostock 主方案）')
    parser.add_argument('--search', type=str, help='搜索公司名')
    parser.add_argument('--code', type=str, help='股票代码')
    parser.add_argument('--codes', type=str, help='多股票代码，逗号分隔')
    parser.add_argument('--type', type=str, default='annual',
                        choices=['annual', 'quarterly', 'semiannual'], help='报告类型')
    parser.add_argument('--years', type=int, default=5, help='年数')
    parser.add_argument('--kline', action='store_true', help='获取K线数据')
    parser.add_argument('--start', type=str, help='K线开始日期 YYYY-MM-DD')
    parser.add_argument('--end', type=str, help='K线结束日期 YYYY-MM-DD')
    args = parser.parse_args()

    if args.search:
        results = search_stock(args.search)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif args.code and args.kline:
        data = get_kline(args.code, args.start or '2024-01-01', args.end or '2024-12-31')
        print(json.dumps(data, ensure_ascii=False, indent=2))
    elif args.code:
        data = get_financial_data(args.code, args.type, args.years)
        print(json.dumps(data, ensure_ascii=False, indent=2))
    elif args.codes:
        codes = [c.strip() for c in args.codes.split(',')]
        data = get_peer_data(codes)
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print("用法:")
        print("  python data_fetcher.py --search '贵州茅台'")
        print("  python data_fetcher.py --code 600519 --type annual --years 5")
        print("  python data_fetcher.py --codes 600519,000858")
        print("  python data_fetcher.py --code 600519 --kline --start 2024-01-01 --end 2024-12-31")


if __name__ == '__main__':
    main()
