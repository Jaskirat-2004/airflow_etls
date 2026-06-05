
# =========================================================
# MAIN FACT TABLE CONFIG -> at the end of file
# =========================================================

# Table names
FACT_TABLES = [
    "lms_fact_user_x_lesson",
    "lms_fact_quiz_assigned",
    "lms_fact_quiz_submitted",
    "lms_fact_agent_journey"
]

# Queries for each table 

lms_fact_user_x_lesson_query = """

-- THIS IS THE EDITED NEW QUERY (ONLY ACTIVE) ->

WITH course_structure AS (
    SELECT
        c."id"          AS courses_id,
        c."name"        AS courses_name,
        c."startDate"   AS courses_assigned_date,
        c."createdAt"   AS courses_created_at,
        c."tenant_name" AS tenant_name,
        cm."id"         AS coursemodule_id,
        cm."title"      AS coursemodule_name,
        cl."id"         AS courselesson_id,
        cl."title"      AS courselesson_name
    FROM "courses" c
    LEFT JOIN "CourseModule" cm
        ON cm."courseId"    = c."id"
        AND cm."tenant_name" = c."tenant_name"
        AND cm."status"      = 'Live'
    LEFT JOIN "CourseLesson" cl
        ON cl."courseModuleId" = cm."id"
        AND cl."tenant_name"   = c."tenant_name"
        AND cl."status"        = 'Live'
    WHERE c."status" = 'Live'
),

user_assignment AS (

    -- Individual
    SELECT
        eu."A"          AS enrolledusers_course_id,
        eu."B"          AS enrolledusers_user_id,
        um."username"   AS usermaster_username,
        eu."tenant_name" AS enrolledusers_tenant_name,
        'Individual'    AS assignment_source,
        um."username"   AS source_name
    FROM "enrolledusers" eu
    LEFT JOIN "userMaster" um
        ON um."id"          = eu."B"
        AND um."tenant_name" = eu."tenant_name"
    WHERE um."status" = 1  -- moved out of JOIN ON

    UNION ALL

    -- Department
    SELECT
        ctd."A",
        um."id",
        um."username",
        ctd."tenant_name",
        'Department',
        d."name" AS source_name
    FROM "CourseTodepartment" ctd
    LEFT JOIN "departmentTorolePolicy" dtp
        ON dtp."A"           = ctd."B"
        AND dtp."tenant_name" = ctd."tenant_name"
    LEFT JOIN "userMaster" um
        ON um."roleId"        = dtp."B"
        AND um."tenant_name"  = ctd."tenant_name"
    LEFT JOIN "department" d
        ON d."id"     = ctd."B"
        AND d."status" = 1
    WHERE um."status" = 1  -- moved out of JOIN ON

    UNION ALL

    -- Designation
    SELECT
        ctd."A",
        um."id",
        um."username",
        ctd."tenant_name",
        'Designation',
        des."name" AS source_name
    FROM "CourseTodesignation" ctd
    LEFT JOIN "userMaster" um
        ON um."designationId" = ctd."B"
        AND um."tenant_name"  = ctd."tenant_name"
    LEFT JOIN "designation" des
        ON des."id"     = um."designationId"
        AND des."status" = 1
    WHERE um."status" = 1  -- moved out of JOIN ON

    UNION ALL

    -- Batch
    SELECT
        btc."B",
        um."id",
        um."username",
        btc."tenant_name",
        'Batch',
        b."name" AS source_name  -- was missing entirely
    FROM "BatchToCourse" btc
    LEFT JOIN "BatchTouserMaster" btum
        ON btum."A"          = btc."A"
        AND btum."tenant_name" = btc."tenant_name"
    LEFT JOIN "userMaster" um
        ON um."id"           = btum."B"
        AND um."tenant_name"  = btc."tenant_name"
    LEFT JOIN "Batch" b
        ON b."id"     = btc."A"
        AND b."status" = 1          -- Batch join was missing entirely
    WHERE um."status" = 1  -- moved out of JOIN ON

    UNION ALL

    -- Coach
    SELECT
        coach."A",
        um."id",
        um."username",
        coach."tenant_name",
        'Coach',
        um."username" AS source_name
    FROM "CourseTouserMaster" coach
    LEFT JOIN "userMaster" um
        ON um."id"          = coach."B"
        AND um."tenant_name" = coach."tenant_name"
    WHERE um."status" = 1  -- moved out of JOIN ON
),

course_progress AS (
    SELECT
        cp."courseId"       AS courseprogress_course_id,
        cp."userId"         AS courseprogress_user_id,
        cp."tenant_name"    AS courseprogress_tenant_name,
        lp."lessonId"       AS lessonprogress_lesson_id,
        lp."completionStatus" AS lessonprogress_status,
        cp."lastAccessedAt" AS courseprogress_completed_at
    FROM "CourseProgress" cp
    LEFT JOIN "ModuleProgress" mp
        ON mp."courseProgressId" = cp."id"
        AND mp."tenant_name"     = cp."tenant_name"
    LEFT JOIN "LessonProgress" lp
        ON lp."moduleProgressId" = mp."id"
        AND lp."tenant_name"     = cp."tenant_name"
    WHERE lp."completionStatus" IS NOT NULL
),

base AS (
    SELECT
        cs.*,
        ua.enrolledusers_user_id,
        ua.usermaster_username,
        ua.assignment_source,
        ua.source_name,
        ua.enrolledusers_tenant_name,
        CASE
            WHEN cp.courseprogress_completed_at::text = '1970-01-01 05:30:00' THEN NULL
            ELSE cp.courseprogress_completed_at
        END AS final_completed_at,
        COALESCE(cp.lessonprogress_status, 'NotStarted') AS final_completion_status
    FROM course_structure cs
    LEFT JOIN user_assignment ua
        ON cs.courses_id         = ua.enrolledusers_course_id
        AND cs.tenant_name = ua.enrolledusers_tenant_name
    LEFT JOIN course_progress cp
        ON cs.courselesson_id          = cp.lessonprogress_lesson_id
        AND ua.enrolledusers_user_id   = cp.courseprogress_user_id
        AND ua.enrolledusers_tenant_name = cp.courseprogress_tenant_name
)

SELECT
    base.*,

    -- Course status across all users
    CASE
        WHEN COUNT(*) OVER w2 = COUNT(CASE WHEN final_completion_status = 'Completed' THEN 1 END) OVER w2
        THEN 'Completed'
        WHEN COUNT(*) OVER w2 = COUNT(CASE WHEN final_completion_status = 'NotStarted' THEN 1 END) OVER w2
        THEN 'NotStarted'
        ELSE 'InProgress'
    END AS final_course_all_user_status,

    -- Course status per user
    CASE
        WHEN COUNT(*) OVER w1 = COUNT(CASE WHEN final_completion_status = 'Completed' THEN 1 END) OVER w1
        THEN 'Completed'
        WHEN COUNT(*) OVER w1 = COUNT(CASE WHEN final_completion_status = 'NotStarted' THEN 1 END) OVER w1
        THEN 'NotStarted'
        ELSE 'InProgress'
    END AS final_course_per_user_status,

    -- User overall status
    CASE
        WHEN COUNT(*) OVER w3 = COUNT(CASE WHEN final_completion_status = 'Completed' THEN 1 END) OVER w3
        THEN 'Completed'
        WHEN COUNT(*) OVER w3 = COUNT(CASE WHEN final_completion_status = 'NotStarted' THEN 1 END) OVER w3
        THEN 'NotStarted'
        ELSE 'InProgress'
    END AS final_user_status,

    -- Module status per user
    CASE
        WHEN COUNT(*) OVER w4 = COUNT(CASE WHEN final_completion_status = 'Completed' THEN 1 END) OVER w4
        THEN 'Completed'
        WHEN COUNT(*) OVER w4 = COUNT(CASE WHEN final_completion_status = 'NotStarted' THEN 1 END) OVER w4
        THEN 'NotStarted'
        ELSE 'InProgress'
    END AS final_module_per_user_status,

    -- Module status across all users
    CASE
        WHEN COUNT(*) OVER w5 = COUNT(CASE WHEN final_completion_status = 'Completed' THEN 1 END) OVER w5
        THEN 'Completed'
        WHEN COUNT(*) OVER w5 = COUNT(CASE WHEN final_completion_status = 'NotStarted' THEN 1 END) OVER w5
        THEN 'NotStarted'
        ELSE 'InProgress'
    END AS final_module_all_user_status

FROM base

WINDOW
    w1 AS (PARTITION BY enrolledusers_tenant_name, courses_id, enrolledusers_user_id),
    w2 AS (PARTITION BY enrolledusers_tenant_name, courses_id),
    w3 AS (PARTITION BY enrolledusers_tenant_name, enrolledusers_user_id),
    w4 AS (PARTITION BY enrolledusers_tenant_name, coursemodule_id, enrolledusers_user_id),
    w5 AS (PARTITION BY enrolledusers_tenant_name, coursemodule_id)
    
"""

