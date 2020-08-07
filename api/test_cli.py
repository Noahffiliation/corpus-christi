import os

import pytest
import json
import yaml
from src import db, create_app
from src.courses.models import Course, Diploma
from src.i18n.models import Language, I18NValue, I18NLocale, I18NKey
from src.people.models import Role
from src.places.models import Country

from commands.people import create_account_cli
from commands.app import create_app_cli
from commands.courses import create_course_cli
from commands.events import create_event_cli
from commands.faker import create_faker_cli
from commands.i18n import create_i18n_cli


@pytest.fixture
def runner():
    app = create_app(os.getenv('CC_CONFIG') or 'test')
    app.testing = True  # Make sure exceptions percolate out

    db.drop_all()
    db.create_all()

    create_account_cli(app)
    create_app_cli(app)
    create_course_cli(app)
    create_event_cli(app)
    create_faker_cli(app)
    create_i18n_cli(app)

    yield app.test_cli_runner()


def test_load_counties(runner):
    runner.invoke(args=['app', 'load-countries'])
    assert db.session.query(Country).count() > 0


def test_load_languages(runner):
    runner.invoke(args=['app', 'load-languages'])
    assert db.session.query(Language).count() > 0


def test_load_roles(runner):
    assert db.session.query(Role).count() == 0
    runner.invoke(args=['app', 'load-roles'])
    assert db.session.query(Role).count() > 0


# ---- Course CLI


def test_course_cli(runner):
    """Tests the cli command for creating a course"""
    # GIVEN all the valid required arguments for course
    name = 'course1'
    desc = 'description'
    # WHEN call is invoked
    runner.invoke(args=['courses', 'create-course', name, desc])
    # THEN a course with zero prereqs is created
    course = db.session.query(Course).filter_by(name=name).first()
    assert course.name == name
    assert course.prerequisites == []
    # GIVEN all the valid arguments for course and a prereqs
    name = 'course2'
    prereq = 'course1'
    # WHEN call is invoked
    runner.invoke(
        args=[
            'courses',
            'create-course',
            name,
            desc,
            '--prereq',
            prereq])
    # THEN a course with two prereqs is created
    course = db.session.query(Course).filter_by(name=name).first()
    assert course.name == name
    assert len(course.prerequisites) == 1
    assert course.prerequisites[0].name == prereq
    # GIVEN offering flag for a course
    name = 'course4'
    offering_name = 'course1'
    # WHEN call is invoked
    runner.invoke(
        args=[
            'courses',
            'create-course',
            name,
            desc,
            '--offering',
            offering_name])
    # THEN help message is printed
    course = db.session.query(Course).filter_by(name=name).first()
    assert course.name == name
    assert course.courses_offered[0].description == offering_name


def test_diploma_cli(runner):
    """Tests the cli command for creating a diploma"""
    # GIVEN all the valid arguments for a diploma
    name = 'diploma1'
    desc = 'description'
    # WHEN call is invoked
    runner.invoke(args=['courses', 'create-diploma', name, desc])
    # THEN
    diploma = db.session.query(Diploma).filter_by(name=name).first()
    assert diploma.name == name
    assert diploma.description == desc
    # GIVEN missing arguments for diploma
    name = 'diploma2'
    # WHEN call is invoked
    result = runner.invoke(args=['courses', 'create-diploma'])
    # THEN help message is printed
    assert 'Usage' in result.output


def test_load_attribute_types(runner):
    runner.invoke(args=['app', 'load-attribute-types'])
    assert db.session.query(I18NValue).filter(
        I18NValue.key_id == 'attribute.date').count() > 0

# ---- i18n CLI


def populate_database_i18n(locale_data, key_data):
    db.session.add_all([I18NLocale(**d) for d in locale_data])
    db.session.add_all([I18NKey(**k) for k in key_data])
    db.session.add_all([
        I18NValue(
            locale_code=locale['code'],
            key_id=key['id'],
            gloss=f"{key['desc']} in {locale['desc']}")
        for locale in locale_data for key in key_data
    ])
    db.session.commit()
    assert db.session.query(I18NValue).count() == len(
        locale_data) * len(key_data)


