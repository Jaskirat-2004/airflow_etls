# dags/lms/lms_fact_tables.py

from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.hooks.base import BaseHook
from airflow.providers.postgres.hooks.postgres import PostgresHook
from clickhouse_driver import Client as CHClient


POSTGRES_CONN_ID     = "DI-POSTGRES"
POSTGRES_DB          = "lms"
CLICKHOUSE_CONN_ID   = "DI-CLICKHOUSE"
CLICKHOUSE_DB        = "lms"
CH_INSERT_CHUNK_SIZE = 50_000   # rows per CH insert — prevents memory spikes


# ─────────────────────────────────────────────────────────────────────────────
# QUERY 1 — fact_course_completion
# ─────────────────────────────────────────────────────────────────────────────

FACT_COURSE_COMPLETION_QUERY = """
SELECT
    base.course_id,
    base.course_name,
    base.assigned_date,
    base.course_created_at,
    base.module_id,
    base.module_name,
    base.lesson_id,
    base.lesson_name,
    base.user_id,
    base.username,
    base.source,
    base.source_name,
    base.client_name,
    base.completed_at,
    base.completion_status,
    CASE
        WHEN COUNT(*) OVER w  = COUNT(CASE WHEN base.completion_status = 'Completed'  THEN 1 END) OVER w  THEN 'Completed'
        WHEN COUNT(*) OVER w  = COUNT(CASE WHEN base.completion_status = 'NotStarted' THEN 1 END) OVER w  THEN 'NotStarted'
        ELSE 'InProgress'
    END AS course_status,
    CASE
        WHEN COUNT(*) OVER w1 = COUNT(CASE WHEN base.completion_status = 'Completed'  THEN 1 END) OVER w1 THEN 'Completed'
        WHEN COUNT(*) OVER w1 = COUNT(CASE WHEN base.completion_status = 'NotStarted' THEN 1 END) OVER w1 THEN 'NotStarted'
        ELSE 'InProgress'
    END AS user_course_status,
    CASE
        WHEN COUNT(*) OVER w2 = COUNT(CASE WHEN base.completion_status = 'Completed'  THEN 1 END) OVER w2 THEN 'Completed'
        WHEN COUNT(*) OVER w2 = COUNT(CASE WHEN base.completion_status = 'NotStarted' THEN 1 END) OVER w2 THEN 'NotStarted'
        ELSE 'InProgress'
    END AS user_status

FROM (
    -- Wrap so that completion_status alias resolves before window functions use it
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
        assign.source_name,
        assign.client_name,
        CASE
            WHEN progress.completed_at::text = '1970-01-01 05:30:00' THEN '-'
            ELSE COALESCE(progress.completed_at::text, '-')
        END AS completed_at,
        CASE
            WHEN progress.completion_status IS NOT NULL
             AND progress.completion_status != '' THEN progress.completion_status
            ELSE 'NotStarted'
        END AS completion_status

    FROM (
        -- assign: live course/module/lesson skeleton × all assignment sources
        SELECT
            cd.course_id,
            cd.course_name,
            cd.assigned_date,
            cd.course_created_at,
            cd.module_id,
            cd.module_name,
            cd.lesson_id,
            cd.lesson_name,
            cd.client_name,
            eu.user_id,
            eu.username,
            eu.source,
            eu.source_name
        FROM (
            -- cd: live course / module / lesson skeleton
            SELECT
                c.id           AS course_id,
                c.name         AS course_name,
                c."startDate"  AS assigned_date,
                c."createdAt"  AS course_created_at,
                cm.id          AS module_id,
                cm.title       AS module_name,
                cl.id          AS lesson_id,
                cl.title       AS lesson_name,
                c.client_name
            FROM courses c
            LEFT JOIN "CourseModule" cm
                ON  cm."courseId"  = c.id
                AND cm.client_name = c.client_name
                AND cm.id         != ''
                AND cm.status      = 'Live'
            LEFT JOIN "CourseLesson" cl
                ON  cl."courseModuleId" = cm.id
                AND cl.client_name      = c.client_name
                AND cl.id              != ''
                AND cl.status           = 'Live'
            WHERE c.status = 'Live'
        ) cd

        LEFT JOIN (
            -- eu: all 5 assignment sources merged
            -- All status/active filters are in JOIN ON, not WHERE,
            -- so assignment rows are never silently dropped by a NULL join miss

            -- Individual assignment
            SELECT
                eu."A"                  AS course_id,
                eu."B"                  AS user_id,
                um.username             AS username,
                'Individual Assignment' AS source,
                um.username             AS source_name,
                eu.client_name
            FROM "enrolledusers" eu
            LEFT JOIN "userMaster" um
                ON  um.id          = eu."B"
                AND um.client_name = eu.client_name
                AND um.status      = 1

            UNION ALL

            -- Department assignment
            SELECT
                ctd."A"                 AS course_id,
                um.id                   AS user_id,
                um.username             AS username,
                'Department Assignment' AS source,
                d.name                  AS source_name,
                ctd.client_name
            FROM "CourseTodepartment" ctd
            LEFT JOIN "departmentTorolePolicy" dtp
                ON  dtp."A"         = ctd."B"
                AND dtp.client_name = ctd.client_name
            LEFT JOIN "userMaster" um
                ON  um."roleId"    = dtp."B"
                AND um.client_name = ctd.client_name
                AND um.status      = 1
            LEFT JOIN department d
                ON  d.id           = ctd."B"
                AND d.client_name  = ctd.client_name
                AND d.status       = 1

            UNION ALL

            -- Designation assignment
            SELECT
                ctdesig."A"              AS course_id,
                um.id                    AS user_id,
                um.username              AS username,
                'Designation Assignment' AS source,
                d.name                   AS source_name,
                ctdesig.client_name
            FROM "CourseTodesignation" ctdesig
            LEFT JOIN "userMaster" um
                ON  um."designationId" = ctdesig."B"
                AND um.client_name     = ctdesig.client_name
                AND um.status          = 1
            LEFT JOIN designation d
                ON  d.id           = um."designationId"
                AND d.client_name  = ctdesig.client_name
                AND d.status       = 1

            UNION ALL

            -- Batch assignment
            SELECT
                btc."B"           AS course_id,
                um.id             AS user_id,
                um.username       AS username,
                'Batch Assignment' AS source,
                b.name            AS source_name,
                btc.client_name
            FROM "BatchToCourse" btc
            LEFT JOIN "Batch" b
                ON  b.id          = btc."A"
                AND b.client_name = btc.client_name
                AND b.status      = 1
            LEFT JOIN "BatchTouserMaster" btum
                ON  btum."A"         = btc."A"
                AND btum.client_name = btc.client_name
            LEFT JOIN "userMaster" um
                ON  um.id          = btum."B"
                AND um.client_name = btc.client_name
                AND um.status      = 1

            UNION ALL

            -- Coach assignment
            SELECT
                coach."A"         AS course_id,
                um.id             AS user_id,
                um.username       AS username,
                'Coach Assignment' AS source,
                um.username       AS source_name,
                coach.client_name
            FROM "CourseTouserMaster" coach
            LEFT JOIN "userMaster" um
                ON  um.id          = coach."B"
                AND um.client_name = coach.client_name
                AND um.status      = 1

        ) eu
            ON  eu.course_id   = cd.course_id
            AND eu.client_name = cd.client_name

    ) assign

    LEFT JOIN (
        -- progress: lesson-level completion per user, scoped to tenant
        SELECT
            cp."courseId"         AS course_id,
            cp."userId"           AS user_id,
            cp.client_name,
            cp."lastAccessedAt"   AS completed_at,
            lp."lessonId"         AS lesson_id,
            lp."completionStatus" AS completion_status
        FROM "CourseProgress" cp
        LEFT JOIN "ModuleProgress" mp
            ON  mp."courseProgressId" = cp.id
            AND mp.client_name        = cp.client_name
        LEFT JOIN "LessonProgress" lp
            ON  lp."moduleProgressId" = mp.id
            AND lp.client_name        = cp.client_name
        WHERE lp."completionStatus" IS NOT NULL
          AND lp."completionStatus" != ''
    ) progress
        ON  progress.lesson_id   = assign.lesson_id
        AND progress.user_id     = assign.user_id
        AND progress.client_name = assign.client_name

) base

WINDOW
    w  AS (PARTITION BY base.client_name, base.course_id),
    w1 AS (PARTITION BY base.client_name, base.course_id, base.user_id),
    w2 AS (PARTITION BY base.client_name, base.user_id)
"""


