from flask import Flask, request, render_template_string, redirect, url_for
import yfinance as yf
import pandas as pd
import ssl
import urllib3

app = Flask(__name__)

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context

# Theme colors and fonts
TATA_BLUE = "#1268B3"
DEEP_BLUE = "#001B5B"
WHITE = "#FFFFFF"
FONT_FAMILY = "'DM Sans', Arial, Helvetica, sans-serif"

metrics_sections = {
    "Income Statements": {
        "Total Revenue": "Total Revenue",
        "Cost Of Revenue": "Cost Of Revenue",
        "Gross Profit": "Gross Profit",
        "Operating Expense": "Operating Expense",
        "Operating Income": "Operating Income",
        "Net Income": "Net Income",
        "Basic EPS": "Basic EPS",
        "Diluted EPS": "Diluted EPS",
        "EBITDA": "EBITDA"
    },
    "Balance Sheets": {
        "Total Assets": "Total Assets",
        "Total Liab": "Total Liabilities Net Minority Interest",
        "Total Stockholder Equity": "Total Equity Gross Minority Interest",
        "Working Capital": "Working Capital",
        "Long Term Debt": "Long Term Debt",
        "Net Debt": "Total Debt"
    },
    "Cashflow": {
        "Operating Cash Flow": "Operating Cash Flow",
        "Investing Cash Flow": "Investing Cash Flow",
        "Financing Cash Flow": "Financing Cash Flow",
        "Repayment of Debt": "Repayment Of Debt"
    }
}

def format_number(val):
    if val is None:
        return "N/A"
    try:
        val = float(val)
    except:
        return str(val)
    abs_val = abs(val)
    if abs_val >= 1_000_000_000_000:
        return f"{val / 1_000_000_000_000:.2f} Tn"
    elif abs_val >= 1_000_000_000:
        return f"{val / 1_000_000_000:.2f} Bn"
    elif abs_val >= 1_000_000:
        return f"{val / 1_000_000:.2f} Mn"
    elif abs_val >= 100_000:
        return f"{int(val // 10000 * 10000):,}"
    elif abs_val >= 10_000:
        return f"{int(val // 1000 * 1000):,}"
    elif abs_val >= 1_000:
        return f"{int(val // 100 * 100):,}"
    elif abs_val >= 100:
        return f"{int(val // 10 * 10):,}"
    else:
        return f"{val:.1f}"

def get_with_ttm(df, num_years):
    if df.empty:
        return pd.DataFrame()
    cols = list(df.columns)
    ttm_idx = next((i for i, c in enumerate(cols) if str(c).upper() == 'TTM'), None)
    ttm_col = [cols[ttm_idx]] if ttm_idx is not None else []
    year_cols = [c for i, c in enumerate(cols) if i != ttm_idx]
    return df.loc[:, ttm_col + year_cols[:num_years]]

def get_net_income(info):
    for key in ['netIncome', 'netIncomeToCommon', 'netIncomeAvailableToCommon']:
        if key in info and info[key] is not None:
            return info[key]
    return None

