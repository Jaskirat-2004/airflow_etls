ENABLED_TABLES = [
    "courses",
    "CourseModule",
    "CourseLesson",
    "enrolledusers",
    "userMaster",
    "CourseTodepartment",
    "departmentTorolePolicy",
    "department",
    "CourseTodesignation",
    "BatchToCourse",
    "Batch",
    "BatchTouserMaster",
    "CourseTouserMaster",
    "CourseProgress",
    "ModuleProgress",
    "LessonProgress",
    "Certificate",
    "CertificateTolanguageMaster",
    "languageMaster",
    "designation",
    "QuizAssignment",
    "QuizAssignmentTouserMaster",
    "quiz_departments",
    "Submission",
    "QuizQuestion",
    "CorrectAnswer",
    "SubmittedAnswers",
    "QuizQuestionAttempt",
    "Page"
]

TENANTS = [
    "boat",
    "orientphygital",
    "wonderchefphygital",
    "urbancompany",
    "atomberg",
    "vivophygital",
    "lenovophygital",
    "eulermotors",
    "hafele",
    "kochiva"
]

TENNAT_MAPPER_SAMPARK = {

    "boat" : "boat",
    "orientphygital" : "orient",
    "wonderchefphygital" : "wonderchef",
    "urbancompany": "urban_company",
    "atomberg": "atomberg",
    "vivophygital": "vivo",
    "lenovophygital": "lenovo",
    "hafele": "hafele",
    "kochiva": "kochiva",

    # "maxicus": "maxicus",
    # "upliance": "upliance",
    # "borosil": "borosil",
    # "heromotocorp": "hero_moto",
    # "domesticappliances-philips": "philips",
    # "igzy": "igzy",
    # "glen": "glen",

}

