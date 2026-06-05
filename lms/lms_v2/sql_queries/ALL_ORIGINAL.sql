
-- THIS IS THE FINAL QUERY ->

WITH course_structure AS (
    SELECT 
        c."id" as course_id,
        c."name" as course_name,
        c."description" as course_description,
        -- c."startDate" as course_startDate,
        -- c."endDate" as course_endDate,
        -- c."isMandatory" as course_isMandatory,
        c."status" as course_status,
        c."createdAt" as course_createdAt,
        -- c."modifiedAt" as course_modifiedAt,
        -- c."languageMasterId" as course_languageMasterId,
        c."avgRating" as course_avgRating,
        -- c."authorId" as course_authorId,
        c."client_name" as course_client_name,

        cm."id" as module_id,
        cm."title" as module_title,
        cm."status" as module_status,
        cm."createdAt" as module_createdAt,
        -- cm."modifiedAt" as module_modifiedAt,
        -- cm."client_name" as module_client_name,

        cl."id" as lesson_id,
        cl."title" as lesson_title,
        cl."status" as lesson_status,
        cl."createdAt" as lesson_createdAt,
        -- cl."modifiedAt" as lesson_modifiedAt,
        -- cl."client_name" as lesson_client_name

    FROM "courses" c
    LEFT JOIN "CourseModule" cm
    ON c."id" = cm."courseId"

    LEFT JOIN "CourseLesson" cl
    ON cm."id" = cl."courseModuleId"
),

user_assignment AS (
    SELECT 
        eu."A" as enrolledusers_course_id,
        eu."B" as enrolledusers_user_id,

        um."departmentId" as user_department_id,
        um."designationId" as user_designation_id,
        -- um."emailId" as user_emailId,
        -- um."fullName" as user_fullName,
        -- um."isMasterEntry" as user_isMasterEntry,
        -- um."createdAt" as user_createdAt,
        -- um."modifiedAt" as user_modifiedAt,
        -- um."status" as user_status,
        um."username" as user_username,
        -- um."locationId" as user_locationId,
        um."client_name" as user_client_name,

        dep."code" as department_code,
        -- dep."isMasterEntry" as department_isMasterEntry,
        -- dep."createdAt" as department_createdAt,
        -- dep."modifiedAt" as department_modifiedAt,
        dep."name" as department_name,
        dep."shortDesc" as department_shortDesc,
        -- dep."status" as department_status,
        dep."quizId" as department_quizId,
        -- dep."client_name" as department_client_name,

        deg."code" as designation_code,
        -- deg."createdAt" as designation_createdAt,
        -- deg."departmentId" as designation_departmentId,
        -- deg."isMasterEntry" as designation_isMasterEntry,
        -- deg."modifiedAt" as designation_modifiedAt,
        deg."name" as designation_name,
        deg."shortDesc" as designation_shortDesc,
        -- deg."status" as designation_status,
        -- deg."client_name" as designation_client_name,

        btm."A" as batch_id,

        b."name" as batch_name,
        b."description" as batch_description,
        -- b."startDate" as batch_startDate,
        -- b."endDate" as batch_endDate,
        -- b."status" as batch_status,
        b."createdAt" as batch_createdAt,
        -- b."modifiedAt" as batch_modifiedAt,
        -- b."client_name" as batch_client_name

    FROM "enrolledusers" eu

    LEFT JOIN "userMaster" um
    ON eu."B" = um."id"

    LEFT JOIN "department" dep
    ON um."departmentId" = dep."id"

    LEFT JOIN "designation" deg
    ON um."designationId" = deg."id"

    LEFT JOIN "BatchTouserMaster" btm
    ON eu."B" = btm."B"

    LEFT JOIN "Batch" b
    ON btm."A" = b."id"

),

