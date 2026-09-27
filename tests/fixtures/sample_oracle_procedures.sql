-- Sample Oracle Stored Procedure for Trade Enrichment and Reconciliation

-- ==========================================
-- SP_ENRICH_TRADE: Enrich trade with fee calculation
-- ==========================================
CREATE OR REPLACE PROCEDURE SP_ENRICH_TRADE (
    p_trade_id   IN VARCHAR2,
    p_trd_dt     IN DATE,
    p_cp_cd      IN VARCHAR2,
    p_sett_raw   IN VARCHAR2,
    p_sett_ccy   IN VARCHAR2,
    p_sett_amt   OUT NUMBER,
    p_fee_pct    OUT NUMBER
) AS
    v_sett_amt   NUMBER(18,2);
    v_fee_pct    NUMBER(6,4);
BEGIN
    -- Parse settlement amount from raw string
    v_sett_amt := CAST(REPLACE(p_sett_raw, ',', '') AS NUMBER(18,2));
    
    -- Lookup fee percentage from fee schedule
    BEGIN
        SELECT FEE_PCT
        INTO v_fee_pct
        FROM FEE_SCHEDULE
        WHERE CP_CD = p_cp_cd
        AND EFF_DT <= SYSDATE
        AND (EXP_DT IS NULL OR EXP_DT > SYSDATE)
        ORDER BY EFF_DT DESC
        FETCH FIRST 1 ROW ONLY;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            v_fee_pct := 0;
    END;
    
    -- Apply fee to settlement amount
    p_sett_amt := v_sett_amt * (1 + NVL(v_fee_pct, 0));
    p_fee_pct := NVL(v_fee_pct, 0);
    
    -- Insert enriched trade
    INSERT INTO TRADE_ENRICHED (
        TRADE_ID, TRD_DT, CP_CD, SETT_AMT, SETT_CCY, FEE_PCT, CREATED_DT
    ) VALUES (
        p_trade_id, p_trd_dt, p_cp_cd, v_sett_amt * (1 + NVL(v_fee_pct, 0)), 
        'USD', NVL(v_fee_pct, 0), SYSDATE
    );
    
    COMMIT;
EXCEPTION
    WHEN OTHERS THEN
        ROLLBACK;
        RAISE;
END SP_ENRICH_TRADE;
/

-- ==========================================
-- SP_RECON_MATCH: Reconcile trades against confirmations
-- ==========================================
CREATE OR REPLACE PROCEDURE SP_RECON_MATCH (
    p_recon_dt   IN DATE,
    p_batch_id   OUT NUMBER
) AS
    v_batch_id   NUMBER;
    v_diff_amt   NUMBER(18,2);
    v_break_code VARCHAR2(10);
BEGIN
    -- Create reconciliation batch
    SELECT RECON_BATCH_SEQ.NEXTVAL INTO v_batch_id FROM DUAL;
    
    -- Match enriched trades with confirmations
    FOR rec IN (
        SELECT 
            e.TRADE_ID,
            e.SETT_AMT AS ENRICHED_SETT_AMT,
            c.CONF_AMT AS CONFIRMED_SETT_AMT,
            c.CONF_DT,
            e.CP_CD
        FROM TRADE_ENRICHED e
        JOIN CONFIRMATIONS c ON e.TRADE_ID = c.TRADE_ID
        WHERE e.TRD_DT = p_recon_dt
    ) LOOP
        v_diff_amt := rec.ENRICHED_SETT_AMT - rec.CONFIRMED_SETT_AMT;
        
        -- Determine break code
        v_break_code := CASE
            WHEN ABS(v_diff_amt) > 0.01 THEN 'SAMT'
            WHEN rec.CONF_DT != p_recon_dt THEN 'SDAT'
            ELSE NULL
        END;
        
        -- Insert reconciliation result
        INSERT INTO RECON_RESULTS (
            BATCH_ID, TRADE_ID, RECON_DT,
            ENRICHED_SETT_AMT, CONF_AMT, DIFF_AMT, BREAK_CODE,
            CP_CD, CREATED_DT
        ) VALUES (
            v_batch_id, rec.TRADE_ID, p_recon_dt,
            rec.ENRICHED_SETT_AMT, rec.CONFIRMED_SETT_AMT, v_diff_amt,
            v_break_code, rec.CP_CD, SYSDATE
        );
    END LOOP;
    
    p_batch_id := v_batch_id;
    COMMIT;
