/* ============================================================================
   fact_certificate_awards — ARCHIVED DESIGN, NOT DEPLOYABLE AS-IS
   ----------------------------------------------------------------------------
   Rescued 2026-08-24 from DAGS\lms\lms_v1\final\lms_fact_tables.py (dag_id
   "lms_fact_tables", L266-318 query / L351-375 DDL) before lms_v0 + lms_v1 were
   deleted. This is the ONLY logic in those two generations that lms_v2 does not
   already supersede: no lms_v2 fact builds certificates, yet lms_v2 still
   ingests the three raw tables it needs (Certificate,
   CertificateTolanguageMaster, languageMaster).

   Two drafts existed. This is v1's — flat column aliases, COALESCE-defended,
   status decoded. v0's was a nested `SELECT out.*` variant, discarded.

   -------------------------------------------------------------------------
   WHY IT CANNOT JUST BE RUN — verified against live db4 (DI-postgres-lms)
   and db5 (DI-ClickHouse) on 2026-08-24:
   -------------------------------------------------------------------------
   1. NO SOURCE DATA.  "Certificate" = 0 rows and "CertificateTolanguageMaster"
      = 0 rows, across all 10 tenants. Only "languageMaster" has data (32 rows).
      So this is blocked on ingestion, not on code.
   2. TWO COLUMNS ARE NOT INGESTED.  The query needs `cert."type"` and
      `course."certificateId"` — neither exists in the live landing tables:
        Certificate = id, name, description, pdfUrl, userId, status,
                      createdAt, modifiedAt, tenant_name
        courses     = id, name, description, mediaId, startDate, endDate,
                      isMandatory, status, createdAt, modifiedAt,
                      languageMasterId, avgRating, authorId, tenant_name
      `certificateId` is FATAL — it is the certificate-to-course join key.
      Either add both to TABLE_CONFIG in lms_v2\config\config.py (if the
      Knowmax source has them), or re-model: Certificate DOES carry `userId`,
      so a direct certificate-to-user grain may remove the need for the
      courses + CourseProgress hop entirely. Decide before writing SQL.
   3. TENANT COLUMN RENAMED.  This draft says `client_name` (6 places);
      lms_v2 standardised on `tenant_name`. Rename all of them.
   4. `cert.status = 1` assumes an integer. lms_v2 ingests Certificate.status
      with no cast — confirm the real type before trusting the CASE.

   TO REVIVE: fix 1-4, then add the query + destination to
   lms_v2\config\fact_config.py FACT_TABLES and the DDL to
   lms_v2\lms_create_fact_tables.py. The generic loader in
   lms_v2\lms_fact_table_etl.py needs no changes — which is why only the SQL
   was kept here and none of the old DAG scaffolding.
   ============================================================================ */


/* ---------- 1. THE QUERY (runs against Postgres landing tables) ---------- */

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
;


/* ---------- 2. THE CLICKHOUSE DESTINATION DDL ---------- */

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
;
