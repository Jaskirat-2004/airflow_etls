CREATE TABLE vodafone_tracking_table (
    table_name          VARCHAR(100) PRIMARY KEY,
    last_processed_date DATE,
    rows_inserted       INTEGER,
    last_run_at         TIMESTAMP DEFAULT NOW(),
    status              VARCHAR(20)
);