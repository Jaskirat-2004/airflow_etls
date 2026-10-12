# dags/lms/lms_facts.py

from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.hooks.base import BaseHook
from airflow.providers.postgres.hooks.postgres import PostgresHook
from clickhouse_driver import Client as CHClient


POSTGRES_CONN_ID      = "DI-POSTGRES"
POSTGRES_DB           = "lms"
CLICKHOUSE_CONN_ID    = "Clickhouse_LMS"   # change to your connection ID
CLICKHOUSE_DB         = "lms"


# ─────────────────────────────────────────────────────────────────────────────
# QUERIES
# ─────────────────────────────────────────────────────────────────────────────

FACT_COURSE_COMPLETION_QUERY = """
SELECT
    assign.course_id,
    assign.course_name,
    assign.assigned_date,
    assign.course_created_at,
    assign.module_id,
    assign.module_name,
    assign.lesson_id,
    assign.lesson_name,
    assign.user_id,
    assign.username,
    assign.source,
    assign."Source Name",
    assign.client_name,
    CASE
        WHEN progress.completed_at::text = '1970-01-01 05:30:00' THEN '-'
        ELSE progress.completed_at::text
    END AS completed_at,
    CASE
        WHEN progress.completion_status IS NOT NULL
         AND progress.completion_status != '' THEN progress.completion_status
        ELSE 'NotStarted'
    END AS completion_status,
    CASE
        WHEN COUNT(*) OVER w = COUNT(CASE WHEN COALESCE(progress.completion_status, 'NotStarted') = 'Completed' THEN 1 END) OVER w
            THEN 'Completed'
        WHEN COUNT(*) OVER w = COUNT(CASE WHEN COALESCE(progress.completion_status, 'NotStarted') = 'NotStarted' THEN 1 END) OVER w
            THEN 'NotStarted'
        ELSE 'InProgress'
    END AS course_status,
    CASE
        WHEN COUNT(*) OVER w1 = COUNT(CASE WHEN COALESCE(progress.completion_status, 'NotStarted') = 'Completed' THEN 1 END) OVER w1
            THEN 'Completed'
        WHEN COUNT(*) OVER w1 = COUNT(CASE WHEN COALESCE(progress.completion_status, 'NotStarted') = 'NotStarted' THEN 1 END) OVER w1
            THEN 'NotStarted'
        ELSE 'InProgress'
    END AS user_course_status,
    CASE
        WHEN COUNT(*) OVER w2 = COUNT(CASE WHEN COALESCE(progress.completion_status, 'NotStarted') = 'Completed' THEN 1 END) OVER w2
            THEN 'Completed'
        WHEN COUNT(*) OVER w2 = COUNT(CASE WHEN COALESCE(progress.completion_status, 'NotStarted') = 'NotStarted' THEN 1 END) OVER w2
            THEN 'NotStarted'
        ELSE 'InProgress'
    END AS user_status

FROM (
    SELECT
        cd.*,
        eu.user_id,
        eu.username,
        eu.source,
        eu."Source Name",
        eu.client_name
    FROM (
        SELECT
            c.id          AS course_id,
            c.name        AS course_name,
            c."startDate" AS assigned_date,
            c."createdAt" AS course_created_at,
            cm.id         AS module_id,
            cm.title      AS module_name,
            cl.id         AS lesson_id,
            cl.title      AS lesson_name,
            c.client_name
        FROM courses c
        LEFT JOIN "CourseModule" cm ON c.id = cm."courseId"
        LEFT JOIN "CourseLesson" cl ON cm.id = cl."courseModuleId"
        WHERE c.status = 'Live'
          AND cm.id    != ''
          AND cl.id    != ''
          AND cm.status = 'Live'
          AND cl.status = 'Live'
    ) cd
    LEFT JOIN (

        -- Individual assignment
        SELECT
            eu."A"       AS course_id,
            eu."B"       AS user_id,
            um.username  AS username,
            'Individual Assignment' AS source,
            um.username  AS "Source Name",
            eu.client_name
        FROM enrolled_users eu
        LEFT JOIN "userMaster" um ON um.id = eu."B"
        WHERE um.status = 1

        UNION ALL

        -- Department assignment
        SELECT
            ctd."A"     AS course_id,
            um.id       AS user_id,
            um.username AS username,
            'Department Assignment' AS source,
            d.name      AS "Source Name",
            ctd.client_name
        FROM "CourseTodepartment" ctd
        LEFT JOIN "departmentTorolePolicy" dtp ON ctd."B" = dtp."A"
        LEFT JOIN "userMaster" um              ON dtp."B" = um."roleId"
        LEFT JOIN department d                 ON d.id    = ctd."B"
        WHERE um.status = 1
          AND d.status  = 1

        UNION ALL

        -- Designation assignment
        SELECT
            ctdesig."A"  AS course_id,
            um.id        AS user_id,
            um.username  AS username,
            'Designation Assignment' AS source,
            d.name       AS "Source Name",
            ctdesig.client_name
        FROM "CourseTodesignation" ctdesig
        LEFT JOIN "userMaster" um  ON ctdesig."B" = um."designationId"
        LEFT JOIN designation d    ON d.id         = um."designationId"
        WHERE um.status = 1
          AND d.status  = 1

        UNION ALL

        -- Batch assignment
        SELECT
            btc."B"     AS course_id,
            um.id       AS user_id,
            um.username AS username,
            'Batch Assignment' AS source,
            b.name      AS "Source Name",
            btc.client_name
        FROM "BatchToCourse" btc
        LEFT JOIN "Batch" b                  ON btc."A"  = b.id
        LEFT JOIN "BatchTouserMaster" btum   ON btc."A"  = btum."A"
        LEFT JOIN "userMaster" um            ON btum."B" = um.id
        WHERE um.status   = 1
          AND b.status     = 1
          AND um.id        != ''

        UNION ALL

        -- Coach assignment
        SELECT
            coach."A"   AS course_id,
            um.id       AS user_id,
            um.username AS username,
            'Coach Assignment' AS source,
            um.username AS "Source Name",
            coach.client_name
        FROM "CourseTouserMaster" coach
        LEFT JOIN "userMaster" um ON coach."B" = um.id
        WHERE um.status = 1
          AND um.id     != ''

    ) eu ON eu.course_id = cd.course_id
) assign

LEFT JOIN (
    SELECT
        cp.id                AS courseprogress_id,
        cp."courseId"        AS course_id,
        cp."userId"          AS user_id,
        cp."lastAccessedAt"  AS completed_at,
        lp."lessonId"        AS lesson_id,
        lp."completionStatus" AS completion_status
    FROM "CourseProgress" cp
    LEFT JOIN "ModuleProgress" mp ON cp.id     = mp."courseProgressId"
    LEFT JOIN "LessonProgress" lp ON mp.id     = lp."moduleProgressId"
    WHERE lp."completionStatus" != ''
) progress
    ON assign.lesson_id = progress.lesson_id
   AND assign.user_id   = progress.user_id

WINDOW
    w  AS (PARTITION BY assign.course_id),
    w1 AS (PARTITION BY assign.course_id, assign.user_id),
    w2 AS (PARTITION BY assign.user_id)
"""


