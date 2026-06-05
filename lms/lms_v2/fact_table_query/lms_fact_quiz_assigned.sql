-- ######################################################################################
-- THIS ONE IS WORKING


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



-- #################################################################################################
-- #################################################################################################
-- #################################################################################################
-- #################################################################################################

-- THIS ONE RETURNS DATA 
-- NO LMS LINK THE COURSE IDS ARE NULL IN THE ABOVE SO NO DTA RETURNED ON JOIN

WITH quiz_assignments AS (
    SELECT
        qa."quizId"                      AS quizid,
        qa."id"                          AS assign_id,
        qa."title"                       AS title,
        qa."status"                      AS status,
        qa."modifiedAt"                  AS modified_at,
        qa."quizCompletionTimeInMinutes" AS completion_time_minutes,
        qa."passingPercentage"           AS passing_percentage,
        qa."quizAttemptLimit"            AS attempt_limit,
        qa."tenant_name"                 AS tenant_name,
        atu."B"                          AS user_id
    FROM "QuizAssignment" qa
    LEFT JOIN "QuizAssignmentTouserMaster" atu
        ON atu."A"           = qa."id"
        AND atu."tenant_name" = qa."tenant_name"
    WHERE qa."status" IN (0, 1, 6)
      AND CAST(qa."bindToDept" AS INT) = 0

    UNION ALL

    SELECT
        qa."quizId",
        qa."id",
        qa."title",
        qa."status",
        qa."modifiedAt",
        qa."quizCompletionTimeInMinutes",
        qa."passingPercentage",
        qa."quizAttemptLimit",
        qa."tenant_name",
        um."id" AS user_id
    FROM "QuizAssignment" qa
    LEFT JOIN "quiz_departments" qd
        ON qd."A"            = qa."quizId"
        AND qd."tenant_name"  = qa."tenant_name"
    LEFT JOIN "userMaster" um
        ON um."departmentId"  = qd."B"
        AND um."tenant_name"  = qa."tenant_name"
        AND um."status"       = 1
    WHERE qa."status" IN (0, 1, 6)
      AND CAST(qa."bindToDept" AS INT) = 1
),

user_details AS (
    SELECT
        um."id"           AS user_id,
        um."username"     AS username,
        um."departmentId" AS department_id,
        um."tenant_name",
        d."name"          AS department_name,
        des."name"        AS designation_name
    FROM "userMaster" um
    LEFT JOIN "department" d
        ON d."id"          = um."departmentId"
        AND d."tenant_name" = um."tenant_name"
    LEFT JOIN "designation" des
        ON des."id"          = um."designationId"
        AND des."tenant_name" = um."tenant_name"
    WHERE um."status" = 1
),

latest_submission AS (
    SELECT
        "quizId",
        "quizAssignmentId",
        "userId",
        "tenant_name",
        1                  AS is_submitted,
        MAX("submittedAt") AS attempted_at
    FROM "Submission"
    WHERE "isSubmitted" = 1
      AND "quizAssignmentId" IS NOT NULL
    GROUP BY "quizId", "quizAssignmentId", "userId", "tenant_name"
)

SELECT
    qa.quizid            AS quiz_id,
    qa.assign_id         AS quiz_assignment_id,
    qa.title             AS assessment_title,
    qa.modified_at,
    qa.tenant_name,

    CASE qa.status
        WHEN 0 THEN 'Uploaded for approval'
        WHEN 1 THEN 'Active'
        WHEN 2 THEN 'Deleted'
        WHEN 3 THEN 'Drafts'
        WHEN 6 THEN 'Scheduled'
    END                  AS quiz_status,

    ud.user_id,
    ud.username,
    ud.department_name,
    ud.designation_name,

    CASE
        WHEN sub.attempted_at IS NULL              THEN NULL
        WHEN DATE(sub.attempted_at) = '1970-01-01' THEN NULL
        ELSE sub.attempted_at
    END                  AS attempted_at,

    CASE
        WHEN sub.is_submitted = 1 THEN 'Attempted'
        ELSE 'Not Attempted'
    END                  AS attempt_status

FROM quiz_assignments qa
LEFT JOIN user_details ud
    ON ud.user_id      = qa.user_id
    AND ud.tenant_name = qa.tenant_name
LEFT JOIN latest_submission sub
    ON sub."quizId"            = qa.quizid
    AND sub."quizAssignmentId" = qa.assign_id
    AND sub."userId"           = qa.user_id
    AND sub.tenant_name        = qa.tenant_name
WHERE ud.department_name IS NOT NULL
  AND ud.department_name != ''
  AND qa.modified_at >= NOW() - INTERVAL '90 days';   