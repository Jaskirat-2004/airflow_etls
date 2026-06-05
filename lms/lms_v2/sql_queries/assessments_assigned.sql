SELECT 
    qm.`Title` AS `Assessment Title`,
    qm.`StartDate` AS `Start Date`,
    qm.`EndDate` AS `End Date`,
    ddu.`Department` AS `Department`,
    ddu.`Username` AS `Username`,
    ddu.`Designation` AS `Designation`,
    qm.`ModifiedAt` AS `modifiedAt`,
    CASE
        WHEN qm.`Status` = 0 THEN 'Uploaded for approval'
        WHEN qm.`Status` = 1 THEN 'Active'
        WHEN qm.`Status` = 2 THEN 'Deleted'
        WHEN qm.`Status` = 3 THEN 'Drafts'
        WHEN qm.`Status` = 6 THEN 'Scheduled'
    END AS `Quiz Status`,
    CASE
        WHEN sub.`Attempted At` = '1970-01-01' THEN '-'
        ELSE toString(sub.`Attempted At`)
    END AS `Attempted At`,
    CASE
        WHEN sub.`isSubmitted` = true THEN 'Attempted'
        ELSE 'Not Attempted'
    END AS `Attempt Status`
FROM (

    -- 🧩 Branch 1: Quizzes assigned to individual users
    SELECT 
        qa.`quizid`,
        qa.`Assignid`,
        qa.`Title`,
        qa.`Status`,
        qa.`ModifiedAt`,
        qa.`StartDate`,
        qa.`EndDate`,
        qa.`quizCompletionTimeInMinutes`,
        qa.`passingPercentage`,
        qa.`quizAttemptLimit`,
        atu.`B` AS `userid`
    FROM (
        SELECT 
            `quizId` AS `quizid`,
            `title` AS `Title`,
            `status` AS `Status`,
            `modifiedAt` AS `ModifiedAt`,
            `startDate` AS `StartDate`,
            `endDate` AS `EndDate`,
            `id` AS `Assignid`,
            `quizCompletionTimeInMinutes`,
            `passingPercentage`,
            `quizAttemptLimit`,
            `bindToDept`
        FROM `kmdemo`.`QuizAssignment`
        WHERE `status` IN (0, 1, 6)
          AND CAST(`bindToDept` AS INT) = 0
    ) qa
    LEFT JOIN `kmdemo`.`QuizAssignmentTouserMaster` atu
        ON qa.`Assignid` = atu.`A`

    UNION ALL

    -- 🧩 Branch 2: Quizzes assigned to entire departments
    SELECT 
        qa.`quizid`,
        qa.`Assignid`,
        qa.`Title`,
        qa.`Status`,
        qa.`ModifiedAt`,
        qa.`StartDate`,
        qa.`EndDate`,
        qa.`quizCompletionTimeInMinutes`,
        qa.`passingPercentage`,
        qa.`quizAttemptLimit`,
        um.`id` AS `userid`
    FROM (
        SELECT 
            `quizId` AS `quizid`,
            `title` AS `Title`,
            `status` AS `Status`,
            `modifiedAt` AS `ModifiedAt`,
            `startDate` AS `StartDate`,
            `endDate` AS `EndDate`,
            `id` AS `Assignid`,
            `quizCompletionTimeInMinutes`,
            `passingPercentage`,
            `quizAttemptLimit`,
            `bindToDept`
        FROM `kmdemo`.`QuizAssignment`
        WHERE `status` IN (0, 1, 6)
          AND CAST(`bindToDept` AS INT) = 1
    ) qa
    LEFT JOIN `kmdemo`.`quiz_departments` qd
        ON qa.`quizid` = qd.`A`
    LEFT JOIN `kmdemo`.`userMaster` um
        ON um.`departmentId` = qd.`B`
        AND um.`status` = 1

) AS qm

-- 🧍 User and department details
LEFT JOIN (
    SELECT 
        dept.`Department Name` AS `Department`,
        dept.`departmentId` AS `departmentid`,
        UM.`UserId` AS `UserID`,
        UM.`username` AS `Username`,
        UM.`departmentId` AS `user_department_id`,
        desig.`designation` AS `Designation`
    FROM (
        SELECT 
            `id` AS `UserId`,
            `departmentId`,
            `designationId`,
            `username`
        FROM `kmdemo`.`userMaster`
        WHERE `status` = 1
    ) UM
    LEFT JOIN (
        SELECT 
            `name` AS `Department Name`,
            `id` AS `departmentId`
        FROM `kmdemo`.`department`
    ) dept ON dept.`departmentId` = UM.`departmentId`
    LEFT JOIN (
        SELECT 
            `id`,
            `name` AS `designation`
        FROM `kmdemo`.`designation`
    ) desig ON UM.`designationId` = desig.`id`
) AS ddu 
    ON ddu.`UserID` = qm.`userid`

-- 🧾 Submission join (tracks attempts)
LEFT JOIN (
    SELECT 
        `quizId`,
        `quizAssignmentId`,
        `userId`,
        CAST(`isSubmitted` AS Boolean) AS `isSubmitted`,
        MAX(`submittedAt`) AS `Attempted At`
    FROM `kmdemo`.`Submission`
    WHERE CAST(`isSubmitted` AS Boolean) = true
      AND `quizAssignmentId` IS NOT NULL
    GROUP BY `quizId`, `quizAssignmentId`, `userId`, `isSubmitted`
) AS sub 
    ON sub.`quizId` = qm.`quizid`
    AND sub.`quizAssignmentId` = qm.`Assignid`
    AND sub.`userId` = qm.`userid`
WHERE ddu.`Department` != '' AND toDate(`modifiedAt`)>= today() - INTERVAL 90 DAY
