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