# ─────────────────────────────────────────────────────────────────────────────
# QUERY 2 — fact_certificate_awards
# ─────────────────────────────────────────────────────────────────────────────

FACT_CERTIFICATE_AWARDS_QUERY = """
SELECT
    cert.id                                  AS id,
    cert.name                                AS certificate_name,
    CASE
        WHEN cert.status = 1 THEN 'Active'
        ELSE 'In-Active'
    END                                      AS certificate_status,
    cert."type"                              AS certificate_type,
    cert."createdAt"                         AS created_at,
    cert."modifiedAt"                        AS modified_at,
    COALESCE(course.id,   '')                AS course_id,
    COALESCE(course.name, '')                AS linked_course_name,
    course."startDate"                       AS start_date,
    course."endDate"                         AS end_date,
    COALESCE(course.status, '')              AS course_status,
    COALESCE(course."certificateId", '')     AS certificate_id,
    COALESCE(lang."B", '')                   AS lang_id,
    cert.client_name,
    COALESCE(cp."userId",           '')      AS user_id,
    COALESCE(cp."completionStatus", '')      AS completion_status,
    cp."completedAt"                         AS awarded_date,
    COALESCE(um.username,       '')          AS user_awarded,
    COALESCE(um."departmentId", '')          AS user_department_id,
    COALESCE(lm.name,           '')          AS language

FROM "Certificate" cert

LEFT JOIN courses course
    ON  course."certificateId" = cert.id
    AND course.status          = 'Live'
    AND course.client_name     = cert.client_name

LEFT JOIN "CertificateTolanguageMaster" lang
    ON  lang."A"         = cert.id
    AND lang.client_name = cert.client_name

LEFT JOIN "CourseProgress" cp
    ON  course.id IS NOT NULL
    AND cp."courseId"         = course.id
    AND cp."completionStatus" = 'Completed'
    AND cp.client_name        = cert.client_name

LEFT JOIN "userMaster" um
    ON  um.id          = cp."userId"
    AND um.client_name = cert.client_name

LEFT JOIN "languageMaster" lm
    ON  lm.id          = lang."B"
    AND lm.client_name = cert.client_name

WHERE cert.status = 1
"""


