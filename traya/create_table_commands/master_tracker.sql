-- dim_employee: slowly changing employee dimension, one row per employee per date
-- join to calling_kpis_data on employee_id + report_date
CREATE TABLE master_tracker (
    report_date                    DATE,
    emp_id                  VARCHAR(50),         -- VARCHAR not INT, some IDs like 'NAPS310623' exist
    emp_name                VARCHAR(255),
    official_email          VARCHAR(255),
    personal_email          VARCHAR(255),
    date_of_birth           VARCHAR(20),         -- stored as-is, format inconsistent (DD-Mon-YY)
    gender                  VARCHAR(10),
    designation             VARCHAR(100),
    group_name              VARCHAR(100),
    sub_group               VARCHAR(100),
    team_leader             VARCHAR(255),
    team_leader_email       VARCHAR(255),
    operations_manager      VARCHAR(255),
    line_of_business        VARCHAR(50),
    date_of_joining         VARCHAR(20),         -- stored as-is, format inconsistent
    batch_number            VARCHAR(50),
    versant_tin             VARCHAR(20),
    versant_score           VARCHAR(50),
    education_level         VARCHAR(50),
    highest_education       VARCHAR(100),
    education_stream        VARCHAR(100),
    fresher_experience      VARCHAR(20),
    partner_name            VARCHAR(100),
    partner_location        VARCHAR(100),
    training_start_date     VARCHAR(20),         -- stored as-is
    ojt_start_date          VARCHAR(20),         -- stored as-is
    ojt_end_date            VARCHAR(20),         -- stored as-is
    certification_date      VARCHAR(20),         -- stored as-is
    ops_movement_date       VARCHAR(20),         -- stored as-is
    last_working_day        VARCHAR(20),         -- stored as-is, nullable
    tenure                  SMALLINT,
    active_status           VARCHAR(20),
    crm_id                  VARCHAR(100),
    ameyo_id                VARCHAR(100),
    payroll                 VARCHAR(100),
    site                    VARCHAR(100)
);