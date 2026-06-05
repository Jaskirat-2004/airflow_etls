SELECT 
    CONCAT(combinedtab.`subId`, '-', usermastertab.`Username`) AS `pkey`,
    usermastertab.`Username` AS `Username`,
    usermastertab.`departmentId` AS `user_department_id`,
    designationtab.`Designation Name` AS `Designation`,
    departmenttab.`Department Name` AS `Department`,
    CASE WHEN qassign.`title` ='' THEN combinedtab.`title` ELSE 
    qassign.`title` end AS `Assessment Title`,
    CASE
    WHEN (combinedtab.`isSubmitted` = true AND SA.`Submitted Answer` != '') THEN 'Submitted'
    WHEN (combinedtab.`isSubmitted` = true AND SA.`Submitted Answer` = '') THEN 'Duration Timeout'
    ELSE 'Not Submitted' END AS `Assessment Status`,
    combinedtab.`Total Time` AS `Total Time Allowed(In Minutes)`,
    combinedtab.`Question Type` AS `Question Type`,
    ROW_NUMBER() OVER (PARTITION BY `pkey` ORDER BY usermastertab.`Username`) AS `Question Number`,
    combinedtab.`Question` AS `Question`,
    SA.`Submitted Answer` AS `Submitted Answer`,
    CA.`Correct Answer` AS `Correct Answer`,
    combinedtab.`score` AS `Score`,
    combinedtab.`Overall Percentage` AS `Overall Percentage`,
    combinedtab.`attemptNumber` AS `Attempt Number`,
    QQA.`startTime` AS `StartDatetime`,
    toDate(`StartDatetime`) AS `StartDate`,
    formatDateTime(`StartDatetime`, '%H')||':'|| 
    CASE WHEN length(toString(toMinute(`StartDatetime`)))=1 THEN '0'||toString(toMinute(`StartDatetime`)) ELSE toString(toMinute(`StartDatetime`)) END 
    ||':'||
    formatDateTime(`StartDatetime`, '%S') AS `StartTime`,
    QQA.`endTime` AS `EndDatetime`,
    toDate(`EndDatetime`) AS `EndDate`,
    formatDateTime(`EndDatetime`, '%H')||':'|| 
    CASE WHEN length(toString(toMinute(`EndDatetime`)))=1 THEN '0'||toString(toMinute(`EndDatetime`)) ELSE toString(toMinute(`EndDatetime`)) END 
    ||':'||
    formatDateTime(`EndDatetime`, '%S') AS `EndTime`,
    CASE WHEN `isCorrect` THEN 'Correct' ELSE 'Incorrect' END AS `Answer Status`,
    dateDiff('millisecond',QQA.`startTime`,QQA.`endTime`) AS `TimeSpentOnQuestion`,
    concat(
    toString(intDiv(dateDiff('millisecond', QQA.startTime, QQA.endTime), 3600000)), ':',
    toString(intDiv(dateDiff('millisecond', QQA.startTime, QQA.endTime) % 3600000, 60000)), ':',
    toString(intDiv(dateDiff('millisecond', QQA.startTime, QQA.endTime) % 60000, 1000))
    ) AS `Time Spent On Question`,
    dateDiff('millisecond',combinedtab.`createdAt`,combinedtab.`submittedAt`) AS `TimeSpentOnAssessment`,
    concat(
    toString(intDiv(dateDiff('millisecond', combinedtab.`createdAt`, combinedtab.`submittedAt`), 3600000)), ':',
    toString(intDiv(dateDiff('millisecond', combinedtab.`createdAt`, combinedtab.`submittedAt`) % 3600000, 60000)), ':',
    toString(intDiv(dateDiff('millisecond', combinedtab.`createdAt`, combinedtab.`submittedAt`) % 60000, 1000))
    ) AS `Time Spent On Assessment`
    
FROM 
    (SELECT `id`, `name` AS `Designation Name` FROM `kmdemo`.`designation`) designationtab
LEFT OUTER JOIN 
    (SELECT `emailId` AS `Email ID`, `fullName` AS `FullName`, `username` AS `Username`, `designationId`, `id`, `departmentId` FROM `kmdemo`.`userMaster` WHERE `status`=1) usermastertab