# ─────────────────────────────────────────────────────────────────────────────
# CLICKHOUSE TABLE DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

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
# LOADER
# ─────────────────────────────────────────────────────────────────────────────

# Columns that are Nullable(DateTime) in ClickHouse — Python None is valid.
# All other columns are String and must receive '' instead of None.
_NULLABLE_DATETIME_COLS = frozenset({
    "assigned_date", "course_created_at",
    "created_at", "modified_at",
    "start_date", "end_date", "awarded_date",
})


def _coerce(col: str, val):
    """None → '' for CH String cols; None stays None for Nullable(DateTime)."""
    if val is None:
        return None if col in _NULLABLE_DATETIME_COLS else ""
    return val


def build_fact_table(
    fact_name: str,
    pg_query: str,
    ch_create_sql: str,
    ch_table: str,
) -> None:
    print(f"[{fact_name}] Starting...")

    ch_client = get_ch_client()

    try:
        ch_client.execute(ch_create_sql)
        print(f"[{fact_name}] ClickHouse table ready")

        ch_client.execute(f"TRUNCATE TABLE IF EXISTS {CLICKHOUSE_DB}.{ch_table}")
        print(f"[{fact_name}] Truncated")

        print(f"[{fact_name}] Querying PostgreSQL...")
        pg_conn = get_pg_conn()

        try:
            cur = pg_conn.cursor()
            cur.execute(pg_query)

            # description is guaranteed non-None after execute() on a regular cursor
            col_names  = [d[0] for d in cur.description]
            total_rows = 0
            chunk_num  = 0

            print(f"[{fact_name}] Columns: {col_names}")

            # fetchmany keeps memory flat — only CH_INSERT_CHUNK_SIZE rows in RAM at once
            while True:
                rows = cur.fetchmany(CH_INSERT_CHUNK_SIZE)
                if not rows:
                    break

                chunk_num += 1
                data = [
                    {col: _coerce(col, val) for col, val in zip(col_names, row)}
                    for row in rows
                ]
                ch_client.execute(
                    f"INSERT INTO {CLICKHOUSE_DB}.{ch_table} VALUES",
                    data,
                )
                total_rows += len(data)
                print(f"[{fact_name}] Chunk {chunk_num}: {len(data)} rows (total: {total_rows})")

            cur.close()

        finally:
            pg_conn.close()

        if total_rows == 0:
            print(f"[{fact_name}] WARNING: 0 rows — nothing inserted")
        else:
            print(f"[{fact_name}] Done — {total_rows} rows in {chunk_num} chunk(s)")

    finally:
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
    dag_id="lms_fact_tables",
    description="Compute LMS fact tables from Postgres and load into ClickHouse",
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

    # Both tasks are independent — run in parallel
    [t1_course, t2_cert]