TABLE_CONFIG = {

    "courses": {
        "columns": ["id","name","description","mediaId","startDate","endDate","isMandatory","status","createdAt","modifiedAt","languageMasterId","avgRating","authorId"],
        "primary_key": ["id"],
        "incremental_column": "modifiedAt",
        "casts": {},
    },

    "CourseModule": {
        "columns": ["id","title","status","createdAt","modifiedAt","courseId"],
        "primary_key": ["id"],
        "incremental_column": "modifiedAt",
        "casts": {},
    },

    "CourseLesson": {
        "columns": ["id","title","status","createdAt","modifiedAt","courseModuleId"],
        "primary_key": ["id"],
        "incremental_column": "modifiedAt",
        "casts": {},
    },

    "enrolledusers": {
        "columns": ["A","B"],
        "primary_key": None,
        "incremental_column": None,
        "casts": {},
    },

    "userMaster": {
        "columns": ["id","departmentId","designationId","emailId","fullName","isMasterEntry","createdAt","roleId","modifiedAt","status","username","locationId"],
        "primary_key": ["id"],
        "incremental_column": "modifiedAt",
        "casts": {"isMasterEntry": "toInt8"},
    },

    "CourseTodepartment": {
        "columns": ["A","B"],
        "primary_key": None,
        "incremental_column": None,
        "casts": {},
    },

    "departmentTorolePolicy": {
        "columns": ["A","B"],
        "primary_key": None,
        "incremental_column": None,
        "casts": {},
    },

    "department": {
        "columns": ["id","code","isMasterEntry","createdAt","modifiedAt","name","shortDesc","status","quizId"],
        "primary_key": ["id"],
        "incremental_column": "modifiedAt",
        "casts": {"isMasterEntry": "toInt8"},
    },

    "CourseTodesignation": {
        "columns": ["A","B"],
        "primary_key": None,
        "incremental_column": None,
        "casts": {},
    },

    "BatchToCourse": {
        "columns": ["A","B"],
        "primary_key": None,
        "incremental_column": None,
        "casts": {},
    },

    "Batch": {
        "columns": ["id","name","description","startDate","endDate","status","createdAt","modifiedAt"],
        "primary_key": ["id"],
        "incremental_column": "modifiedAt",
        "casts": {},
    },

    "BatchTouserMaster": {
        "columns": ["A","B"],
        "primary_key": None,
        "incremental_column": None,
        "casts": {},
    },

    "CourseTouserMaster": {
        "columns": ["A","B"],
        "primary_key": None,
        "incremental_column": None,
        "casts": {},
    },

    "CourseProgress": {
        "columns": ["id","userId","memberId","courseId","completionStatus","startedAt","lastAccessedAt","completedAt"],
        "primary_key": ["id"],
        "incremental_column": None,
        "casts": {},
    },

    "ModuleProgress": {
        "columns": ["id","courseProgressId","moduleId","courseModuleId","completionStatus","startedAt","lastAccessedAt","completedAt"],
        "primary_key": ["id"],
        "incremental_column": None,
        "casts": {},
    },

    "LessonProgress": {
        "columns": ["id","moduleProgressId","lessonId","completionStatus","startedAt","lastAccessedAt","completedAt"],
        "primary_key": ["id"],
        "incremental_column": None,
        "casts": {},
    },

    "Certificate": {
        "columns": ["id","name","description","pdfUrl","userId","status","createdAt","modifiedAt"],
        "primary_key": ["id"],
        "incremental_column": "modifiedAt",
        "casts": {},
    },

    "CertificateTolanguageMaster": {
        "columns": ["A","B"],
        "primary_key": None,
        "incremental_column": None,
        "casts": {},
    },

    "languageMaster": {
        "columns": ["id","IsLeftToRight","bcp47Code","code","isMasterEntry","name","status","createdAt","modifiedAt"],
        "primary_key": ["id"],
        "incremental_column": "modifiedAt",
        "casts": {},
    },

    "designation": {
        "columns": ["id","code","createdAt","departmentId","isMasterEntry","modifiedAt","name","shortDesc","status"],
        "primary_key": ["id"],
        "incremental_column": "modifiedAt",
        "casts": {"isMasterEntry": "toInt8"},
    },

    "QuizAssignment": {
        "columns": ["id","title","quizId","quizCompletionTimeInMinutes","passingPercentage","quizAttemptLimit","createdAt","modifiedAt","status","sendBroadcast","authorId","bindToDept","startDate","endDate"],
        "primary_key": ["id"],
        "incremental_column": "modifiedAt",
        "casts": {}
    },

    "QuizAssignmentTouserMaster": {
        "columns": ["A","B"],
        "primary_key": None,
        "incremental_column": None,
        "casts": {}
    },

    "quiz_departments": {
        "columns": ["A","B"],
        "primary_key": None,
        "incremental_column": None,
        "casts": {}
    },

    "Submission": {
        "columns": ["id","userId","quizId","title","createdAt","modifiedAt","isSubmitted","isActive","score","passingPercentage","submittedAt","attemptNumber","quizAssignmentId","courseId","courseLessonId","courseModuleId","isReviewed","timeSpentOnSubmission"],
        "primary_key": ["id"],
        "incremental_column": "modifiedAt",
        "casts": {"isSubmitted":"toInt8", "isActive":"toInt8","isReviewed":"toInt8"}
    },

    "QuizQuestion": {
        "columns": ["id","title","type","submissionId","isCorrect","finalScore","review","score"],
        "primary_key": ["id"],
        "incremental_column": None,
        "casts": {}
    },

    "CorrectAnswer": {
        "columns": ["id","title","quizQuestionId","createdAt"],
        "primary_key": ["id"],
        "incremental_column": "createdAt",
        "casts": {}
    },

    "SubmittedAnswers": {
        "columns": ["id","title","quizQuestionId","createdAt"],
        "primary_key": ["id"],
        "incremental_column": "createdAt",
        "casts": {}
    },

    "QuizQuestionAttempt": {
        "columns": ["id","startTime","endTime","submittedAnswers","quizQuestionId","createdAt","courseId","lessonId","moduleId","passingPercentage","quizCompletionTimeInMinutes","timeSpentOnQuestion"],
        "primary_key": ["id"],
        "incremental_column": "createdAt",
        "casts": {}
    },

    "Page": {
        "columns": ["id","title","sequence","type","courseLessonId","quizId","createdAt","modifiedAt"],
        "primary_key": ["id"],
        "incremental_column": "modifiedAt",
        "casts": {}
    },

    "events": {
        "columns": [],
        "primary_key": None,
        "incremental_column": None,
        "casts": {}
    }
}


