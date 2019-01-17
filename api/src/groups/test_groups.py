import pytest
import random
import datetime
import random
from faker import Faker
from flask import url_for
from flask_jwt_extended import create_access_token
from werkzeug.datastructures import Headers
from werkzeug.security import check_password_hash

from .models import Group, GroupSchema, Member, MemberSchema, Meeting, MeetingSchema, Attendance, AttendanceSchema
from .create_group_data import flip, fake, group_object_factory, create_multiple_groups, member_object_factory, create_multiple_members, meeting_object_factory, create_multiple_meetings, attendance_object_factory, create_attendance
from ..people.models import Person, Manager
from ..places.models import Address
from ..people.test_people import create_multiple_managers, create_multiple_people

fake = Faker()


# ---- Group

@pytest.mark.smoke
def test_create_group(auth_client):
    # GIVEN an empty database
    create_multiple_people(auth_client.sqla, 3)
    create_multiple_managers(auth_client.sqla, 2, "Manager")
    # WHEN we add in some events

    count = random.randint(5, 15)

    # WHEN
    for i in range(count):
        resp = auth_client.post(url_for('groups.create_group'), json=group_object_factory(auth_client.sqla))
        assert resp.status_code == 201

    # THEN
    assert auth_client.sqla.query(Group).count() == count


@pytest.mark.smoke
def test_create_invalid_group(auth_client):
    # GIVEN an empty database
    create_multiple_people(auth_client.sqla, 3)
    create_multiple_managers(auth_client.sqla, 2, "Manager")
    # WHEN we attempt to add invalid events
    count = random.randint(5, 15)

    for i in range(count):
        group = group_object_factory(auth_client.sqla)

        if flip():
            group['name'] = None
        elif flip():
            group['description'] = None
        else:
            group['active'] = None

        resp = auth_client.post(url_for('groups.create_group'), json=group)

        # THEN the response should have the correct code
        assert resp.status_code == 422

    # AND the database should still be empty
    assert auth_client.sqla.query(Group).count() == 0


@pytest.mark.smoke
def test_read_all_groups(auth_client):
    # GIVEN
    count = random.randint(3, 11)
    create_multiple_people(auth_client.sqla, 3)
    create_multiple_managers(auth_client.sqla, 2, "Manager")
    create_multiple_groups(auth_client.sqla, count)

    # WHEN
    resp = auth_client.get(url_for('groups.read_all_groups'))
    assert resp.status_code == 200
    groups = auth_client.sqla.query(Group).all()

    # THEN
    assert len(groups) == count
    assert len(resp.json) == count

    for i in range(count):
        assert resp.json[i]['name'] == groups[i].name


# @pytest.mark.smoke
# def test_read_all_events_with_query(auth_client):
#     # GIVEN some existing events
#     count = random.randint(3, 11)
#     create_multiple_people(auth_client.sqla, 3)
#     create_multiple_managers(auth_client.sqla, 2, "Manager")
#     create_multiple_groups(auth_client.sqla, count)
#     all_groups = auth_client.sqla.query(Group).all()
#
#     for _ in range(15):
#         # WHEN queried for all events matching a flag
#         query_string = dict()
#         if flip():
#             query_string['return_group'] = 'inactive'
#         else:
#             query_string['return_group'] = 'both'
#
#         if flip():
#             query_string['start'] = datetime.datetime.now().strftime('%Y-%m-%d')
#         if flip():
#             query_string['end'] = datetime.datetime.now().strftime('%Y-%m-%d')
#
#         if flip():
#             query_string['title'] = 'c'
#
#         if flip():
#             query_string['location_id'] = 1
#
#         if flip():
#             query_string['include_assets'] = 1
#
#         # THEN the response should match those flags
#         resp = auth_client.get(url_for('events.read_all_events'), query_string=query_string)
#         assert resp.status_code == 200
#         events = auth_client.sqla.query(Event).all()
#
#         for event in resp.json:
#             if 'return_group' in query_string:
#                 if query_string['return_group'] == 'inactive':
#                     assert event['active'] == False
#             else:
#                 assert event['active'] == True
#
#             if 'start' in query_string:
#                 assert datetime.datetime.strptime(event['start'][:event['start'].index('T')],
#                                                   '%Y-%m-%d') >= datetime.datetime.strptime(query_string['start'],
#                                                                                             '%Y-%m-%d')
#             if 'end' in query_string:
#                 assert datetime.datetime.strptime(event['end'][:event['end'].index('T')],
#                                                   '%Y-%m-%d') <= datetime.datetime.strptime(query_string['end'],
#                                                                                             '%Y-%m-%d')
#
#             if 'title' in query_string:
#                 assert query_string['title'].lower() in event['title'].lower()
#
#             if 'location_id' in query_string:
#                 assert event['location_id'] == query_string['location_id']



@pytest.mark.smoke
def test_read_one_group(auth_client):
    # GIVEN
    count = random.randint(3, 11)
    create_multiple_people(auth_client.sqla, 3)
    create_multiple_managers(auth_client.sqla, 2, "Manager")
    create_multiple_groups(auth_client.sqla, count)

    # WHEN
    groups = auth_client.sqla.query(Group).all()

    for group in groups:
        resp = auth_client.get(url_for('groups.read_one_group', group_id=group.id))
    #THEN expect groups to match
        assert resp.status_code == 200
        assert resp.json['name'] == group.name


