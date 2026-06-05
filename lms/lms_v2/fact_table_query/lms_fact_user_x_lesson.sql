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
    
    
    
    
-- ========================================================================================== 
-- ========================================================================================== 
-- ========================================================================================== 
-- ========================================================================================== 
-- ==========================================================================================

-- THIS IS THE OLD QUERY ->

WITH course_structure AS (
    SELECT 
        c."id" as courses_id,
        c."name" as courses_name,
        c."startDate" as courses_assigned_date,
        c."createdAt" as courses_created_at,
        c."tenant_name" as courses_tenant_name,

        cm."id" as coursemodule_id,
        cm."title" as coursemodule_name,

        cl."id" as courselesson_id,
        cl."title" as courselesson_name,
        cl."tenant_name" as courselesson_tenant_name

    FROM "courses" c

    LEFT JOIN "CourseModule" cm
        ON cm."courseId" = c."id"
        AND cm."tenant_name" = c."tenant_name"
        AND cm."status" = 'Live'

    LEFT JOIN "CourseLesson" cl
        ON cl."courseModuleId" = cm."id"
        AND cl."tenant_name" = c."tenant_name"
        AND cl."status" = 'Live'

    WHERE c."status" = 'Live'
),

user_assignment AS (

    -- Individual
    SELECT 
        eu."A" as enrolledusers_course_id,
        eu."B" as enrolledusers_user_id,
        um."username" as usermaster_username,
        eu."tenant_name" as enrolledusers_tenant_name,
        'Individual' as assignment_source
    FROM "enrolledusers" eu
    LEFT JOIN "userMaster" um
        ON um."id" = eu."B"
        AND um."tenant_name" = eu."tenant_name"
        AND um."status" = 1

    UNION ALL

    -- Department
    SELECT 
        ctd."A",
        um."id",
        um."username",
        ctd."tenant_name",
        'Department'
    FROM "CourseTodepartment" ctd
    LEFT JOIN "departmentTorolePolicy" dtp
        ON dtp."A" = ctd."B"
        AND dtp."tenant_name" = ctd."tenant_name"
    LEFT JOIN "userMaster" um
        ON um."roleId" = dtp."B"
        AND um."tenant_name" = ctd."tenant_name"
        AND um."status" = 1

    UNION ALL

    -- Designation
    SELECT 
        ctd."A",
        um."id",
        um."username",
        ctd."tenant_name",
        'Designation'
    FROM "CourseTodesignation" ctd
    LEFT JOIN "userMaster" um
        ON um."designationId" = ctd."B"
        AND um."tenant_name" = ctd."tenant_name"
        AND um."status" = 1

    UNION ALL

    -- Batch
    SELECT 
        btc."B",
        um."id",
        um."username",
        btc."tenant_name",
        'Batch'
    FROM "BatchToCourse" btc
    LEFT JOIN "BatchTouserMaster" btum
        ON btum."A" = btc."A"
        AND btum."tenant_name" = btc."tenant_name"
    LEFT JOIN "userMaster" um
        ON um."id" = btum."B"
        AND um."tenant_name" = btc."tenant_name"
        AND um."status" = 1

    UNION ALL

    -- Coach
    SELECT 
        coach."A",
        um."id",
        um."username",
        coach."tenant_name",
        'Coach'
    FROM "CourseTouserMaster" coach
    LEFT JOIN "userMaster" um
        ON um."id" = coach."B"
        AND um."tenant_name" = coach."tenant_name"
        AND um."status" = 1
),

course_progress AS (
    SELECT
        cp."courseId" as courseprogress_course_id,
        cp."userId" as courseprogress_user_id,
        cp."tenant_name" as courseprogress_tenant_name,

        lp."lessonId" as lessonprogress_lesson_id,
        lp."completionStatus" as lessonprogress_status,
        cp."lastAccessedAt" as courseprogress_completed_at

    FROM "CourseProgress" cp

    LEFT JOIN "ModuleProgress" mp
        ON mp."courseProgressId" = cp."id"
        AND mp."tenant_name" = cp."tenant_name"

    LEFT JOIN "LessonProgress" lp
        ON lp."moduleProgressId" = mp."id"
        AND lp."tenant_name" = cp."tenant_name"

    WHERE lp."completionStatus" IS NOT NULL
),