# ==============================================================================================

lms_fact_quiz_assigned_query = """

WITH course_quiz_pages AS (
    SELECT
        c."id"           AS courses_id,
        c."name"         AS courses_name,
        c."tenant_name"  AS tenant_name,
        cm."id"          AS coursemodule_id,
        cm."title"       AS coursemodule_name,
        cl."id"          AS courselesson_id,
        cl."title"       AS courselesson_name,
        p."id"           AS page_id,
        p."title"        AS quiz_page_title,
        p."quizId"       AS quiz_id
    FROM "courses" c
    INNER JOIN "CourseModule" cm
        ON cm."courseId"     = c."id"
        AND cm."tenant_name" = c."tenant_name"
        AND cm."status"      = 'Live'
    INNER JOIN "CourseLesson" cl
        ON cl."courseModuleId" = cm."id"
        AND cl."tenant_name"   = c."tenant_name"
        AND cl."status"        = 'Live'
    INNER JOIN "Page" p
        ON p."courseLessonId" = cl."id"
        AND p."tenant_name"   = c."tenant_name"
        AND p."type"          = 'Quiz'
    WHERE c."status" = 'Live'
      AND p."quizId" IS NOT NULL
      AND p."quizId" != ''
),

enrolled_users AS (
    -- Individual
    SELECT eu."A" AS course_id, eu."B" AS user_id, eu."tenant_name" AS tenant_name,
           'Individual' AS assignment_source, um."username" AS source_name
    FROM "enrolledusers" eu
    LEFT JOIN "userMaster" um
        ON um."id" = eu."B" AND um."tenant_name" = eu."tenant_name"
    WHERE um."status" = 1

    UNION ALL
    -- Department
    SELECT ctd."A", um."id", ctd."tenant_name", 'Department', d."name"
    FROM "CourseTodepartment" ctd
    LEFT JOIN "departmentTorolePolicy" dtp
        ON dtp."A" = ctd."B" AND dtp."tenant_name" = ctd."tenant_name"
    LEFT JOIN "userMaster" um
        ON um."roleId" = dtp."B" AND um."tenant_name" = ctd."tenant_name"
    LEFT JOIN "department" d
        ON d."id" = ctd."B" AND d."status" = 1
    WHERE um."status" = 1

    UNION ALL
    -- Designation
    SELECT ctd."A", um."id", ctd."tenant_name", 'Designation', des."name"
    FROM "CourseTodesignation" ctd
    LEFT JOIN "userMaster" um
        ON um."designationId" = ctd."B" AND um."tenant_name" = ctd."tenant_name"
    LEFT JOIN "designation" des
        ON des."id" = um."designationId" AND des."status" = 1
    WHERE um."status" = 1

    UNION ALL
    -- Batch
    SELECT btc."B", um."id", btc."tenant_name", 'Batch', b."name"
    FROM "BatchToCourse" btc
    LEFT JOIN "BatchTouserMaster" btum
        ON btum."A" = btc."A" AND btum."tenant_name" = btc."tenant_name"
    LEFT JOIN "userMaster" um
        ON um."id" = btum."B" AND um."tenant_name" = btc."tenant_name"
    LEFT JOIN "Batch" b
        ON b."id" = btc."A" AND b."status" = 1
    WHERE um."status" = 1

    UNION ALL
    -- Coach
    SELECT coach."A", um."id", coach."tenant_name", 'Coach', um."username"
    FROM "CourseTouserMaster" coach
    LEFT JOIN "userMaster" um
        ON um."id" = coach."B" AND um."tenant_name" = coach."tenant_name"
    WHERE um."status" = 1
),

user_details AS (
    SELECT
        um."id"           AS user_id,
        um."username",
        um."departmentId" AS department_id,
        um."tenant_name",
        d."name"          AS department_name,
        des."name"        AS designation_name
    FROM "userMaster" um
    LEFT JOIN "department" d
        ON d."id" = um."departmentId" AND d."tenant_name" = um."tenant_name"
    LEFT JOIN "designation" des
        ON des."id" = um."designationId" AND des."tenant_name" = um."tenant_name"
    WHERE um."status" = 1
),

quiz_attempts AS (
    SELECT
        "quizId",
        "userId",
        "tenant_name",
        1                  AS is_submitted,
        MAX("submittedAt") AS attempted_at
    FROM "Submission"
    WHERE "isSubmitted" = 1
    GROUP BY "quizId", "userId", "tenant_name"
)

SELECT
    cqp.tenant_name,
    cqp.courses_id        AS course_id,
    cqp.courses_name      AS course_name,
    cqp.coursemodule_id,
    cqp.coursemodule_name,
    cqp.courselesson_id,
    cqp.courselesson_name,
    cqp.quiz_id,
    COALESCE(NULLIF(cqp.quiz_page_title, ''), cqp.courselesson_name) AS assessment_title,

    eu.assignment_source,
    eu.source_name,

    ud.user_id,
    ud.username,
    ud.department_name,
    ud.designation_name,

    CASE
        WHEN att.attempted_at IS NULL              THEN NULL
        WHEN DATE(att.attempted_at) = '1970-01-01' THEN NULL
        ELSE att.attempted_at
    END                   AS attempted_at,

    CASE
        WHEN att.is_submitted = 1 THEN 'Attempted'
        ELSE 'Not Attempted'
    END                   AS attempt_status

FROM course_quiz_pages cqp
INNER JOIN enrolled_users eu
    ON eu.course_id    = cqp.courses_id
    AND eu.tenant_name = cqp.tenant_name
LEFT JOIN user_details ud
    ON ud.user_id      = eu.user_id
    AND ud.tenant_name = eu.tenant_name
LEFT JOIN quiz_attempts att
    ON att."quizId"     = cqp.quiz_id
    AND att."userId"    = eu.user_id
    AND att.tenant_name = cqp.tenant_name
WHERE ud.department_name IS NOT NULL
  AND ud.department_name != ''
ORDER BY cqp.tenant_name, cqp.courses_name, ud.username;

"""

