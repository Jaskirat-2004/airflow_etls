CREATE TABLE sql_manual_staging (
    report_date         DATE,
    user_id             TEXT,
    sql                 INTEGER
);

CREATE TABLE sql_manual (
    report_date         DATE,
    user_id             TEXT,
    sql                 INTEGER,
    updated_at          TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY(report_date,user_id)
);