EXCEPTION
    WHEN OTHERS THEN
        ROLLBACK;
        RAISE;
END SP_RECON_MATCH;
/

-- ==========================================
-- FEE_SCHEDULE Table
-- ==========================================
CREATE TABLE FEE_SCHEDULE (
    CP_CD          VARCHAR2(20) PRIMARY KEY,
    FEE_PCT        NUMBER(6,4) NOT NULL,
    FEE_TYPE       VARCHAR2(20) DEFAULT 'SETTLEMENT',
    EFF_DT         DATE DEFAULT SYSDATE,
    EXP_DT         DATE,
    CREATED_BY     VARCHAR2(50),
    CREATED_DT     DATE DEFAULT SYSDATE
);

-- Sample data
INSERT INTO FEE_SCHEDULE (CP_CD, FEE_PCT, FEE_TYPE, EFF_DT) VALUES ('GS', 0.0005, 'SETTLEMENT', DATE '2024-01-01');
INSERT INTO FEE_SCHEDULE (CP_CD, FEE_PCT, FEE_TYPE, EFF_DT) VALUES ('MS', 0.0003, 'SETTLEMENT', DATE '2024-01-01');
INSERT INTO FEE_SCHEDULE (CP_CD, FEE_PCT, FEE_TYPE, EFF_DT) VALUES ('JPM', 0.0004, 'SETTLEMENT', DATE '2024-01-01');
INSERT INTO FEE_SCHEDULE (CP_CD, FEE_PCT, FEE_TYPE, EFF_DT) VALUES ('CITI', 0.0002, 'SETTLEMENT', DATE '2024-01-01');
COMMIT;

-- ==========================================
-- TRADE_CORE Table
-- ==========================================
CREATE TABLE TRADE_CORE (
    TRADE_ID       VARCHAR2(50) PRIMARY KEY,
    TRD_DT         DATE NOT NULL,
    CP_CD          VARCHAR2(20) NOT NULL,
    TRD_STATUS     VARCHAR2(20),
    SETT_AMT       NUMBER(18,2),
    SETT_CCY       VARCHAR2(3),
    CREATED_DT     DATE DEFAULT SYSDATE,
    UPDATED_DT     DATE DEFAULT SYSDATE
);

-- ==========================================
-- TRADE_ENRICHED Table
-- ==========================================
CREATE TABLE TRADE_ENRICHED (
    TRADE_ID       VARCHAR2(50) PRIMARY KEY,
    TRD_DT         DATE NOT NULL,
    CP_CD          VARCHAR2(20) NOT NULL,
    SETT_AMT       NUMBER(18,2) NOT NULL,
    SETT_CCY       VARCHAR2(3) NOT NULL,
    FEE_PCT        NUMBER(6,4) DEFAULT 0,
    CREATED_DT     DATE DEFAULT SYSDATE
);

-- ==========================================
-- CONFIRMATIONS Table
-- ==========================================
CREATE TABLE CONFIRMATIONS (
    TRADE_ID       VARCHAR2(50) PRIMARY KEY,
    CONF_AMT       NUMBER(18,2) NOT NULL,
    CONF_DT        DATE NOT NULL,
    CP_CD          VARCHAR2(20) NOT NULL,
    CONF_STATUS    VARCHAR2(20),
    RECEIVED_DT    DATE DEFAULT SYSDATE
);

-- ==========================================
-- RECON_RESULTS Table
-- ==========================================
CREATE TABLE RECON_RESULTS (
    BATCH_ID           NUMBER NOT NULL,
    TRADE_ID           VARCHAR2(50) NOT NULL,
    RECON_DT           DATE NOT NULL,
    ENRICHED_SETT_AMT  NUMBER(18,2),
    CONF_AMT           NUMBER(18,2),
    DIFF_AMT           NUMBER(18,2),
    BREAK_CODE         VARCHAR2(10),
    CP_CD              VARCHAR2(20),
    CREATED_DT         DATE DEFAULT SYSDATE,
    PRIMARY KEY (BATCH_ID, TRADE_ID)
);

-- Indexes
CREATE INDEX IDX_RECON_BATCH ON RECON_RESULTS(BATCH_ID);
CREATE INDEX IDX_RECON_BREAK ON RECON_RESULTS(BREAK_CODE);
CREATE INDEX IDX_TRADE_CP ON TRADE_CORE(CP_CD);
CREATE INDEX IDX_TRADE_DT ON TRADE_CORE(TRD_DT);

COMMIT;