FACT_CERTIFICATE_AWARDS_QUERY = """
SELECT
    full_data.*,
    langmaster.name AS "Language"
FROM (
    SELECT
        out.*,
        um.username        AS "User Awarded",
        um."departmentId"  AS user_department_id
    FROM (
        SELECT
            main.*,
            cp."userId",
            cp."completionStatus",
            cp."completedAt" AS "Awarded Date"
        FROM (
            SELECT
                cert.id                 AS id,
                cert.name               AS "Certificate Name",
                CASE
                    WHEN cert.status = 1 THEN 'Active'
                    ELSE 'In-Active'
                END                     AS "Certificate Status",
                cert.type               AS "Certificate Type",
                cert."createdAt",
                cert."modifiedAt",
                course.id               AS course_id,
                course.name             AS "Linked Course Name",
                course."startDate",
                course."endDate",
                course.status           AS course_status,
                course."certificateId"  AS "certificateId",
                lang."B"                AS langid,
                cert.client_name
            FROM "Certificate" cert
            LEFT JOIN courses course
                ON  cert.id     = course."certificateId"
                AND course.status = 'Live'
            LEFT JOIN "CertificateTolanguageMaster" lang
                ON cert.id = lang."A"
            WHERE cert.status = 1
        ) main
        LEFT JOIN "CourseProgress" cp
            ON  main.course_id        = cp."courseId"
            AND cp."completionStatus" = 'Completed'
    ) out
    LEFT JOIN "userMaster" um ON out."userId" = um.id
) full_data
LEFT JOIN "languageMaster" langmaster ON full_data.langid = langmaster.id
"""


# ─────────────────────────────────────────────────────────────────────────────
# CLICKHOUSE TABLE DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

# ClickHouse requires a table engine and an ORDER BY key.
# MergeTree is the standard engine for analytical tables.
# We use a minimal ORDER BY — adjust if you need specific query patterns.

FACT_COURSE_COMPLETION_CREATE = """
CREATE TABLE IF NOT EXISTS lms.fact_course_completion (
    course_id          String,
    course_name        String,
    assigned_date      Nullable(DateTime),
    course_created_at  Nullable(DateTime),
    module_id          String,
    module_name        String,
    lesson_id          String,
    lesson_name        String,
    user_id            String,
    username           String,
    source             String,
    source_name        String,
    client_name        String,
    completed_at       String,
    completion_status  String,
    course_status      String,
    user_course_status String,
    user_status        String
)
ENGINE = MergeTree()
ORDER BY (client_name, course_id, user_id)
"""