# Not in API yet
# @pytest.mark.smoke
# def test_replace_group(auth_client):
#     # GIVEN a database with a number of groups
#     count = random.randint(3, 11)
#     create_multiple_people(auth_client.sqla, 3)
#     create_multiple_managers(auth_client.sqla, 2, "Manager")
#     create_multiple_groups(auth_client.sqla, count)
#     # WHEN we replace one event with a predefined content
#     group = auth_client.sqla.query(Group).first()
#     new_group = {
#         'name': fake.word(),
#         'start': str(fake.future_datetime(end_date="+6h")),
#         'end': str(fake.date_time_between(start_date="+6h", end_date="+1d", tzinfo=None)),
#         'active': flip()
#     }
#     resp = auth_client.put(url_for('events.replace_event', event_id=event.id), json=new_event)
#     # THEN we expect the right status code
#     assert resp.status_code == 200
#     # THEN we expect the event in the database to have the same content of the predefined content
#     assert resp.json['id'] == event.id
#     assert resp.json['title'] == new_event['title']
#     assert resp.json['active'] == new_event['active']


@pytest.mark.smoke
def test_update_group(auth_client):
    # GIVEN a database with a number of groups
    count = random.randint(3, 11)
    create_multiple_people(auth_client.sqla, 3)
    create_multiple_managers(auth_client.sqla, 2, "Manager")
    create_multiple_groups(auth_client.sqla, count)

    # WHEN we update one group
    group = auth_client.sqla.query(Group).first()
    manager_id = auth_client.sqla.query(Manager.id).first()[0]

    payload = group_object_factory(auth_client.sqla)

    # payload['name'] = new_group['name']
    # payload['description'] = new_group['description']
    payload['manager_id'] = manager_id
    flips = flip()
    if flips:
        payload['active'] = flip()

    resp = auth_client.patch(url_for('groups.update_group', group_id=group.id), json=payload)

    # THEN we assume the correct status code
    assert resp.status_code == 200

    # THEN we assume the correct content in the returned object
    assert resp.json['name'] == payload['name']
    assert resp.json['description'] == payload['description']
    if flips:
        assert resp.json['active'] == payload['active']

# Waiting on API
# @pytest.mark.xfail()
# def test_delete_group(auth_client):
#     # GIVEN
#     # WHEN
#     # THEN
#     assert True == False


# ---- Meeting


@pytest.mark.smoke
def test_create_meeting(auth_client):
    # GIVEN an empty database
    create_multiple_people(auth_client.sqla, 3)
    create_multiple_managers(auth_client.sqla, 2, "Manager")
    create_multiple_groups(auth_client.sqla, 1)
    # WHEN we add in some events

    count = random.randint(5, 15)

    # WHEN
    for i in range(count):
        resp = auth_client.post(url_for('groups.create_meeting'), json=meeting_object_factory(auth_client.sqla))
        assert resp.status_code == 201

    # THEN
    assert auth_client.sqla.query(Meeting).count() == count


@pytest.mark.xfail()
def test_read_all_meetings(auth_client, db):
    # GIVEN
    # WHEN
    # THEN
    assert True == False


@pytest.mark.xfail()
def test_read_one_meeting(auth_client, db):
    # GIVEN
    # WHEN
    # THEN
    assert True == False


@pytest.mark.xfail()
def test_replace_meeting(auth_client, db):
    # GIVEN
    # WHEN
    # THEN
    assert True == False


@pytest.mark.xfail()
def test_update_meeting(auth_client, db):
    # GIVEN
    # WHEN
    # THEN
    assert True == False


@pytest.mark.xfail()
def test_delete_meeting(auth_client, db):
    # GIVEN
    # WHEN
    # THEN
    assert True == False


# ---- Member


@pytest.mark.xfail()
def test_create_member(auth_client, db):
    # GIVEN
    # WHEN
    # THEN
    assert True == False


@pytest.mark.xfail()
def test_read_all_members(auth_client, db):
    # GIVEN
    # WHEN
    # THEN
    assert True == False


@pytest.mark.xfail()
def test_read_one_member(auth_client, db):
    # GIVEN
    # WHEN
    # THEN
    assert True == False


@pytest.mark.xfail()
def test_replace_member(auth_client, db):
    # GIVEN
    # WHEN
    # THEN
    assert True == False


@pytest.mark.xfail()
def test_update_member(auth_client, db):
    # GIVEN
    # WHEN
    # THEN
    assert True == False


@pytest.mark.xfail()
def test_delete_member(auth_client, db):
    # GIVEN
    # WHEN
    # THEN
    assert True == False


# ---- Attendance


@pytest.mark.xfail()
def test_create_attendance(auth_client, db):
    # GIVEN
    # WHEN
    # THEN
    assert True == False


@pytest.mark.xfail()
def test_read_all_attendance(auth_client, db):
    # GIVEN
    # WHEN
    # THEN
    assert True == False


@pytest.mark.xfail()
def test_read_one_attendance(auth_client, db):
    # GIVEN
    # WHEN
    # THEN
    assert True == False


@pytest.mark.xfail()
def test_replace_attendance(auth_client, db):
    # GIVEN
    # WHEN
    # THEN
    assert True == False


@pytest.mark.xfail()
def test_update_attendance(auth_client, db):
    # GIVEN
    # WHEN
    # THEN
    assert True == False


@pytest.mark.xfail()
def test_delete_attendance(auth_client, db):
    # GIVEN
    # WHEN
    # THEN
    assert True == False