def test_i18n_load(runner):
    with runner.isolated_filesystem():
        filename = 'en-US.json'
        # GIVEN a file with some translation entries
        with open(filename, "w") as f:
            json.dump({
                "account": {
                    "messages": {
                        "added-ok": {
                            "gloss": "Account added successfully",
                            "verified": False
                        },
                        "updated-ok": {
                            "gloss": "Account updated successfully",
                            "verified": False
                        }
                    }
                }
            }, f)
            # WHEN we load the entries into the database
        result = runner.invoke(
            args=[
                'i18n',
                'load',
                'en-US',
                '--target',
                filename])
        # THEN we expect the correct number of entries to be loaded
        assert db.session.query(I18NValue).count() == 2


def test_i18n_dump(runner):
    # GIVEN a database with some entries
    locale_data = [{'code': 'en-US', 'desc': 'English US'}]
    key_data = [
        {'id': 'alt.logo', 'desc': 'Alt text for logo'},
        {'id': 'app.name', 'desc': 'Application name'},
        {'id': 'app.desc', 'desc': 'This is a test application'}
    ]
    populate_database_i18n(locale_data, key_data)
    with runner.isolated_filesystem():
        # WHEN we dump the entries into a file
        filename = 'en-US.json'
        result = runner.invoke(
            args=[
                'i18n',
                'dump',
                'en-US',
                '--target',
                filename])
        # THEN we expect the file to be created
        assert os.path.exists(filename)
        # THEN we expect the json structure to match what we created
        with open(filename, "r") as f:
            tree = json.load(f)
            assert 'alt' in tree
            assert 'app' in tree
            assert tree['app']['desc']['gloss'] == "This is a test application in English US"


def test_i18n_import(runner):
    with runner.isolated_filesystem():
        filename = 'entries.yaml'
        # GIVEN a file with "locale-tail" structured tree
        with open(filename, "w") as f:
            f.write("""added-ok:
  _desc: messages for successful adding account
  en-US: Account added successfully
  es-EC: Cuenta agregada exitosamente
updated-ok:
  _desc: messages for successful updating account
  en-US: Account updated successfully
  es-EC: "Cuenta actualizada con \xE9xito" """)
        # WHEN we load the entries into the database
        result = runner.invoke(
            args=['i18n',
                  'import',
                  '--target',
                  filename,
                  'account.messages'])
        # THEN we expect the correct number of entries to be loaded
        assert db.session.query(I18NValue).count() == 4
        # THEN we expect the value to be correct
        assert db.session.query(I18NValue).filter_by(
            key_id="account.messages.added-ok",
            locale_code='en-US').first().gloss == "Account added successfully"
        # THEN we expect the descriptions to be loaded correctly
        assert db.session.query(I18NKey).filter_by(
            id="account.messages.added-ok").first().desc == "messages for successful adding account"

        # WHEN we update a single leaf record with standard input
        result = runner.invoke(
            args=[
                'i18n',
                'import',
                '--target',
                '-',
                'account.messages.added-ok'],
            input="_desc: Messages for successful adding account\nen-US: Success!")
        # THEN we expect the record to be updated
        assert db.session.query(I18NValue).filter_by(
            key_id="account.messages.added-ok",
            locale_code='en-US').first().gloss == "Success!"
        # THEN we expect the descriptions to be loaded correctly
        assert db.session.query(I18NKey).filter_by(
            id="account.messages.added-ok").first().desc == "Messages for successful adding account"
        # WHEN we try to write a leaf record onto an intermediate path
        result = runner.invoke(
            args=[
                'i18n',
                'import',
                '--target',
                '-',
                'account.messages'],
            input="_desc: Messages for successful adding account\nen-US: Success!")

        # THEN we expect the program to be aborted
        assert result.exit_code == 1 
        # THEN we expect the correct output is printed
        assert b'invalid locale-tail structured tree' in result.stdout_bytes

        # WHEN we try to write a leaf node without a path
        result = runner.invoke(
            args=[
                'i18n',
                'import',
                '--target',
                '-'],
            input="_desc: Messages for successful adding account\nen-US: Success!")

        # THEN we expect the program to be aborted 
        assert result.exit_code == 1
        # THEN we expect the correct output is printed
        assert b'invalid locale-tail structured tree' in result.stdout_bytes


