CREATE TABLE agent_mapper_staging (
    email_id        TEXT,
    emp_id          TEXT,
    designation     TEXT,
    location        TEXT
);

CREATE TABLE agent_mapper (
    email_id        TEXT,
    emp_id          TEXT,
    designation     TEXT,
    location        TEXT,
    updated_at      TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY(email_id.emp_id)
);