# ==============================================================================================

lms_fact_quiz_submitted_query = """
WITH course_quiz_ids AS (
    SELECT DISTINCT p."quizId", p."tenant_name"
    FROM "Page" p
    INNER JOIN "CourseLesson" cl
        ON cl."id"          = p."courseLessonId"
        AND cl."tenant_name" = p."tenant_name"
    INNER JOIN "CourseModule" cm
        ON cm."id"          = cl."courseModuleId"
        AND cm."tenant_name" = cl."tenant_name"
    INNER JOIN "courses" c
        ON c."id"          = cm."courseId"
        AND c."tenant_name" = cm."tenant_name"
    WHERE p."type" = 'Quiz'
      AND p."quizId" IS NOT NULL
      AND p."quizId" != ''
),

submissions AS (
    SELECT s.*
    FROM "Submission" s
    INNER JOIN course_quiz_ids cq
        ON cq."quizId"      = s."quizId"
        AND cq."tenant_name" = s."tenant_name"
    WHERE s."isSubmitted" = 1
      AND DATE(s."submittedAt") >= CURRENT_DATE - INTERVAL '90 days'
),

avg_score AS (
    SELECT
        "submissionId",
        ROUND(SUM("finalScore") * 100.0 / NULLIF(SUM("score"), 0), 2) AS overall_percentage
    FROM "QuizQuestion"
    GROUP BY "submissionId"
),

questions AS (
    SELECT
        qq."submissionId",
        qq."id"   AS quiz_question_id,
        REGEXP_REPLACE(
            REPLACE(qq."title", '&nbsp;', ' '),
            '<[^>]*>', '', 'g'
        )         AS question,
        qq."type" AS question_type,
        qq."isCorrect",
        qq."finalScore",
        qq."score"
    FROM "QuizQuestion" qq
),

correct_answers AS (
    SELECT
        "quizQuestionId",
        STRING_AGG("title", ', ') AS correct_answer
    FROM "CorrectAnswer"
    GROUP BY "quizQuestionId"
),

submitted_answers AS (
    SELECT
        "quizQuestionId",
        STRING_AGG("title", ', ') AS submitted_answer
    FROM "SubmittedAnswers"
    GROUP BY "quizQuestionId"
),

question_timing AS (
    SELECT
        "quizQuestionId",
        MAX("startTime") AS start_time,
        MAX("endTime")   AS end_time
    FROM "QuizQuestionAttempt"
    GROUP BY "quizQuestionId"
),

user_details AS (
    SELECT
        um."id"          AS user_id,
        um."username",
        um."departmentId",
        um."tenant_name",
        d."name"         AS department_name,
        des."name"       AS designation_name
    FROM "userMaster" um
    LEFT JOIN "department" d
        ON d."id" = um."departmentId" AND d."tenant_name" = um."tenant_name"
    LEFT JOIN "designation" des
        ON des."id" = um."designationId" AND des."tenant_name" = um."tenant_name"
    WHERE um."status" = 1
)

SELECT
    CONCAT(s."id"::TEXT, '-', ud.username)       AS pkey,
    ud.username,
    ud."departmentId"                             AS user_department_id,
    ud.department_name,
    ud.designation_name,
    s."tenant_name",

    COALESCE(NULLIF(qa."title", ''), s."title")  AS assessment_title,

    CASE
        WHEN s."isSubmitted" = 1
             AND COALESCE(sa.submitted_answer, '') != '' THEN 'Submitted'
        WHEN s."isSubmitted" = 1
             AND COALESCE(sa.submitted_answer, '') = '' THEN 'Duration Timeout'
        ELSE 'Not Submitted'
    END                                           AS assessment_status,

    qa."quizCompletionTimeInMinutes"              AS total_time_allowed_minutes,
    q.question_type,

    ROW_NUMBER() OVER (
        PARTITION BY CONCAT(s."id"::TEXT, '-', ud.username)
        ORDER BY q.quiz_question_id
    )                                             AS question_number,

    q.question,
    COALESCE(sa.submitted_answer, '')             AS submitted_answer,
    COALESCE(ca.correct_answer, '')               AS correct_answer,
    s."score",
    avs.overall_percentage,
    s."attemptNumber"                             AS attempt_number,

    qt.start_time                                 AS start_datetime,
    DATE(qt.start_time)                           AS start_date,
    TO_CHAR(qt.start_time, 'HH24:MI:SS')         AS start_time_formatted,
    qt.end_time                                   AS end_datetime,
    DATE(qt.end_time)                             AS end_date,
    TO_CHAR(qt.end_time, 'HH24:MI:SS')           AS end_time_formatted,

    CASE WHEN q."isCorrect" = 1 THEN 'Correct' ELSE 'Incorrect' END AS answer_status,

    EXTRACT(EPOCH FROM (qt.end_time - qt.start_time)) * 1000     AS time_spent_on_question_ms,
    TO_CHAR((qt.end_time - qt.start_time), 'HH24:MI:SS')         AS time_spent_on_question,

    EXTRACT(EPOCH FROM (s."submittedAt" - s."createdAt")) * 1000  AS time_spent_on_assessment_ms,
    TO_CHAR((s."submittedAt" - s."createdAt"), 'HH24:MI:SS')      AS time_spent_on_assessment

FROM submissions s
LEFT JOIN questions q
    ON q."submissionId"    = s."id"
LEFT JOIN avg_score avs
    ON avs."submissionId"  = s."id"
LEFT JOIN correct_answers ca
    ON ca."quizQuestionId" = q.quiz_question_id
LEFT JOIN submitted_answers sa
    ON sa."quizQuestionId" = q.quiz_question_id
LEFT JOIN question_timing qt
    ON qt."quizQuestionId" = q.quiz_question_id
LEFT JOIN user_details ud
    ON ud.user_id      = s."userId"
    AND ud.tenant_name = s."tenant_name"
LEFT JOIN "QuizAssignment" qa
    ON qa."id"          = s."quizAssignmentId"
    AND qa."tenant_name" = s."tenant_name"
WHERE s."title" != ''
  AND (qt.end_time IS NULL OR DATE(qt.end_time) != '1970-01-01')
ORDER BY ud.username, ud.department_name;

"""

