import pytest
import random

from faker import Faker
from flask import url_for

from .models import Course, CourseSchema, Course_Offering,\
        Course_OfferingSchema, Diploma, DiplomaSchema, Student, StudentSchema,\
        Class_Meeting, Class_MeetingSchema, Diploma_Awarded, Diploma_AwardedSchema
from ..people.models import Person
from ..places.models import Location


def flip():
    """Return true or false randomly."""
    return random.choice((True, False))


def course_object_factory():
    """Cook up a fake course."""
    fake = Faker()  # Use a generic one; others may not have all methods.
    course = {
        'name': fake.sentence(nb_words=3),
        'description': fake.paragraph(),
        'active': flip()
    }
    return course


def create_multiple_courses(sqla, n=10):
    """Commits the number of courses to the DB."""
    fake = Faker()  # Use a generic one; others may not have all methods.
    course_schema = CourseSchema()
    new_courses = []
    for i in range(n):
        valid_course = course_schema.load(course_object_factory())
        new_courses.append(Course(**valid_course))
    sqla.add_all(new_courses)
    sqla.commit()


def course_offerings_object_factory(course_id):
    """Cook up a fake course."""
    fake = Faker()  # Use a generic one; others may not have all methods.
    course_offerings = {
        'maxSize': random.randint(1, 100),
        'description': fake.paragraph(),
        'active': flip(),
        'courseId': course_id
    }
    return course_offerings


def create_multiple_course_offerings(sqla, n=3):
    """Commits the number of course offering to the DB."""
    courses = sqla.query(Course).all()
    course_offerings_schema = Course_OfferingSchema()
    new_course_offerings = []
    for i in range(n):
        valid_course_offering = course_offerings_schema.load(
            course_offerings_object_factory(courses[i].id))
        new_course_offerings.append(Course_Offering(**valid_course_offering))
    sqla.add_all(new_course_offerings)
    sqla.commit()


def create_multiple_prerequisites(sqla):
    """Commits the number of prerequisites to the DB."""
    courses = sqla.query(Course).all()
    new_prerequisites = []
    for i in range(len(courses)-1):
        courses[i].prerequisites = [courses[i+1]]
    sqla.add_all(new_prerequisites)
    sqla.commit()


def courses_diploma_object_factory():
    """Cook up a fake diploma."""
    fake = Faker()  # Use a generic one; others may not have all methods.
    course_diploma = {
    'name': fake.sentence(nb_words=4),
    'description': fake.paragraph(),
    'active': flip(),
    }
    return course_diploma


def create_multiple_diplomas(sqla, n=20):
    """Commits the number of diplomas to the DB."""
    courses = sqla.query(Course).all()
    course_diploma_schema = DiplomaSchema()
    new_courses = []
    for i in range(n):
        valid_course_diploma = course_diploma_schema.load(courses_diploma_object_factory())
        diploma = Diploma(**valid_course_diploma)
        courses[i%len(courses)].diplomas.append(diploma)
    sqla.add_all(new_courses)
    sqla.commit()


def student_object_factory(offering_id, student_id):
    """Cook up a fake student"""
    fake = Faker()
    course_student = {
    'studentId': student_id,
    'offeringId': offering_id,
    'confirmed': flip(),
    'active': flip()
    }
    return course_student

def create_multiple_students(sqla, n=6):
    """Commits the number of students to the DB."""
    students = sqla.query(Person).all()
    course_offering = sqla.query(Course_Offering).all()
    course_students_schema = StudentSchema()
    new_students = []
    for i in range(n):
        valid_student = course_students_schema.load(student_object_factory(course_offering[i%len(course_offering)].id, students[i%len(students)].id))
        student = Student(**valid_student)
        new_students.append(student)
    sqla.add_all(new_students)
    sqla.commit()


def class_meeting_object_factory(teacher, offering_id, location=1):
    """Cook up a fake class meeting"""
    fake = Faker()
    class_meeting = {
    'offeringId': offering_id,
    'teacher': teacher,
    'when': str(fake.future_datetime(end_date="+30d")),
    'location': location,
    }
    return class_meeting

def create_class_meetings(sqla, n=6):
    """Commits the number of class meetings to the DB."""
    people = sqla.query(Person).all()
    course_offerings = sqla.query(Course_Offering).all()
    locations = sqla.query(Location).all()
    class_meeting_schema = Class_MeetingSchema()
    new_class_meetings = []
    for i in range(n):
        teacher = people[random.randint(0,len(people)-1)].id
        offering = course_offerings[i%len(course_offerings)].id
        location = 1#locations[random.randint(0,len(locations)-1)].id

        valid_class_meeting = class_meeting_schema.load(class_meeting_object_factory(teacher, offering, location))
        class_meeting = Class_Meeting(**valid_class_meeting)
        new_class_meetings.append(class_meeting)
    sqla.add_all(new_class_meetings)
    sqla.commit()

def diploma_award_object_factory():
    """Cook up a fake diploma award"""
    fake = faker()
    print(fake.past_date(start_date="-30d"))
    diploma_award = {
        'when': str(fake.past_date(start_date="-30d"))
    }

def create_diploma_awards(sqla, n):
    """Commits the number of diploma awards to the DB."""
    students = sqla.query(Student).all()
    diplomas = sqla.query(Diploma).all()
    # diploma_award_schema = Diploma_AwardedSchema()
    new_diploma_awards = []
    for student in students:
        diploma = diplomas[random.randint(0, len(diplomas))]
        # print(student.diplomas.when)
        print(diploma)
        student.diplomas.append(diploma)
        new_diploma_awards.append(student)
    sqla.add_all(new_diploma_awards)
    sqla.commit()


# ---- Course

# Test course creation