course_progress AS (
    SELECT
        cp."id" as course_progress_id,
        cp."courseId" as course_progress_course_id,
        cp."userId" as course_progress_user_id,
        -- cp."completionStatus" as course_progress_completionStatus,
        -- cp."memberId" as course_progress_memberId,
        -- cp."startedAt" as course_progress_startedAt,
        -- cp."lastAccessedAt" as course_progress_lastAccessedAt,
        -- cp."completedAt" as course_progress_completedAt,
        -- cp."client_name" as course_progress_client_name,

        mp."id" as module_progress_id,
        mp."courseProgressId" as module_progress_course_progress_id,
        -- mp."courseModuleId" as module_progress_module_id,
        -- mp."completionStatus" as module_progress_completionStatus,
        -- mp."startedAt" as module_progress_startedAt,
        -- mp."lastAccessedAt" as module_progress_lastAccessedAt,
        -- mp."completedAt" as module_progress_completedAt,
        -- mp."client_name" as module_progress_client_name,

        lp."id" as lesson_progress_id,
        lp."lessonId" as lesson_progress_lesson_id,
        lp."moduleProgressId" as lesson_progress_module_progress_id,
        lp."completionStatus" as lesson_progress_completionStatus,
        lp."startedAt" as lesson_progress_startedAt,
        -- lp."lastAccessedAt" as lesson_progress_lastAccessedAt,
        lp."completedAt" as lesson_progress_completedAt,
        lp."client_name" as lesson_progress_client_name

    FROM "CourseProgress" cp
    LEFT JOIN "ModuleProgress" mp
        ON cp."id" = mp."courseProgressId"
    LEFT JOIN "LessonProgress" lp
        ON mp."id" = lp."moduleProgressId"
)

, base AS (
    SELECT
        cs.*,
        ua.*,
        cp.*,

        COALESCE(cp.lesson_progress_completionStatus, 'NotStarted') 
            AS final_lesson_completion_status

    FROM course_structure cs

    LEFT JOIN user_assignment ua
        ON cs.course_id = ua.enrolledusers_course_id

    LEFT JOIN course_progress cp
        ON cs.lesson_id = cp.lesson_progress_lesson_id
        AND ua.enrolledusers_user_id = cp.course_progress_user_id

)

SELECT
    base.*,

    --  USER COURSE STATUS (per user per course)
    CASE
        WHEN COUNT(*) OVER w1 = COUNT(CASE WHEN final_lesson_completion_status = 'Completed' THEN 1 END) OVER w1
            THEN 'Completed'

        WHEN COUNT(*) OVER w1 = COUNT(CASE WHEN final_lesson_completion_status = 'NotStarted' THEN 1 END) OVER w1
            THEN 'NotStarted'

        ELSE 'InProgress'
    END AS final_course_per_user_status,

    --  COURSE STATUS (overall course)
    CASE
        WHEN COUNT(*) OVER w2 = COUNT(CASE WHEN final_lesson_completion_status = 'Completed' THEN 1 END) OVER w2
            THEN 'Completed'

        WHEN COUNT(*) OVER w2 = COUNT(CASE WHEN final_lesson_completion_status = 'NotStarted' THEN 1 END) OVER w2
            THEN 'NotStarted'

        ELSE 'InProgress'
    END AS final_course_all_user_status,

    --  USER STATUS (overall user)
    CASE
        WHEN COUNT(*) OVER w3 = COUNT(CASE WHEN final_lesson_completion_status = 'Completed' THEN 1 END) OVER w3
            THEN 'Completed'

        WHEN COUNT(*) OVER w3 = COUNT(CASE WHEN final_lesson_completion_status = 'NotStarted' THEN 1 END) OVER w3
            THEN 'NotStarted'

        ELSE 'InProgress'
    END AS final_user_status,

    -- MODULE STATUS (per user)
    CASE
        WHEN COUNT(*) OVER w4 = COUNT(CASE WHEN final_lesson_completion_status = 'Completed' THEN 1 END) OVER w4
            THEN 'Completed'

        WHEN COUNT(*) OVER w4 = COUNT(CASE WHEN final_lesson_completion_status = 'NotStarted' THEN 1 END) OVER w4
            THEN 'NotStarted'

        ELSE 'InProgress'
    END AS final_module_per_user_status,

    -- MODULE STATUS (overall)
    CASE
        WHEN COUNT(*) OVER w5 = COUNT(CASE WHEN final_lesson_completion_status = 'Completed' THEN 1 END) OVER w5
            THEN 'Completed'

        WHEN COUNT(*) OVER w5 = COUNT(CASE WHEN final_lesson_completion_status = 'NotStarted' THEN 1 END) OVER w5
            THEN 'NotStarted'

        ELSE 'InProgress'
    END AS final_module_all_user_status

FROM base

WINDOW
    w1 AS (PARTITION BY course_id, enrolledusers_user_id),
    w2 AS (PARTITION BY course_id),
    w3 AS (PARTITION BY enrolledusers_user_id),
    w4 AS (PARTITION BY module_id,enrolledusers_user_id),
    w5 AS (PARTITION BY module_id);

