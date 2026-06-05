
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