@pytest.mark.xfail()
def test_create_course(client, db):
    # GIVEN course entry to put in database
    # WHEN database does not contain entry
    # THEN assert that entry is now in database
    assert True == False

# Test getting all courses from the database


@pytest.mark.xfail()
def test_read_all_courses(client, db):
    # GIVEN existing (active and inactive) courses in database
    # WHEN call to database
    # THEN assert all entries from database are called
    assert True == False


@pytest.mark.xfail()
def test_read_all_active_courses(client, db):
    # GIVEN existing and active courses
    # WHEN call to database
    # THEN assert all active courses are listed
    assert True == False


@pytest.mark.xfail()
def test_read_all_inactive_courses(client, db):
    # GIVEN existing and inactive courses
    # WHEN call to database
    # THEN assert all active courses are listed
    assert True == False

# Test reading a single course from the database


@pytest.mark.xfail()
def test_read_one_course(client, db):
    # GIVEN one course in the database
    # WHEN call to database
    # THEN assert entry called is only entry returned
    assert True == False


def create_course(sqla):
    """Create single course into DB"""
    course_schema = CourseSchema()
    new_courses = []
    valid_course = course_schema.load(course_object_factory(1))
    new_courses.append(Course(**valid_course))
    sqla.add_all(new_courses)  # should only add one course tho
    sqla.commit()


@pytest.mark.smoke
def test_deactivate_course(auth_client):
    """Test that an active course can be deactivated"""
    # GIVEN course to deactivate
    create_course(auth_client.sqla)
    course = auth_client.sqla.query(Course).first()
    # WHEN course is changed to inactive
    resp = auth_client.patch(url_for('courses.deactivate_course', course_id=course.id),
                             json={'active': False})
    # THEN assert course is inactive
    assert resp.status_code == 200
    assert resp.json['active'] == False


@pytest.mark.smoke
def test_reactivate_course(auth_client):
    """Test that an active course can be deactivated"""
    # GIVEN course to activate
    create_course(auth_client.sqla)
    course = auth_client.sqla.query(Course).first()
    # WHEN course is changed to active
    resp = auth_client.patch(url_for('courses.reactivate_course', course_id=course.id),
                             json={'active': True})
    # THEN assert course is active
    assert resp.status_code == 200
    assert resp.json['active'] == True


"""
# Test
@pytest.mark.xfail()
def test_replace_course(client, db):
    # GIVEN a deactivated course in database
    # WHEN
    # THEN assert
    assert True == False
"""


@pytest.mark.xfail()
def test_update_course(client, db):
    # GIVEN active or inactive course in database
    # WHEN course information updated
    # THEN assert course reflects new detail(s)
    assert True == False


"""
@pytest.mark.xfail()
def test_delete_course(client, db):
    # GIVEN undesirable course in database
    # WHEN course is removed
    # THEN assert course and all associated information deleted
    assert True == False
"""

# ---- Prerequisite


@pytest.mark.xfail()
def test_create_prerequisite(client, db):
    # GIVEN existing and available course in database
    # WHEN course requires previous attendance to another course
    # THEN add course as prerequisite
    assert True == False

# This will test getting all prerequisites for a single course


@pytest.mark.xfail()
def test_read_all_prerequisites(client, db):
    # GIVEN existing and available course in database
    # WHEN that course has prerequisites
    # THEN assert all prereq's are listed
    assert True == False

# FIX NAME (Will test to see all courses that have given course as a prerequisite)


@pytest.mark.xfail()
def test_read_all_courses_with_prerequisite(client, db):
    # GIVEN prerequisite course in database
    # WHEN other courses have that course as a prerequisite
    # THEN list all courses with given prerequisite
    assert True == False


@pytest.mark.xfail()
def test_update_prerequisite(client, db):
    # GIVEN an existing and available course with an existing prereq
    # WHEN new prereq for existing course is required
    # THEN existing course has new prereq in place of existing prereq
    assert True == False


"""
@pytest.mark.xfail()
def test_delete_prerequisite(client, db):
    # GIVEN an existing prereq and related course
    # WHEN prereq no longer needed from associated course
    # THEN prereq row entry removed (along with associated course)
    assert True == False
"""


# ---- Course_Offering


@pytest.mark.xfail()
def test_create_course_offering(client, db):
    # GIVEN an existing course
    # WHEN one or more courses need a section to offer
    # THEN create new course section
    assert True == False


@pytest.mark.xfail()
def test_read_all_course_offerings(client, db):
    # GIVEN existing (active and inactive) course offerings
    # WHEN all sections needed
    # THEN list all course sections
    assert True == False


@pytest.mark.xfail()
def test_read_all_active_course_offerings(client, db):
    # GIVEN existing active course offerings
    # WHEN all active course sections needed
    # THEN list all sections of active courses
    assert True == False


@pytest.mark.xfail()
def test_read_all_inactive_course_offerings(client, db):
    # GIVEN existing inactive course offerings
    # WHEN all inactive course sections needed
    # THEN list all sections of inactive courses
    assert True == False


@pytest.mark.xfail()
def test_read_one_course_offering(client, db):
    # GIVEN an existing course
    # WHEN one course section needed
    # THEN list one course section of course
    assert True == False


"""
@pytest.mark.xfail()
def test_replace_course_offering(client, db):
    # GIVEN
    # WHEN
    # THEN
    assert True == False
"""


@pytest.mark.xfail()
def test_update_course_offering(client, db):
    # GIVEN an existing (active or inactive) course offering
    # WHEN course offering needs to update existing information
    # THEN assert changes to course offering reflect update
    assert True == False


"""
@pytest.mark.xfail()
def test_delete_course_offering(client, db):
    # GIVEN an existing (active or inactive) course and at least one section
    # WHEN user desires to remove course offering
    # THEN
    assert True == False
"""