base AS (
    SELECT
        cs.*,
        ua.enrolledusers_user_id,
        ua.usermaster_username,
        ua.assignment_source,
        ua.enrolledusers_tenant_name,

        CASE
            WHEN cp.courseprogress_completed_at::text = '1970-01-01 05:30:00' THEN NULL
            ELSE cp.courseprogress_completed_at
        END as final_completed_at,

        COALESCE(cp.lessonprogress_status, 'NotStarted') as final_completion_status

    FROM course_structure cs

    LEFT JOIN user_assignment ua
        ON cs.courses_id = ua.enrolledusers_course_id
        AND cs.tenant_name = ua.enrolledusers_tenant_name

    LEFT JOIN course_progress cp
        ON cs.courselesson_id = cp.lessonprogress_lesson_id
        AND ua.enrolledusers_user_id = cp.courseprogress_user_id
        AND ua.enrolledusers_tenant_name = cp.courseprogress_tenant_name
)

SELECT
    base.*,

    -- COURSE ALL USERS
    CASE
        WHEN COUNT(*) OVER w2 = COUNT(CASE WHEN final_completion_status = 'Completed' THEN 1 END) OVER w2
        THEN 'Completed'
        WHEN COUNT(*) OVER w2 = COUNT(CASE WHEN final_completion_status = 'NotStarted' THEN 1 END) OVER w2
        THEN 'NotStarted'
        ELSE 'InProgress'
    END as final_course_all_user_status,

    -- COURSE PER USER
    CASE
        WHEN COUNT(*) OVER w1 = COUNT(CASE WHEN final_completion_status = 'Completed' THEN 1 END) OVER w1
        THEN 'Completed'
        WHEN COUNT(*) OVER w1 = COUNT(CASE WHEN final_completion_status = 'NotStarted' THEN 1 END) OVER w1
        THEN 'NotStarted'
        ELSE 'InProgress'
    END as final_course_per_user_status,

    -- USER OVERALL
    CASE
        WHEN COUNT(*) OVER w3 = COUNT(CASE WHEN final_completion_status = 'Completed' THEN 1 END) OVER w3
        THEN 'Completed'
        WHEN COUNT(*) OVER w3 = COUNT(CASE WHEN final_completion_status = 'NotStarted' THEN 1 END) OVER w3
        THEN 'NotStarted'
        ELSE 'InProgress'
    END as final_user_status,

    -- MODULE PER USER
    CASE
        WHEN COUNT(*) OVER w4 = COUNT(CASE WHEN final_completion_status = 'Completed' THEN 1 END) OVER w4
        THEN 'Completed'
        WHEN COUNT(*) OVER w4 = COUNT(CASE WHEN final_completion_status = 'NotStarted' THEN 1 END) OVER w4
        THEN 'NotStarted'
        ELSE 'InProgress'
    END as final_module_per_user_status,

    -- MODULE ALL USERS
    CASE
        WHEN COUNT(*) OVER w5 = COUNT(CASE WHEN final_completion_status = 'Completed' THEN 1 END) OVER w5
        THEN 'Completed'
        WHEN COUNT(*) OVER w5 = COUNT(CASE WHEN final_completion_status = 'NotStarted' THEN 1 END) OVER w5
        THEN 'NotStarted'
        ELSE 'InProgress'
    END as final_module_all_user_status

FROM base

WINDOW
    w1 AS (PARTITION BY enrolledusers_tenant_name, courses_id, enrolledusers_user_id),
    w2 AS (PARTITION BY enrolledusers_tenant_name, courses_id),
    w3 AS (PARTITION BY enrolledusers_tenant_name, enrolledusers_user_id),
    w4 AS (PARTITION BY enrolledusers_tenant_name, coursemodule_id, enrolledusers_user_id),
    w5 AS (PARTITION BY enrolledusers_tenant_name, coursemodule_id)
