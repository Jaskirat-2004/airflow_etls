SELECT 
    full.*, 
    langmaster.`name` AS `Language`
FROM 
    (
        SELECT 
            out.*, 
            um.`username` AS `User Awarded`,
            um.`departmentId` AS `user_department_id`
        FROM 
            (
                SELECT 
                    main.*, 
                    cp.`userId`, 
                    cp.`completionStatus`,
                    cp.`completedAt` AS `Awarded Date`
                FROM 
                    (
                        SELECT 
                            cert.`id` AS `id`, 
                            cert.`name` AS `Certificate Name`, 
                            CASE 
                                WHEN cert.`status` = 1 THEN 'Active' 
                                ELSE 'In-Active' 
                            END AS `Certificate Status`, 
                            cert.`type` AS `Certificate Type`, 
                            cert.`createdAt`, 
                            cert.`modifiedAt`, 
                            course.`id` AS `course_id`, 
                            course.`name` AS `Linked Course Name`, 
                            course.`startDate`, 
                            course.`endDate`, 
                            course.`status` AS `course_status`, 
                            course.`certificateId` AS `certificateId`,
                            lang.`B` AS `langid`  -- Language ID from CertificateTolanguageMaster
                        FROM 
                            Certificate AS cert
                        LEFT OUTER JOIN 
                            courses AS course 
                            ON cert.`id` = course.`certificateId` 
                            AND course.`status` = 'Live'  -- Only live courses
                        LEFT OUTER JOIN 
                            CertificateTolanguageMaster AS lang
                            ON cert.`id` = lang.`A`  -- Language mapping for the certificate
                        WHERE 
                            cert.`status` = 1  -- Only active certificates
                    ) AS main
                LEFT OUTER JOIN 
                    CourseProgress AS cp
                    ON main.`course_id` = cp.`courseId`
                    AND cp.`completionStatus` = 'Completed'  -- Only completed courses
            ) AS out
        LEFT OUTER JOIN 
            userMaster AS um
            ON out.`userId` = um.`id`  -- Fetching username for the certificate creator
    ) AS full
LEFT OUTER JOIN 
    languageMaster AS langmaster
    ON full.`langid` = langmaster.`id`  -- Fetching the language name from languageMaster
--WHERE (CASE WHEN '{{ url_param("departmentId") }}'='' THEN TRUE ELSE `user_department_id` = '{{ url_param("departmentId") }}' END)
 