@app.route('/')
def home():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Tata Electronics Financial Dashboard</title>
        <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;700&display=swap" rel="stylesheet">
        <style>
            body { font-family: {{ font_family }}; background: {{ white }}; margin:0; }
            .main-bg { background: linear-gradient(135deg, {{ deep_blue }} 0%, {{ tata_blue }} 100%);
                       min-height: 100vh; display:flex; justify-content:center; align-items:center; }
            .container { background: {{ white }}; padding: 40px; border-radius: 18px;
                         box-shadow:0 4px 16px rgba(0,0,0,0.08); width: 430px; text-align:center; }
            h1 { color: {{ tata_blue }}; margin-bottom:18px; }
            label { display:block; margin:16px 0 4px; font-weight:bold; color: {{ deep_blue }}; }
            input, button { width:85%; padding:10px; margin:10px 0; border-radius:8px; border:1px solid #d0d9e0; font-size:17px; }
            button { background: {{ tata_blue }}; color: {{ white }}; font-weight:bold; border:none; cursor:pointer; }
            button:hover { background: {{ deep_blue }}; }
            input::placeholder { font-style: italic; color: #555; }
        </style>
    </head>
    <body class="main-bg">
        <div class="container">
            <img src="https://www.tataelectronics.com/assets/images/logo.svg" alt="Tata Electronics" style="height:36px;margin-bottom:14px;">
            <h1>Tata Electronics Financial Dashboard</h1>
            <form action="/result" method="get">
                <label>Company Ticker</label>
                <input type="text" name="ticker" placeholder="Enter Company Ticker Name like AMZN, MSFT" required />
                <label>Number of Years</label>
                <input type="number" name="years" min="1" max="10" value="4" required />
                <button type="submit">View Financials</button>
            </form>
        </div>
    </body>
    </html>
    """, font_family=FONT_FAMILY, white=WHITE, deep_blue=DEEP_BLUE, tata_blue=TATA_BLUE)

@app.route('/result')
def result():
    ticker = request.args.get('ticker', '').upper().strip()
    years = int(request.args.get('years', 4))
    if not ticker:
        return redirect(url_for('home'))

    stock = yf.Ticker(ticker)
    info = stock.info

    company_name = info.get('shortName', ticker)
    currency = info.get('currency', 'N/A')
    market_cap = info.get('marketCap')
    total_revenue = info.get('totalRevenue')
    net_income = get_net_income(info)

    profile = {
        "Company Name": company_name,
        "Industry": info.get("industry", "N/A"),
        "Sector": info.get("sector", "N/A"),
        "Website": info.get("website", "N/A"),
        "Full Time Employees": info.get("fullTimeEmployees", "N/A"),
        "Headquarters": info.get("address1", "N/A"),
        "City": info.get("city", "N/A"),
        "State": info.get("state", "N/A"),
        "Country": info.get("country", "N/A"),
        "Phone": info.get("phone", "N/A"),
        "Exchange": info.get("exchange", "N/A")
    }
    description = info.get('longBusinessSummary', 'N/A')

    try:
        key_execs = info.get("companyOfficers", [])
    except:
        key_execs = []

    income_df = get_with_ttm(stock.financials, years)
    balance_df = get_with_ttm(stock.balance_sheet, years)
    cashflow_df = get_with_ttm(stock.cashflow, years)

    if income_df.empty and balance_df.empty and cashflow_df.empty:
        return f"<h2 style='text-align:center;color:{TATA_BLUE}'>No financial data for {ticker}</h2>"

    def to_dict(df, metrics):
        out = {}
        for name, key in metrics.items():
            if key in df.index:
                row_vals = df.loc[key].where(pd.notnull(df.loc[key]), None).tolist()
                years_str = [str(c.year) if hasattr(c, "year") else str(c) for c in df.columns]
                out[name] = dict(zip(years_str, row_vals))
            else:
                years_str = [str(c.year) if hasattr(c, "year") else str(c) for c in df.columns]
                out[name] = {y: None for y in years_str}
        return out

    income_metrics = to_dict(income_df, metrics_sections['Income Statements'])
    balance_metrics = to_dict(balance_df, metrics_sections['Balance Sheets'])
    cashflow_metrics = to_dict(cashflow_df, metrics_sections['Cashflow'])

    def sorted_years(lst):
        ttm = [y for y in lst if y.upper() == 'TTM']
        nums = [y for y in lst if y.upper() != 'TTM']
        nums_sorted = sorted(nums, key=lambda x: int(x))
        return nums_sorted + ttm

    sorted_income_years = sorted_years(list(next(iter(income_metrics.values())).keys()))
    sorted_balance_years = sorted_years(list(next(iter(balance_metrics.values())).keys()))
    sorted_cashflow_years = sorted_years(list(next(iter(cashflow_metrics.values())).keys()))

    def format_dict(d):
        return {k: {year: format_number(v) for year, v in vals.items()} for k, vals in d.items()}

    income_fmt = format_dict(income_metrics)
    balance_fmt = format_dict(balance_metrics)
    cashflow_fmt = format_dict(cashflow_metrics)

    def chart_format(v):
        if v is None or v == 0:
            return None
        try:
            return round(float(v)/1e6, 2)
        except:
            return None

    def chart_data(metrics, key, years):
        return [chart_format(metrics.get(key, {}).get(y)) for y in years]

    graph_tr = chart_data(income_metrics, 'Total Revenue', sorted_income_years)
    graph_gp = chart_data(income_metrics, 'Gross Profit', sorted_income_years)
    graph_opi = chart_data(income_metrics, 'Operating Income', sorted_income_years)
    graph_ope = chart_data(income_metrics, 'Operating Expense', sorted_income_years)
    graph_ebt = chart_data(income_metrics, 'EBITDA', sorted_income_years)
    graph_assets = chart_data(balance_metrics, 'Total Assets', sorted_balance_years)
    graph_liab = chart_data(balance_metrics, 'Total Liab', sorted_balance_years)
    graph_long_debt = chart_data(balance_metrics, 'Long Term Debt', sorted_balance_years)
    graph_net_debt = chart_data(balance_metrics, 'Net Debt', sorted_balance_years)
    graph_op_cf = chart_data(cashflow_metrics, 'Operating Cash Flow', sorted_cashflow_years)
    graph_inv_cf = chart_data(cashflow_metrics, 'Investing Cash Flow', sorted_cashflow_years)
    graph_fin_cf = chart_data(cashflow_metrics, 'Financing Cash Flow', sorted_cashflow_years)
    graph_repay = chart_data(cashflow_metrics, 'Repayment of Debt', sorted_cashflow_years)

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>{{ profile['Company Name'] }} - Financials</title>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels"></script>
    <style>
        body {
            font-family: {{ font_family }};
            background: {{ white }};
            margin: 0;
        }
        h1 {
            color: {{ tata_blue }};
            margin: 15px 0 5px;
            text-align: center;
        }
        .ticker {
            color: {{ deep_blue }};
            text-align: center;
            margin-bottom: 20px;
            font-size: 1.2em;
            font-weight: 500;
        }
        .container-flex {
            max-width: 900px;
            margin: 0 auto 30px auto;
            display: flex;
            gap: 20px;
            padding: 0 15px;
            flex-wrap: wrap;
        }
        .profile-section {
            flex: 2 1 500px;
            background: {{ white }};
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            padding: 20px;
            text-align: left;
            font-size: 0.95rem;
            line-height: 1.6;
        }
        .financial-data {
            flex: 1 1 300px;
            background: {{ white }};
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            padding: 20px;
            font-size: 0.95rem;
            color: {{ deep_blue }};
        }
        .financial-data strong {
            display: block;
            padding: 4px 0;
        }
        .description-section {
            max-width: 900px;
            margin: 0 auto 30px auto;
            padding: 0 15px;
        }
        .desc-title {
            color: {{ tata_blue }};
            font-weight: 700;
            font-size: 1.4rem;
            margin-bottom: 10px;
            text-align: left;
        }
        .desc-text {
            text-align: justify;
            font-size: 1em;
            color: {{ deep_blue }};
            line-height: 1.5;
        }
        .key-personalities {
            max-width: 900px;
            margin: 0 auto 30px auto;
            padding: 0 15px;
        }
        .key-personalities h2 {
            color: {{ tata_blue }};
            font-weight: 700;
            font-size: 1.4rem;
            margin-bottom: 10px;
            text-align: left;
        }
        .key-list {
            list-style-type: none;
            padding-left: 0;
            color: {{ deep_blue }};
            font-size: 1rem;
            line-height: 1.6;
        }
        .key-list li {
            margin-bottom: 6px;
        }
        table {
            width: 100%;
            max-width: 900px;
            margin: 0 auto 20px;
            border-collapse: collapse;
            font-variant-numeric: tabular-nums;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 6px 8px;
            text-align: center;
        }
        th {
            background: {{ tata_blue }};
            color: {{ white }};
            font-weight: 600;
            font-size: 0.95rem;
        }
        .charts-row {
            max-width: 900px;
            margin: 20px auto;
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            padding: 0 15px;
        }
        .chart-box {
            flex: 1 1 45%;
            background: #f8faff;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            padding: 20px;
        }
        .chart-title {
            font-weight: 700;
            margin-bottom: 12px;
            color: {{ tata_blue }};
            text-align: center;
            font-size: 1.1rem;
        }
        canvas {
            border-radius: 12px;
            background: white;
            height: 380px !important;
            width: 100% !important;
        }
    </style>
</head>
<body>
    <h1>{{ profile['Company Name'] }}</h1>
    <div class="ticker">({{ ticker }})</div>

    <div class="container-flex">
        <div class="profile-section">
            <h2>Company Profile</h2>
            <strong>Industry:</strong> {{ profile['Industry'] }}<br>
            <strong>Sector:</strong> {{ profile['Sector'] }}<br>
            <strong>Full Time Employees:</strong> {{ profile['Full Time Employees'] }}<br>
            <strong>Website:</strong> <a href="{{ profile['Website'] }}" target="_blank">{{ profile['Website'] }}</a><br>
            <strong>Headquarters:</strong> {{ profile['Headquarters'] }}<br>
            <strong>City:</strong> {{ profile['City'] }}<br>
            <strong>State:</strong> {{ profile['State'] }}<br>
            <strong>Country:</strong> {{ profile['Country'] }}<br>
            <strong>Phone:</strong> {{ profile['Phone'] }}<br>
            <strong>Exchange:</strong> {{ profile['Exchange'] }}
        </div>
        <div class="financial-data">
            <h2>Financial Data Summary</h2>
            <strong>Currency:</strong> {{ currency }}<br>
            <strong>Market Cap:</strong> {{ format_number(market_cap) }}<br>
            <strong>Total Revenue:</strong> {{ format_number(total_revenue) }}<br>
            <strong>Net Income:</strong> {{ format_number(net_income) }}
        </div>
    </div>

    <div class="description-section">
        <h2 class="desc-title">Description</h2>
        <p class="desc-text">{{ description }}</p>
    </div>

    <div class="key-personalities">
        <h2>Key Personalities</h2>
        {% if key_execs and key_execs|length > 0 %}
        <ul class="key-list">
            {% for exec in key_execs %}
            <li><strong>{{ exec.get('name', 'N/A') }}</strong> — {{ exec.get('title', 'N/A') }}</li>
            {% endfor %}
        </ul>
        {% else %}
        <p style="color: {{ deep_blue }}">No key executive data available.</p>
        {% endif %}
    </div>

    <div class="section">
        <h2>Income Statement</h2>
        <table>
            <thead>
                <tr>
                    <th>Metric</th>
                    {% for y in sorted_income_years %}
                    <th>{{ y }}</th>
                    {% endfor %}
                </tr>
            </thead>
            <tbody>
                {% for m, vals in income_fmt.items() %}
                <tr>
                    <td>{{ m }}</td>
                    {% for y in sorted_income_years %}
                    <td>{{ vals[y] }}</td>
                    {% endfor %}
                </tr>
                {% endfor %}
            </tbody>
        </table>
        <!-- Income Statement Charts with exact layout -->
        <div class="charts-row">
            <div class="chart-box">
                <div class="chart-title">Total Revenue vs Gross Profit</div>
                <canvas id="chart1"></canvas>
            </div>
            <div class="chart-box">
                <div class="chart-title">Operating Income vs Operating Expense</div>
                <canvas id="chart2"></canvas>
            </div>
        </div>
        <div class="charts-row">
            <div class="chart-box">
                <div class="chart-title">Total Revenue vs EBITDA</div>
                <canvas id="chart3"></canvas>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>Balance Sheet</h2>
        <table>
            <thead>
                <tr>
                    <th>Metric</th>
                    {% for y in sorted_balance_years %}
                    <th>{{ y }}</th>
                    {% endfor %}
                </tr>
            </thead>
            <tbody>
                {% for m, vals in balance_fmt.items() %}
                <tr>
                    <td>{{ m }}</td>
                    {% for y in sorted_balance_years %}
                    <td>{{ vals[y] }}</td>
                    {% endfor %}
                </tr>
                {% endfor %}
            </tbody>
        </table>
        <div class="charts-row">
            <div class="chart-box">
                <div class="chart-title">Total Assets vs Total Liabilities</div>
                <canvas id="chart5"></canvas>
            </div>
            <div class="chart-box">
                <div class="chart-title">Long Term Debt vs Net Debt</div>
                <canvas id="chart6"></canvas>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>Cash Flow</h2>
        <table>
            <thead>
                <tr>
                    <th>Metric</th>
                    {% for y in sorted_cashflow_years %}
                    <th>{{ y }}</th>
                    {% endfor %}
                </tr>
            </thead>
            <tbody>
                {% for m, vals in cashflow_fmt.items() %}
                <tr>
                    <td>{{ m }}</td>
                    {% for y in sorted_cashflow_years %}
                    <td>{{ vals[y] }}</td>
                    {% endfor %}
                </tr>
                {% endfor %}
            </tbody>
        </table>
        <div class="charts-row">
            <div class="chart-box">
                <div class="chart-title">Operating vs Investing vs Financing Cash Flow</div>
                <canvas id="chart7"></canvas>
            </div>
            <div class="chart-box">
                <div class="chart-title">Repayment of Debt</div>
                <canvas id="chart8"></canvas>
            </div>
        </div>
    </div>

<script>
    const labelsIncome = {{ sorted_income_years | tojson }};
    const labelsBalance = {{ sorted_balance_years | tojson }};
    const labelsCash = {{ sorted_cashflow_years | tojson }};
    const commonOptions = {
        responsive: true,
        plugins: { legend: { position: 'bottom' }, datalabels: { display: false } },
        elements: { point: { radius: 0 } },
        scales: {
            x: { ticks: { font: { size: 10 } } },
            y: { ticks: { font: { size: 10 } } }
        }
    };

    new Chart(document.getElementById('chart1'), {
        type: 'line',
        data: {
            labels: labelsIncome,
            datasets: [
                { label: 'Total Revenue (Mn)', data: {{ graph_tr | tojson }}, borderColor: '{{ tata_blue }}', fill: false },
                { label: 'Gross Profit (Mn)', data: {{ graph_gp | tojson }}, borderColor: '{{ deep_blue }}', fill: false }
            ]
        },
        options: commonOptions,
        plugins: [ChartDataLabels]
    });

    new Chart(document.getElementById('chart2'), {
        type: 'line',
        data: {
            labels: labelsIncome,
            datasets: [
                { label: 'Operating Income (Mn)', data: {{ graph_opi | tojson }}, borderColor: 'purple', fill: false },
                { label: 'Operating Expense (Mn)', data: {{ graph_ope | tojson }}, borderColor: 'orange', fill: false }
            ]
        },
        options: commonOptions,
        plugins: [ChartDataLabels]
    });

    new Chart(document.getElementById('chart3'), {
        type: 'line',
        data: {
            labels: labelsIncome,
            datasets: [
                { label: 'Total Revenue (Mn)', data: {{ graph_tr | tojson }}, borderColor: '{{ tata_blue }}', fill: false },
                { label: 'EBITDA (Mn)', data: {{ graph_ebt | tojson }}, borderColor: 'red', fill: false }
            ]
        },
        options: commonOptions,
        plugins: [ChartDataLabels]
    });

    new Chart(document.getElementById('chart5'), {
        type: 'bar',
        data: {
            labels: labelsBalance,
            datasets: [
                { label: 'Total Assets (Mn)', data: {{ graph_assets | tojson }}, backgroundColor: '{{ tata_blue }}' },
                { label: 'Total Liabilities (Mn)', data: {{ graph_liab | tojson }}, backgroundColor: '{{ deep_blue }}' }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'bottom', labels: { font: { size: 10 } } },
                datalabels: {
                    display: true,
                    font: { size: 10 },
                    color: '{{ deep_blue }}',
                    anchor: 'end',
                    align: 'center',
                    formatter: val => val !== null ? val : ''
                }
            },
            scales: {
                x: { ticks: { font: { size: 10 } } },
                y: { ticks: { font: { size: 10 } } }
            }
        },
        plugins: [ChartDataLabels]
    });

    new Chart(document.getElementById('chart6'), {
        type: 'line',
        data: {
            labels: labelsBalance,
            datasets: [
                { label: 'Long Term Debt (Mn)', data: {{ graph_long_debt | tojson }}, borderColor: 'orange', fill: false },
                { label: 'Net Debt (Mn)', data: {{ graph_net_debt | tojson }}, borderColor: 'brown', fill: false }
            ]
        },
        options: commonOptions,
        plugins: [ChartDataLabels]
    });

    new Chart(document.getElementById('chart7'), {
        type: 'line',
        data: {
            labels: labelsCash,
            datasets: [
                { label: 'Operating CF (Mn)', data: {{ graph_op_cf | tojson }}, borderColor: 'green', fill: false },
                { label: 'Investing CF (Mn)', data: {{ graph_inv_cf | tojson }}, borderColor: '{{ tata_blue }}', fill: false },
                { label: 'Financing CF (Mn)', data: {{ graph_fin_cf | tojson }}, borderColor: '{{ deep_blue }}', fill: false }
            ]
        },
        options: commonOptions,
        plugins: [ChartDataLabels]
    });

    new Chart(document.getElementById('chart8'), {
        type: 'line',
        data: {
            labels: labelsCash,
            datasets: [
                { label: 'Repayment of Debt (Mn)', data: {{ graph_repay | tojson }}, borderColor: 'red', fill: false }
            ]
        },
        options: commonOptions,
        plugins: [ChartDataLabels]
    });
</script>
</body>
</html>
""",
    profile=profile,
    ticker=ticker,
    description=description,
    key_execs=key_execs,
    currency=currency,
    market_cap=market_cap,
    total_revenue=total_revenue,
    net_income=net_income,
    income_fmt=income_fmt,
    balance_fmt=balance_fmt,
    cashflow_fmt=cashflow_fmt,
    sorted_income_years=sorted_income_years,
    sorted_balance_years=sorted_balance_years,
    sorted_cashflow_years=sorted_cashflow_years,
    graph_tr=graph_tr,
    graph_gp=graph_gp,
    graph_opi=graph_opi,
    graph_ope=graph_ope,
    graph_ebt=graph_ebt,
    graph_assets=graph_assets,
    graph_liab=graph_liab,
    graph_long_debt=graph_long_debt,
    graph_net_debt=graph_net_debt,
    graph_op_cf=graph_op_cf,
    graph_inv_cf=graph_inv_cf,
    graph_fin_cf=graph_fin_cf,
    graph_repay=graph_repay,
    tata_blue=TATA_BLUE,
    deep_blue=DEEP_BLUE,
    white=WHITE,
    font_family=FONT_FAMILY,
    format_number=format_number
)

if __name__ == "__main__":
    app.run(debug=True)
