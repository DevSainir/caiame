"""
Every table, in one import.

SQLAlchemy only knows about a table if the module defining it has been imported. A foreign
key to a table nobody imported fails at mapper configuration — and it fails far from the
cause, in whatever code first touched an unrelated model.

Two places need the whole set: Alembic, to see what to generate a migration from, and the
seeding scripts, which talk to models directly. Both import this module instead of keeping
their own list, because a list kept in two places is a list that is wrong in one of them.
"""

from models.accreditation import Accreditation
from models.assignment import Assignment
from models.base import Base
from models.course import Course
from models.course_benefit import CourseBenefit
from models.course_question import CourseQuestion
from models.course_reviewer import CourseReviewer
from models.course_unit import CourseUnit
from models.enrollment import Enrollment
from models.entitlement import Entitlement
from models.lesson import Lesson
from models.lesson_progress import LessonProgress
from models.media_file import MediaFile
from models.quiz import Quiz
from models.quiz_attempt import QuizAttempt, QuizAttemptAnswer
from models.quiz_question import QuizOption, QuizQuestion
from models.refresh_token import RefreshToken
from models.review import Review
from models.specialization import Specialization
from models.submission import Submission, SubmissionFile
from models.submission_review import SubmissionReview
from models.unit_progress import UnitProgress
from models.user import User

__all__ = [
    "Accreditation",
    "Assignment",
    "Base",
    "Course",
    "CourseBenefit",
    "CourseQuestion",
    "CourseReviewer",
    "CourseUnit",
    "Enrollment",
    "Entitlement",
    "Lesson",
    "LessonProgress",
    "MediaFile",
    "Quiz",
    "QuizAttempt",
    "QuizAttemptAnswer",
    "QuizOption",
    "QuizQuestion",
    "RefreshToken",
    "Review",
    "Specialization",
    "Submission",
    "SubmissionFile",
    "SubmissionReview",
    "UnitProgress",
    "User",
]
