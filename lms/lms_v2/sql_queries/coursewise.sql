select assign.*, case when toString(progress.`completed_at`) in '1970-01-01 05:30:00' THEN '-' ELSE toString(progress.`completed_at`) END AS completed_at,
case WHEN progress.`completion_status`!='' THEN progress.`completion_status` ELSE 'NotStarted' END AS completion_status,
CASE 
    WHEN COUNT(*) OVER w = COUNT(CASE WHEN completion_status = 'Completed' THEN 1 END) OVER w THEN 'Completed'
    WHEN COUNT(*) OVER w = COUNT(CASE WHEN completion_status = 'NotStarted' THEN 1 END) OVER w THEN 'NotStarted'
    ELSE 'InProgress'
  END AS course_status,
CASE 
    WHEN COUNT(*) OVER w1 = COUNT(CASE WHEN completion_status = 'Completed' THEN 1 END) OVER w1 THEN 'Completed'
    WHEN COUNT(*) OVER w1 = COUNT(CASE WHEN completion_status = 'NotStarted' THEN 1 END) OVER w1 THEN 'NotStarted'
    ELSE 'InProgress'
  END AS user_course_status,
  CASE 
    WHEN COUNT(*) OVER w2 = COUNT(CASE WHEN completion_status = 'Completed' THEN 1 END) OVER w2 THEN 'Completed'
    WHEN COUNT(*) OVER w2 = COUNT(CASE WHEN completion_status = 'NotStarted' THEN 1 END) OVER w2 THEN 'NotStarted'
    ELSE 'InProgress'
  END AS user_status


FROM 
(select cd.*, eu.user_id as user_id, eu.username as username, eu.source as source, eu.`Source Name`  from
(
select c.`id` AS course_id, c.`name` AS course_name, c.`startDate` as assigned_date, c.`createdAt` AS course_created_at,cm.`id` AS module_id,cm.`title` AS module_name,
cl.`id` AS lesson_id, cl.`title` AS lesson_name 
from courses c
LEFT OUTER JOIN CourseModule cm
ON c.`id`=cm.`courseId` 
LEFT OUTER JOIN CourseLesson cl
ON cm.`id`=cl.`courseModuleId`
WHERE c.status='Live' and cm.`id`!='' and cl.`id`!='' and cm.status='Live' and cl.status='Live')cd
LEFT OUTER JOIN 

    (
        select A as course_id, B AS user_id, um.username AS username,'Individual Assignment' AS source, um.username AS `Source Name`  from enrolledusers eu
    LEFT OUTER JOIN userMaster um
    on um.`id`=user_id 
    WHERE um.`status`=1
    
    union all
    
    select ctd.course as course_id, um.id as user_id, um.username AS username,'Department Assignment' AS source, d.`name` AS  `Source Name`  FROM 
    (select A AS course, B as department_id from CourseTodepartment ctd) ctd
    LEFT OUTER JOIN 
    (select A as department_id, B as role FROM departmentTorolePolicy )dtp 
    ON ctd.department_id=dtp.department_id
    LEFT outer JOIN 
    (select id, username,roleId, status FROM userMaster) um
    ON dtp.role=um.roleId
    LEFT OUTER JOIN (select id, name from department where status=1) d
    on d.id=ctd.department_id
    WHERE um.status=1
    
    union all
    
    select ctdesig.A as course_id, um.id as user_id, um.username,'Designation Assignment' AS source, d.name as `Source Name`  from CourseTodesignation ctdesig
    LEFT OUTER JOIN userMaster  um
    ON ctdesig.B=um.designationId
    LEFT OUTER JOIN (select id, name from designation WHERE status=1 )d
    on d.id=um.designationId
    WHERE um.status=1
    
    union all
    
    select btc.course_id as course_id, um.user_id as user_id, um.username AS username, 'Batch Assignment' as source, B.name AS `Source Name`  FROM 
    (select A as batch_name_id, B as course_id FROM BatchToCourse )btc
    LEFT outer JOIN 
    (SELECT id as batch_name_id, name as batch_name, status FROM Batch )b
    ON btc.batch_name_id = b.batch_name_id
    LEFT outer JOIN 
    (select A as batch_name_id, B as user_id FROM BatchTouserMaster )btum
    ON btc.batch_name_id=btum.batch_name_id
    LEFT OUTER JOIN 
    (SELECT id AS user_id, status, username from userMaster WHERE status=1)um
    ON btum.user_id=um.user_id 
    LEFT OUTER JOIN (select id, name from Batch WHERE status=1)B
    ON B.id=btc.batch_name_id
    WHERE user_id!='' 
    
    union all
    
    select coach.course_id AS course_id, um.user_id as user_id, um.username as username, 'Coach Assignment' as source, um.username AS `Source Name` FROM 
    (select A as course_id, B as coach_user_id from CourseTouserMaster )coach
    LEFT OUTER JOIN 
    (SELECT id AS user_id, status, username from userMaster WHERE status=1)um
    ON coach.coach_user_id=um.user_id 
    WHERE user_id!=''
    ) eu
on eu.`course_id`=cd.`course_id`)assign
LEFT OUTER JOIN 
(
SELECT cp.`id` AS courseprogress_id,cp.`courseId` AS course_id, cp.`userId` AS user_id, cp.`lastAccessedAt` AS completed_at, lp.`lessonId` AS lesson_id,
lp.`completionStatus` AS completion_status  
FROM CourseProgress cp
LEFT OUTER JOIN ModuleProgress mp ON cp.`id`=mp.`courseProgressId`
LEFT OUTER JOIN LessonProgress lp ON mp.`id`=lp.`moduleProgressId`
where completion_status!='')progress
on assign.`lesson_id`=progress.`lesson_id` AND assign.user_id=progress.user_id
WINDOW w AS (PARTITION BY course_id),
 w1 AS (PARTITION BY course_id, user_id),
 w2 AS (PARTITION BY user_id) 