"""
Test fixtures for NL2SQL evaluation
"""

NL2SQL_TEST_CASES = [
    {
        "question": "Show all trades where settlement amount differs from confirmed amount for Goldman Sachs in January 2024",
        "category": "reconciliation",
        "expected_sql": "SELECT t.TRADE_ID, t.TRD_DT, r.SETT_AMT, c.CONF_AMT, (r.SETT_AMT - c.CONF_AMT) as DIFF FROM RECON_RESULTS r JOIN TRADE_CORE t ON r.TRADE_ID = t.TRADE_ID JOIN CONFIRMATIONS c ON r.TRADE_ID = c.TRADE_ID WHERE t.CP_CD = 'GS' AND t.TRD_DT BETWEEN '2024-01-01' AND '2024-01-31' AND ABS(r.SETT_AMT - c.CONF_AMT) > 0.01",
        "expected_tables": ["RECON_RESULTS", "TRADE_CORE", "CONFIRMATIONS"],
        "expected_columns": ["TRADE_ID", "TRD_DT", "SETT_AMT", "CONF_AMT"],
    },
    {
        "question": "What's the total settlement amount by counterparty for last month?",
        "category": "aggregation",
        "expected_sql": "SELECT t.CP_CD, SUM(r.SETT_AMT) as TOTAL_SETTLEMENT FROM RECON_RESULTS r JOIN TRADE_CORE t ON r.TRADE_ID = t.TRADE_ID WHERE t.TRD_DT >= CURRENT_DATE - INTERVAL '1 month' GROUP BY t.CP_CD",
        "expected_tables": ["RECON_RESULTS", "TRADE_CORE"],
        "expected_columns": ["CP_CD", "SETT_AMT"],
    },
    {
        "question": "Find trades with break code SAMT for the past week",
        "category": "break_analysis",
        "expected_sql": "SELECT t.TRADE_ID, t.TRD_DT, t.CP_CD, r.BREAK_CODE FROM RECON_RESULTS r JOIN TRADE_CORE t ON r.TRADE_ID = t.TRADE_ID WHERE r.BREAK_CODE = 'SAMT' AND t.TRD_DT >= CURRENT_DATE - INTERVAL '7 days'",
        "expected_tables": ["RECON_RESULTS", "TRADE_CORE"],
        "expected_columns": ["TRADE_ID", "TRD_DT", "CP_CD", "BREAK_CODE"],
    },
    {
        "question": "Show all trades for counterparty JPM where settlement amount exceeds 1 million",
        "category": "filtering",
        "expected_sql": "SELECT TRADE_ID, TRD_DT, SETT_AMT, CP_CD FROM TRADE_CORE WHERE CP_CD = 'JPM' AND SETT_AMT > 1000000",
        "expected_tables": ["TRADE_CORE"],
        "expected_columns": ["TRADE_ID", "TRD_DT", "SETT_AMT", "CP_CD"],
    },
    {
        "question": "List all break codes and their counts for the current month",
        "category": "aggregation",
        "expected_sql": "SELECT BREAK_CODE, COUNT(*) as COUNT FROM RECON_RESULTS WHERE RECON_DT >= TRUNC(SYSDATE, 'MM') GROUP BY BREAK_CODE ORDER BY COUNT DESC",
        "expected_tables": ["RECON_RESULTS"],
        "expected_columns": ["BREAK_CODE"],
    },
]