FACT_CERTIFICATE_AWARDS_CREATE = """
CREATE TABLE IF NOT EXISTS lms.fact_certificate_awards (
    id                   String,
    certificate_name     String,
    certificate_status   String,
    certificate_type     String,
    created_at           Nullable(DateTime),
    modified_at          Nullable(DateTime),
    course_id            String,
    linked_course_name   String,
    start_date           Nullable(DateTime),
    end_date             Nullable(DateTime),
    course_status        String,
    certificate_id       String,
    lang_id              String,
    client_name          String,
    user_id              String,
    completion_status    String,
    awarded_date         Nullable(DateTime),
    user_awarded         String,
    user_department_id   String,
    language             String
)
ENGINE = MergeTree()
ORDER BY (client_name, id, user_id)
"""


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_ch_client() -> CHClient:
    conn = BaseHook.get_connection(CLICKHOUSE_CONN_ID)
    return CHClient(
        host     = conn.host,
        port     = conn.port or 9000,
        user     = conn.login,
        password = conn.password or "",
    )


def get_pg_conn():
    pg_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID, database=POSTGRES_DB)
    return pg_hook.get_conn()


# ─────────────────────────────────────────────────────────────────────────────
# TASK FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def build_fact_table(
    fact_name: str,
    pg_query: str,
    ch_create_sql: str,
    ch_table: str,
) -> None:
    """
    Generic fact table builder — works for both fact tables.

    Steps:
      1. Ensure ClickHouse table exists
      2. Truncate it — fact tables are fully recomputed every run
      3. Run the JOIN query against Postgres
      4. Insert results directly into ClickHouse
    """

    print(f"[{fact_name}] Starting...")

    # ── Ensure ClickHouse table exists ────────────────────────────────────────
    ch_client = get_ch_client()
    ch_client.execute(ch_create_sql)
    print(f"[{fact_name}] ClickHouse table ready")

    # Truncate — fact tables are always fully recomputed from current Postgres data
    # This ensures the fact table always reflects the latest state
    ch_client.execute(f"TRUNCATE TABLE IF EXISTS {CLICKHOUSE_DB}.{ch_table}")
    print(f"[{fact_name}] Truncated existing data")

    # ── Run query against Postgres ────────────────────────────────────────────
    print(f"[{fact_name}] Running query against PostgreSQL...")
    pg_conn   = get_pg_conn()
    pg_cursor = pg_conn.cursor()

    pg_cursor.execute(pg_query)
    rows = pg_cursor.fetchall()

    # column names from cursor description — used to log and verify
    col_names = [desc[0] for desc in pg_cursor.description]

    pg_cursor.close()
    pg_conn.close()

    print(f"[{fact_name}] Query returned {len(rows)} rows")
    print(f"[{fact_name}] Columns: {col_names}")

    if not rows:
        print(f"[{fact_name}] No data returned — skipping insert")
        ch_client.disconnect()
        return

    # ── Convert rows to list of dicts for ClickHouse driver ───────────────────
    # clickhouse-driver insert() expects a list of dicts when column_names given
    # This also handles None values cleanly — ClickHouse Nullable columns accept None
    data = [dict(zip(col_names, row)) for row in rows]

    # ── Insert into ClickHouse ────────────────────────────────────────────────
    print(f"[{fact_name}] Inserting into ClickHouse {CLICKHOUSE_DB}.{ch_table}...")

    ch_client.execute(
        f"INSERT INTO {CLICKHOUSE_DB}.{ch_table} VALUES",
        data,
    )

    print(f"[{fact_name}] Done — {len(data)} rows inserted into ClickHouse")
    ch_client.disconnect()


def build_fact_course_completion() -> None:
    build_fact_table(
        fact_name     = "fact_course_completion",
        pg_query      = FACT_COURSE_COMPLETION_QUERY,
        ch_create_sql = FACT_COURSE_COMPLETION_CREATE,
        ch_table      = "fact_course_completion",
    )


def build_fact_certificate_awards() -> None:
    build_fact_table(
        fact_name     = "fact_certificate_awards",
        pg_query      = FACT_CERTIFICATE_AWARDS_QUERY,
        ch_create_sql = FACT_CERTIFICATE_AWARDS_CREATE,
        ch_table      = "fact_certificate_awards",
    )


# ─────────────────────────────────────────────────────────────────────────────
# DAG
# ─────────────────────────────────────────────────────────────────────────────

with DAG(
    dag_id="lms_facts",
    description="Compute LMS fact tables from Postgres and load into ClickHouse",
    # No schedule — triggered by lms_etl via TriggerDagRunOperator
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["facts", "lms", "production"],
) as dag:

    t1_course = PythonOperator(
        task_id="build_fact_course_completion",
        python_callable=build_fact_course_completion,
    )

    t2_cert = PythonOperator(
        task_id="build_fact_certificate_awards",
        python_callable=build_fact_certificate_awards,
    )

    # both fact tables are independent — run in parallel
    [t1_course, t2_cert]