ON 
    designationtab.`id` = usermastertab.`designationId`
LEFT OUTER JOIN 
    (SELECT `name` AS `Department Name`, `id` AS `departmentId` FROM `kmdemo`.`department`) departmenttab
ON 
    departmenttab.`departmentId` = usermastertab.`departmentId`
LEFT OUTER JOIN 
(select submissiontab.`subId` AS `subId`,submissiontab.`userId` AS `userId`, submissiontab.`title` AS `title`, submissiontab.`quizId` AS `quizId`,submissiontab.`score` AS `score`,
submissiontab.`Total Time` AS `Total Time`, submissiontab.`questionsLimit` AS `questionsLimit`, submissiontab.`isSubmitted` AS `isSubmitted`,submissiontab.`createdAt` AS `createdAt`,
submissiontab.`modifiedAt` AS `modifiedAt`,submissiontab.`submittedAt` AS `submittedAt`, avgscore.`Overall Percentage` AS `Overall Percentage`,submissiontab.`quizAssignmentId` AS `quizAssignmentId`,
submissiontab.`attemptNumber` AS `attemptNumber` ,quizques.`submissionId` AS `submissionId`, quizques.`Question` AS `Question`,quizques.`Question Type` AS `Question Type`,
quizques.`quizQuestionId` AS `quizQuestionId`,quizques.`isCorrect` AS `isCorrect`
 FROM 
(SELECT `id` AS `subId`, `userId`, `title`, `quizId`, `score` , `quizCompletionTimeInMinutes` AS `Total Time`, `questionsLimit`, `isSubmitted`, `createdAt`, `modifiedAt`, `submittedAt`,
 `quizAssignmentId`,`attemptNumber` FROM `kmdemo`.`Submission` WHERE CAST(`isSubmitted` AS Boolean) = true)submissiontab
    LEFT OUTER  JOIN 
(SELECT `submissionId`, replaceRegexpAll(replaceRegexpAll(`title`, '<[^>]*>', ''), '&nbsp;', ' ') AS `Question`, `type` AS `Question Type`, `id` AS `quizQuestionId`, `isCorrect`
FROM `kmdemo`.`QuizQuestion` )quizques
on submissiontab.`subId` = quizques.`submissionId`
 LEFT OUTER JOIN 
  (SELECT `submissionId`,SUM(`finalScore`)*100.0/SUM (`score`) AS `Overall Percentage` 
FROM `kmdemo`.`QuizQuestion`
 GROUP BY submissionId)avgscore
 ON quizques.`submissionId` = avgscore.`submissionId`) combinedtab
ON 
    usermastertab.`id` = combinedtab.`userId` 
LEFT OUTER JOIN 
    (SELECT `quizQuestionId`, arrayStringConcat(groupArray(`title`), ', ') AS `Correct Answer` FROM `kmdemo`.`CorrectAnswer` GROUP BY `quizQuestionId`) CA
ON 
    combinedtab.`quizQuestionId` = CA.`quizQuestionId`
LEFT OUTER JOIN 
    (SELECT `quizQuestionId`, arrayStringConcat(groupArray(`title`), ', ') AS `Submitted Answer` FROM `kmdemo`.`SubmittedAnswers` GROUP BY `quizQuestionId`) SA
ON 
    combinedtab.`quizQuestionId` = SA.`quizQuestionId` 
LEFT OUTER JOIN 
    (select `quizQuestionId`, max(`startTime`) AS `startTime`, max(`endTime`) AS `endTime` from `kmdemo`.`QuizQuestionAttempt` QQA group BY `quizQuestionId`) QQA
ON QQA.`quizQuestionId` = combinedtab.`quizQuestionId`
LEFT OUTER JOIN 
    `kmdemo`.`QuizAssignment` qassign 
ON qassign.`id`=combinedtab.`quizAssignmentId`
WHERE 
    combinedtab.`title` != '' AND `EndDate` NOT IN ('1970-01-01')
    and toDate(combinedtab.`submittedAt`)>= today() - INTERVAL 90 DAY
ORDER BY `Username`,`Department`