def test_i18n_export(runner):
    # GIVEN a database with some entries
    locale_data = [{'code': 'en-US', 'desc': 'English US'},
                   {'code': 'es-EC', 'desc': 'Spanish Ecuador'}]
    key_data = [
        {'id': 'alt.logo', 'desc': 'Alt text for logo'},
        {'id': 'app.name', 'desc': 'Application name'},
        {'id': 'app.desc', 'desc': 'This is a test application'}
    ]
    populate_database_i18n(locale_data, key_data)
    with runner.isolated_filesystem():
        # WHEN we export all the entries into a file
        filename = 'entries.yaml'
        result = runner.invoke(
            args=[
                'i18n',
                'export',
                '--target',
                filename])
        # THEN we expect the file to be created
        assert os.path.exists(filename)
        # THEN we expect the json structure to match what we created
        with open(filename, "r") as f:
            tree = yaml.safe_load(f)
            assert 'alt' in tree
            assert 'app' in tree
            assert tree['app']['desc']['en-US'] == "This is a test application in English US"

        # WHEN we export part of the entries into a file
        filename = 'entries.yaml'
        result = runner.invoke(
            args=[
                'i18n',
                'export',
                '--target',
                filename,
                'app'])
        # THEN we expect the json structure to match what we created
        with open(filename, "r") as f:
            tree = yaml.safe_load(f)
            assert 'name' in tree
            assert 'desc' in tree
            assert tree['desc']['en-US'] == "This is a test application in English US"


def test_i18n_list(runner):
    # GIVEN a database with some entries
    locale_data = [{'code': 'en-US', 'desc': 'English US'},
                   {'code': 'es-EC', 'desc': 'Spanish Ecuador'}]
    key_data = [
        {'id': 'alt.logo', 'desc': 'Alt text for logo'},
        {'id': 'app.name', 'desc': 'Application name'},
        {'id': 'app.desc', 'desc': 'This is a test application'}
    ]
    populate_database_i18n(locale_data, key_data)
    # WHEN we list some entries
    result = runner.invoke(
        args=[
            'i18n',
            'list',
            'app'])
    list_result = result
    # THEN we expect the same output as export
    result = runner.invoke(
        args=[
            'i18n',
            'export',
            '--target',
            '-',
            'app'])
    assert result.stdout_bytes == list_result.stdout_bytes


def test_i18n_delete(runner):
    # GIVEN a database with some entries
    locale_data = [{'code': 'en-US', 'desc': 'English US'},
                   {'code': 'es-EC', 'desc': 'Spanish Ecuador'}]
    key_data = [
        {'id': 'alt.logo', 'desc': 'Alt text for logo'},
        {'id': 'app.name', 'desc': 'Application name'},
        {'id': 'app.desc', 'desc': 'This is a test application'}
    ]
    populate_database_i18n(locale_data, key_data)
    assert db.session.query(I18NValue).count() == 6
    # WHEN we delete some entries with a certain locale
    result = runner.invoke(
        args=[
            'i18n',
            'delete',
            '--locale',
            'en-US',
            'alt.logo'])
    # THEN we expect the correct entry count in database
    assert db.session.query(I18NValue).count() == 5
    # THEN we expect the deleted entry not to be in database
    assert not db.session.query(I18NValue).filter_by(
        key_id='alt.logo', locale_code='en-US').first()
    # WHEN we delete entries recursively with all locales
    result = runner.invoke(
        args=[
            'i18n',
            'delete',
            '-r',
            'app'])
    # THEN we expect the correct entry count in database
    assert db.session.query(I18NValue).count() == 1
    # THEN we expect the corresponding key to be deleted
    keys = db.session.query(I18NKey).all()
    assert len(keys) == 1
    assert keys[0].id == 'alt.logo'