# ==============================================================================================
# lms_fact_agent_journey  —  Phase 1 (Postgres / raw LMS only)
# Grain: user x course x lesson x (course-embedded) quiz   [unique key = journey_key]
# Course completion + quiz attempt/score/pass in one row. TL/AM + agent name added downstream
# in the ClickHouse _merged DAG via sampark.employee_fact (join on email / usermaster_username).
# ==============================================================================================

lms_fact_agent_journey_query = """

WITH course_structure AS (
    SELECT
        c."id"          AS courses_id,
        c."name"        AS courses_name,
        c."startDate"   AS courses_assigned_date,
        c."createdAt"   AS courses_created_at,
        c."tenant_name" AS tenant_name,
        cm."id"         AS coursemodule_id,
        cm."title"      AS coursemodule_name,
        cl."id"         AS courselesson_id,
        cl."title"      AS courselesson_name
    FROM "courses" c
    LEFT JOIN "CourseModule" cm
        ON cm."courseId" = c."id" AND cm."tenant_name" = c."tenant_name" AND cm."status" = 'Live'
    LEFT JOIN "CourseLesson" cl
        ON cl."courseModuleId" = cm."id" AND cl."tenant_name" = c."tenant_name" AND cl."status" = 'Live'
    WHERE c."status" = 'Live'
),

user_assignment AS (
    -- Individual
    SELECT eu."A" AS enrolledusers_course_id, eu."B" AS enrolledusers_user_id, um."username" AS usermaster_username,
            eu."tenant_name" AS enrolledusers_tenant_name, 'Individual' AS assignment_source, um."username" AS source_name
    FROM "enrolledusers" eu
    LEFT JOIN "userMaster" um ON um."id" = eu."B" AND um."tenant_name" = eu."tenant_name"
    WHERE um."status" = 1
    UNION ALL
    -- Department
    SELECT ctd."A", um."id", um."username", ctd."tenant_name", 'Department', d."name"
    FROM "CourseTodepartment" ctd
    LEFT JOIN "departmentTorolePolicy" dtp ON dtp."A" = ctd."B" AND dtp."tenant_name" = ctd."tenant_name"
    LEFT JOIN "userMaster" um ON um."roleId" = dtp."B" AND um."tenant_name" = ctd."tenant_name"
    LEFT JOIN "department" d ON d."id" = ctd."B" AND d."status" = 1
    WHERE um."status" = 1
    UNION ALL
    -- Designation
    SELECT ctd."A", um."id", um."username", ctd."tenant_name", 'Designation', des."name"
    FROM "CourseTodesignation" ctd
    LEFT JOIN "userMaster" um ON um."designationId" = ctd."B" AND um."tenant_name" = ctd."tenant_name"
    LEFT JOIN "designation" des ON des."id" = um."designationId" AND des."status" = 1
    WHERE um."status" = 1
    UNION ALL
    -- Batch
    SELECT btc."B", um."id", um."username", btc."tenant_name", 'Batch', b."name"
    FROM "BatchToCourse" btc
    LEFT JOIN "BatchTouserMaster" btum ON btum."A" = btc."A" AND btum."tenant_name" = btc."tenant_name"
    LEFT JOIN "userMaster" um ON um."id" = btum."B" AND um."tenant_name" = btc."tenant_name"
    LEFT JOIN "Batch" b ON b."id" = btc."A" AND b."status" = 1
    WHERE um."status" = 1
    UNION ALL
    -- Coach
    SELECT coach."A", um."id", um."username", coach."tenant_name", 'Coach', um."username"
    FROM "CourseTouserMaster" coach
    LEFT JOIN "userMaster" um ON um."id" = coach."B" AND um."tenant_name" = coach."tenant_name"
    WHERE um."status" = 1
),

course_progress AS (
    SELECT
        cp."courseId"         AS courseprogress_course_id,
        cp."userId"           AS courseprogress_user_id,
        cp."tenant_name"      AS courseprogress_tenant_name,
        lp."lessonId"         AS lessonprogress_lesson_id,
        lp."completionStatus" AS lessonprogress_status,
        cp."lastAccessedAt"   AS courseprogress_completed_at
    FROM "CourseProgress" cp
    LEFT JOIN "ModuleProgress" mp ON mp."courseProgressId" = cp."id" AND mp."tenant_name" = cp."tenant_name"
    LEFT JOIN "LessonProgress" lp ON lp."moduleProgressId" = mp."id" AND lp."tenant_name" = cp."tenant_name"
    WHERE lp."completionStatus" IS NOT NULL
),

base AS (
    SELECT
        cs.*,
        ua.enrolledusers_user_id,
        ua.usermaster_username,
        ua.assignment_source,
        ua.source_name,
        ua.enrolledusers_tenant_name,
        CASE WHEN cp.courseprogress_completed_at::text = '1970-01-01 05:30:00' THEN NULL
            ELSE cp.courseprogress_completed_at END AS final_completed_at,
        COALESCE(cp.lessonprogress_status, 'NotStarted') AS final_completion_status
    FROM course_structure cs
    LEFT JOIN user_assignment ua
        ON cs.courses_id = ua.enrolledusers_course_id AND cs.tenant_name = ua.enrolledusers_tenant_name
    LEFT JOIN course_progress cp
        ON cs.courselesson_id = cp.lessonprogress_lesson_id
        AND ua.enrolledusers_user_id = cp.courseprogress_user_id
        AND ua.enrolledusers_tenant_name = cp.courseprogress_tenant_name
),

-- All completion statuses computed at clean lesson grain (BEFORE quiz join -> no fan-out)
journey_base AS (
    SELECT
        base.*,
        CASE WHEN COUNT(*) OVER w2 = COUNT(CASE WHEN final_completion_status = 'Completed' THEN 1 END) OVER w2 THEN 'Completed'
            WHEN COUNT(*) OVER w2 = COUNT(CASE WHEN final_completion_status = 'NotStarted' THEN 1 END) OVER w2 THEN 'NotStarted'
            ELSE 'InProgress' END AS final_course_all_user_status,
        CASE WHEN COUNT(*) OVER w1 = COUNT(CASE WHEN final_completion_status = 'Completed' THEN 1 END) OVER w1 THEN 'Completed'
            WHEN COUNT(*) OVER w1 = COUNT(CASE WHEN final_completion_status = 'NotStarted' THEN 1 END) OVER w1 THEN 'NotStarted'
            ELSE 'InProgress' END AS final_course_per_user_status,
        CASE WHEN COUNT(*) OVER w3 = COUNT(CASE WHEN final_completion_status = 'Completed' THEN 1 END) OVER w3 THEN 'Completed'
            WHEN COUNT(*) OVER w3 = COUNT(CASE WHEN final_completion_status = 'NotStarted' THEN 1 END) OVER w3 THEN 'NotStarted'
            ELSE 'InProgress' END AS final_user_status,
        CASE WHEN COUNT(*) OVER w4 = COUNT(CASE WHEN final_completion_status = 'Completed' THEN 1 END) OVER w4 THEN 'Completed'
            WHEN COUNT(*) OVER w4 = COUNT(CASE WHEN final_completion_status = 'NotStarted' THEN 1 END) OVER w4 THEN 'NotStarted'
            ELSE 'InProgress' END AS final_module_per_user_status,
        CASE WHEN COUNT(*) OVER w5 = COUNT(CASE WHEN final_completion_status = 'Completed' THEN 1 END) OVER w5 THEN 'Completed'
            WHEN COUNT(*) OVER w5 = COUNT(CASE WHEN final_completion_status = 'NotStarted' THEN 1 END) OVER w5 THEN 'NotStarted'
            ELSE 'InProgress' END AS final_module_all_user_status
    FROM base
    WINDOW
        w1 AS (PARTITION BY enrolledusers_tenant_name, courses_id, enrolledusers_user_id),
        w2 AS (PARTITION BY enrolledusers_tenant_name, courses_id),
        w3 AS (PARTITION BY enrolledusers_tenant_name, enrolledusers_user_id),
        w4 AS (PARTITION BY enrolledusers_tenant_name, coursemodule_id, enrolledusers_user_id),
        w5 AS (PARTITION BY enrolledusers_tenant_name, coursemodule_id)
),

-- One row per quiz PAGE -> supports MULTIPLE quizzes per lesson; dedupes only duplicate QuizAssignment matches
lesson_quiz AS (
    SELECT DISTINCT ON (p."id")
        p."courseLessonId"               AS courselesson_id,
        p."tenant_name",
        p."quizId"                       AS quiz_id,
        COALESCE(NULLIF(qa."title", ''), NULLIF(p."title", '')) AS quiz_title,
        qa."passingPercentage"           AS passing_percentage,
        qa."quizCompletionTimeInMinutes" AS total_time_allowed_minutes
    FROM "Page" p
    LEFT JOIN "QuizAssignment" qa ON qa."quizId" = p."quizId" AND qa."tenant_name" = p."tenant_name"
    WHERE p."type" = 'Quiz' AND p."quizId" IS NOT NULL AND p."quizId" <> ''
    ORDER BY p."id", qa."passingPercentage" DESC NULLS LAST
),

-- Per-submission overall % from question-level scores
qq_score AS (
    SELECT "submissionId", ROUND(SUM("finalScore") * 100.0 / NULLIF(SUM("score"), 0), 2) AS overall_percentage
    FROM "QuizQuestion"
    GROUP BY "submissionId"
),

-- Latest submitted attempt per (user, quiz)
subs AS (
    SELECT
        s."userId", s."quizId", s."tenant_name", s."id" AS submission_id,
        s."attemptNumber", s."submittedAt", qq.overall_percentage,
        ROW_NUMBER() OVER (PARTITION BY s."userId", s."quizId", s."tenant_name"
                            ORDER BY s."submittedAt" DESC NULLS LAST, s."attemptNumber" DESC) AS rn,
        COUNT(*) OVER (PARTITION BY s."userId", s."quizId", s."tenant_name") AS total_attempts
    FROM "Submission" s
    LEFT JOIN qq_score qq ON qq."submissionId" = s."id"
    WHERE s."isSubmitted" = 1
),
quiz_user AS (SELECT * FROM subs WHERE rn = 1),

-- Agent identity (email = downstream join key to sampark.employee_fact for TL/AM)
user_details AS (
    SELECT
        um."id"      AS user_id,
        um."username",
        um."emailId" AS email,
        um."tenant_name",
        d."name"     AS department_name,
        des."name"   AS designation_name
    FROM "userMaster" um
    LEFT JOIN "department" d ON d."id" = um."departmentId" AND d."tenant_name" = um."tenant_name"
    LEFT JOIN "designation" des ON des."id" = um."designationId" AND des."tenant_name" = um."tenant_name"
    WHERE um."status" = 1
)

SELECT
    -- unique row key for this grain (user x lesson x quiz)
    jb.enrolledusers_user_id || '|' || jb.courselesson_id || '|' || COALESCE(lq.quiz_id, '') AS journey_key,

    -- course / structure
    jb.tenant_name,
    jb.courses_id,
    jb.courses_name,
    jb.courses_assigned_date,
    jb.courses_created_at,
    jb.coursemodule_id,
    jb.coursemodule_name,
    jb.courselesson_id,
    jb.courselesson_name,

    -- agent identity + keys (TL/AM added downstream via email / usermaster_username)
    jb.enrolledusers_user_id,
    jb.usermaster_username,
    ud.email,
    ud.department_name,
    ud.designation_name,
    jb.assignment_source,
    jb.source_name,
    jb.enrolledusers_tenant_name,

    -- course / lesson completion (all original statuses preserved)
    jb.final_completed_at,
    jb.final_completion_status,
    jb.final_course_all_user_status,
    jb.final_course_per_user_status,
    jb.final_user_status,
    jb.final_module_per_user_status,
    jb.final_module_all_user_status,

    -- the quiz embedded on this lesson
    lq.quiz_id,
    COALESCE(lq.quiz_title, jb.courselesson_name) AS quiz_title,
    lq.passing_percentage,
    lq.total_time_allowed_minutes,

    -- quiz attempt + score + pass
    CASE WHEN lq.quiz_id IS NULL THEN NULL
        WHEN qu.submission_id IS NOT NULL THEN 'Attempted'
        ELSE 'Not Attempted' END AS attempt_status,
    qu."attemptNumber"    AS attempt_number,
    qu.total_attempts,
    qu."submittedAt"      AS attempted_at,
    qu.overall_percentage AS quiz_score,
    CASE WHEN qu.overall_percentage IS NULL THEN NULL
        WHEN qu.overall_percentage >= COALESCE(lq.passing_percentage, 70) THEN 'Pass'
        ELSE 'Fail' END  AS quiz_pass_status

FROM journey_base jb
LEFT JOIN lesson_quiz  lq ON lq.courselesson_id = jb.courselesson_id AND lq."tenant_name" = jb.enrolledusers_tenant_name
LEFT JOIN quiz_user    qu ON qu."userId" = jb.enrolledusers_user_id AND qu."quizId" = lq.quiz_id AND qu."tenant_name" = jb.enrolledusers_tenant_name
LEFT JOIN user_details ud ON ud.user_id = jb.enrolledusers_user_id AND ud."tenant_name" = jb.enrolledusers_tenant_name

ORDER BY jb.enrolledusers_tenant_name, jb.courses_name, jb.usermaster_username, jb.coursemodule_name, jb.courselesson_name, lq.quiz_id;

"""

# =============================================================
# THIS IS THE MAIN CONFIG
# =============================================================

FACT_CONFIG = {
    "lms_fact_user_x_lesson" : {
        "query" : lms_fact_user_x_lesson_query,
        "destination_table" : "lms_fact_user_x_lesson",
    },
  
    "lms_fact_quiz_assigned" : {
        "query" : lms_fact_quiz_assigned_query,
        "destination_table" : "lms_fact_quiz_assigned",
    },
  
    "lms_fact_quiz_submitted" : {
        "query" : lms_fact_quiz_submitted_query,
        "destination_table" : "lms_fact_quiz_submitted",
    },

   "lms_fact_agent_journey": {
       "query": lms_fact_agent_journey_query,
       "destination_table": "lms_fact_agent_journey",
  },
}
