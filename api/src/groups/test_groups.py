import random

import pytest
from dateutil import parser
from faker import Faker
from flask import url_for

from .create_group_data import flip, create_role, group_object_factory, group_object_factory_with_members, \
    create_multiple_groups, member_object_factory, create_multiple_members, meeting_object_factory, \
    create_multiple_meetings, create_attendance, create_multiple_group_types, create_multiple_manager_types, \
    group_type_object_factory
from .models import Group, GroupType, Member, Meeting, MeetingSchema, Attendance, Manager, ManagerType, ManagerSchema
from ..images.create_image_data import create_images_groups
from ..images.create_image_data import create_test_images
from ..images.models import Image, ImageGroup
from ..people.test_people import create_multiple_people
from ..places.models import Address, Country
from ..places.test_places import create_multiple_addresses, create_multiple_areas

fake = Faker()


def generate_managers(auth_client):
    create_multiple_people(auth_client.sqla, 4)
    create_multiple_accounts(auth_client.sqla)
    # create_multiple_managers(auth_client.sqla, 4, "Manager")


# ---- Group Type

def test_create_group_type(auth_client):
    # GIVEN an empty database
    # WHEN we add in a group type
    resp = auth_client.post(url_for('groups.create_group_type'), json = {'name':'group_type_1'})
    # THEN expect the create to run OK
    assert resp.status_code == 201

    # WHEN we create an invalid group type
    resp = auth_client.post(url_for('groups.create_group_type'), json = {'name':''})
    # THEN we expect the request to be unprocessable
    assert resp.status_code == 422

    # THEN we expect the correct number of items in the database
    assert auth_client.sqla.query(GroupType).count() == 1

def test_read_one_group_type(auth_client):
    # GIVEN a database with a number of group types
    count = random.randint(3, 11)
    create_multiple_group_types(auth_client.sqla, count)

    group_types = auth_client.sqla.query(GroupType).all()

    # WHEN we ask for the group_types one by one
    for group_type in group_types:
        # THEN we expect each of them to correspond to the group_type in the database
        resp = auth_client.get(
            url_for('groups.read_one_group_type', group_type_id=group_type.id))
        assert resp.status_code == 200
        assert resp.json['name'] == group_type.name
    
def test_read_all_group_types(auth_client):
    # GIVEN a database with some group_types
    count = random.randint(3, 11)
    create_multiple_group_types(auth_client.sqla, count)

    # WHEN we read all active group_types
    resp = auth_client.get(url_for('groups.read_all_group_types'))
    # THEN we expect the right status code
    assert resp.status_code == 200
    # THEN we expect the database has the same number of group_types as we created
    group_types = auth_client.sqla.query(GroupType).all()
    assert len(group_types) == count

def test_update_group_type(auth_client):
    # GIVEN a database with a number of group_types
    count = random.randint(3, 11)
    create_multiple_group_types(auth_client.sqla, count)

    # WHEN we update one group_type
    group_type = auth_client.sqla.query(GroupType).first()

    payload = group_type_object_factory("new_name")

    resp = auth_client.patch(
        url_for('groups.update_group_type', group_type_id=group_type.id), json=payload)

    # THEN we assume the correct status code
    assert resp.status_code == 200
    # THEN we assume the correct content in the returned object
    assert resp.json['name'] == 'new_name'
    # THEN we assume the correct content in the database
    assert auth_client.sqla.query(GroupType).filter_by(id=group_type.id).first().name == 'new_name'


def test_delete_group_type(auth_client):
    # GIVEN a database with a number of group_types
    count = random.randint(3, 11)
    create_multiple_group_types(auth_client.sqla, count)

    # WHEN we delete one of them
    group_type = auth_client.sqla.query(GroupType).first()
    resp = auth_client.delete(url_for('groups.delete_group_type', group_type_id = group_type.id))
    # THEN we assume the correct status code
    assert resp.status_code == 204

    # WHEN we delete a non-existent item
    resp = auth_client.delete(url_for('groups.delete_group_type', group_type_id = -1))
    # THEN we expect an error
    assert resp.status_code == 404

    # THEN we assume the number of group_types in the database to be the correct number
    group_types = auth_client.sqla.query(GroupType).all()
    assert len(group_types) == count - 1


# ---- Group

@pytest.mark.smoke
def test_create_group(auth_client):
    # GIVEN an empty database
    generate_managers(auth_client)
    create_role(auth_client.sqla)
    # print(auth_client.sqla.query(Role).first().name_i18n)
    # WHEN we add in some events
    count = random.randint(5, 15)
    # WHEN
    for i in range(count):
        resp = auth_client.post(url_for('groups.create_group'),
                                json=group_object_factory_with_members(auth_client.sqla))
        assert resp.status_code == 201

    # THEN
    assert auth_client.sqla.query(Group).count() == count

    group = group_object_factory_with_members(auth_client.sqla)
    group['manager_id'] = -1
    resp = auth_client.post(url_for('groups.create_group'), json=group)
    # THEN assert group is not found
    assert resp.status_code == 404


@pytest.mark.smoke
def test_create_invalid_group(auth_client):
    # GIVEN an empty database
    generate_managers(auth_client)
    # WHEN we attempt to add invalid events
    count = random.randint(5, 15)

    for i in range(count):
        group = group_object_factory(auth_client.sqla)

        if flip():
            group['name'] = None
        group['invalid_field'] = 4

        resp = auth_client.post(url_for('groups.create_group'), json=group)

        # THEN the response should have the correct code
        assert resp.status_code == 422

    # AND the database should still be empty
    assert auth_client.sqla.query(Group).count() == 0


@pytest.mark.smoke
def test_read_all_groups(auth_client):
    # GIVEN
    count = random.randint(3, 11)
    generate_managers(auth_client)
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


@pytest.mark.smoke
def test_read_one_group(auth_client):
    # GIVEN
    count = random.randint(3, 11)
    generate_managers(auth_client)
    create_multiple_groups(auth_client.sqla, count)

    # WHEN
    groups = auth_client.sqla.query(Group).all()

    for group in groups:
        resp = auth_client.get(url_for('groups.read_one_group', group_id=group.id))
        # THEN expect groups to match
        assert resp.status_code == 200
        assert resp.json['name'] == group.name

    resp = auth_client.get(url_for('groups.read_one_group', group_id=500))
    assert resp.status_code == 404


@pytest.mark.smoke
def test_update_group(auth_client):
    # GIVEN a database with a number of groups
    count = random.randint(3, 11)
    generate_managers(auth_client)
    create_role(auth_client.sqla)
    create_multiple_groups(auth_client.sqla, count)
    create_multiple_members(auth_client.sqla, count * 3)

    # WHEN we update one group
    group = auth_client.sqla.query(Group).first()
    manager_id = auth_client.sqla.query(Manager.id).first()[0]

    payload = group_object_factory_with_members(auth_client.sqla, 0.5)
    payload['manager_id'] = manager_id

    resp = auth_client.patch(url_for('groups.update_group', group_id=group.id), json=payload)

    # THEN we assume the correct status code
    assert resp.status_code == 201
    # THEN we assume the correct content of the group in the database
    updated_group = auth_client.sqla.query(Group).filter_by(id=group.id).first()
    for attr in ['name', 'description', 'manager_id', 'active']:
        assert vars(updated_group)[attr] == payload[attr]

    # THEN we assume the correct amount of members with the group in the database
    queried_members = auth_client.sqla.query(Group).filter_by(id=group.id).first().members
    queried_members = auth_client.sqla.query(Member).filter_by(group_id=group.id).filter_by(active=True).all()

    print(f"members in database {queried_members}, members in the payload {payload['person_ids']}")

    for queried_member in queried_members:
        print(f"person id in database: {queried_member.person_id}")
    assert len(queried_members) == len(payload['person_ids'])
    # THEN we assume each member in the database match up with a member in the payload
    for queried_member in queried_members:
        assert queried_member.person_id in payload['person_ids']

    # WHEN we update a non-existant group
    resp = auth_client.patch(url_for('groups.update_group', group_id=-1), json=payload)
    # THEN we expect an error code
    assert resp.status_code == 404

    # WHEN we update with an invalid manager
    payload['manager_id'] = -1
    resp = auth_client.patch(url_for('groups.update_group', group_id=group.id), json=payload)
    # THEN we expect an error
    assert resp.status_code == 404


@pytest.mark.smoke
def test_invalid_update_group(auth_client):
    # GIVEN a database with a number of groups
    count = random.randint(3, 11)
    generate_managers(auth_client)
    create_multiple_groups(auth_client.sqla, count)

    original_group = auth_client.sqla.query(Group).first()
    modified_group = group_object_factory(auth_client.sqla)

    modified_group['invalid_field'] = 4

    resp = auth_client.patch(url_for('groups.update_group', group_id=original_group.id), json=modified_group)

    # THEN we assume the incorrect status code
    assert resp.status_code == 422


@pytest.mark.smoke
def test_activate_group(auth_client):
    # GIVEN group to deactivate
    count = random.randint(3, 11)
    generate_managers(auth_client)
    create_multiple_groups(auth_client.sqla, count)

    groups = auth_client.sqla.query(Group).all()

    # WHEN group is changed to active
    for group in groups:
        resp = auth_client.put(url_for('groups.activate_group', group_id=group.id),
                               json={'active': True})
        # THEN assert group is active
        assert resp.status_code == 200
        assert resp.json['active'] == True

    resp = auth_client.put(url_for('groups.activate_group', group_id=500), json={'active': True})
    # THEN assert group is not found
    assert resp.status_code == 404


@pytest.mark.smoke
def test_deactivate_group(auth_client):
    # GIVEN group to deactivate
    count = random.randint(3, 11)
    generate_managers(auth_client)
    create_multiple_groups(auth_client.sqla, count)

    groups = auth_client.sqla.query(Group).all()

    # WHEN group is changed to inactive
    for group in groups:
        resp = auth_client.put(url_for('groups.deactivate_group', group_id=group.id),
                               json={'active': False})
        # THEN assert group is inactive
        assert resp.status_code == 200
        assert resp.json['active'] == False

    resp = auth_client.put(url_for('groups.deactivate_group', group_id=500), json={'active': False})
    # THEN assert group is not found
    assert resp.status_code == 404


# ---- Meeting


@pytest.mark.smoke
def test_create_meeting(auth_client):
    # GIVEN an empty database
    generate_managers(auth_client)
    create_multiple_groups(auth_client.sqla, 1)
    # WHEN we add in some events

    count = random.randint(5, 15)

    # WHEN
    for i in range(count):
        resp = auth_client.post(url_for('groups.create_meeting'), json=meeting_object_factory(auth_client.sqla))
        assert resp.status_code == 201

    # THEN
    assert auth_client.sqla.query(Meeting).count() == count

    payload = meeting_object_factory(auth_client.sqla)
    del payload['active']

    resp = auth_client.post(url_for('groups.create_meeting'), json=payload)
    assert resp.status_code == 201


@pytest.mark.smoke
def test_create_invalid_meeting(auth_client):
    # GIVEN an empty database
    generate_managers(auth_client)
    create_multiple_groups(auth_client.sqla, 1)
    # WHEN we attempt to add invalid events
    count = random.randint(5, 15)

    for i in range(count):
        meeting = meeting_object_factory(auth_client.sqla)
        meeting['invalid_field'] = 4
        resp = auth_client.post(url_for('groups.create_meeting'), json=meeting)

        # THEN the response should have the correct code
        assert resp.status_code == 422

    # AND the database should still be empty
    assert auth_client.sqla.query(Meeting).count() == 0


@pytest.mark.smoke
def test_read_all_meetings(auth_client):
    # Testing an empty Database
    resp = auth_client.get(url_for('groups.read_all_meetings'))
    assert resp.status_code == 404
    # GIVEN a database with a number of meetings
    count = random.randint(3, 11)
    generate_managers(auth_client)
    create_multiple_groups(auth_client.sqla, count)
    create_multiple_meetings(auth_client.sqla, count)

    # WHEN reading all of them
    resp = auth_client.get(url_for('groups.read_all_meetings'))
    # THEN we expect the correct status code
    assert resp.status_code == 200

    meetings_count = auth_client.sqla.query(Meeting).count()
    # THEN the number of meetings should agree with the number in the database
    assert len(resp.json) == meetings_count

    # THEN each one of them should correspond to something in the database
    for meeting in resp.json:
        keylist = ['active', 'address_id', 'group_id', 'id']
        filtered_meeting = {k: meeting[k] for k in meeting if k in keylist}
        assert auth_client.sqla.query(Meeting).filter_by(**filtered_meeting).count() == 1


def generate_addresses(auth_client, count=1):
    Country.load_from_file()
    create_multiple_areas(auth_client.sqla, count)
    create_multiple_addresses(auth_client.sqla, count)


@pytest.mark.smoke
def test_read_all_meetings_by_group(auth_client):
    # GIVEN a database with mutliple meetings connected with a particular group
    count = random.randint(3, 11)
    generate_managers(auth_client)
    create_multiple_groups(auth_client.sqla, 3)
    group_ids = [attr_tuple[0] for attr_tuple in auth_client.sqla.query(Group.id).all()]
    group_id_with_meetings = group_ids[0]
    meetings = []
    for _ in range(count):
        meeting = meeting_object_factory(auth_client.sqla)
        meeting["group_id"] = group_id_with_meetings
        valid_meeting = MeetingSchema().load(meeting)
        meetings.append(Meeting(**valid_meeting))
    auth_client.sqla.add_all(meetings)
    auth_client.sqla.commit()

    # WHEN reading all of them by group
    resp = auth_client.get(url_for('groups.read_all_meetings_by_group', group_id=group_id_with_meetings))
    # THEN we expect the correct status code
    assert resp.status_code == 200

    meetings_count = auth_client.sqla.query(Meeting).filter_by(group_id=group_id_with_meetings).count()
    # THEN the number of meetings should agree with the number in the database
    assert len(resp.json) == meetings_count

    # THEN each one of them should correspond to something in the database
    for meeting in resp.json:
        keylist = ['active', 'address_id', 'group_id', 'id']
        filtered_meeting = {k: meeting[k] for k in meeting if k in keylist}
        assert auth_client.sqla.query(Meeting).filter_by(**filtered_meeting).count() == 1

    # WHEN the group has no meetings
    group_id_with_no_meetings = group_ids[1]
    resp = auth_client.get(url_for('groups.read_all_meetings_by_group', group_id=group_id_with_no_meetings))
    # THEN we expect an error
    assert resp.status_code == 404


@pytest.mark.smoke
def test_read_all_meetings_by_location(auth_client):
    # GIVEN a database with multiple meetings with locations
    count = random.randint(3, 11)
    generate_addresses(auth_client, 2)
    generate_managers(auth_client)
    create_multiple_groups(auth_client.sqla, 3)

    address_ids = [attr_tuple[0] for attr_tuple in auth_client.sqla.query(Address.id).all()]
    address_id_with_meetings = address_ids[0]
    meetings = []
    for _ in range(count):
        meeting = meeting_object_factory(auth_client.sqla)
        meeting["address_id"] = address_id_with_meetings
        valid_meeting = MeetingSchema().load(meeting)
        meetings.append(Meeting(**valid_meeting))
    auth_client.sqla.add_all(meetings)
    auth_client.sqla.commit()

    # WHEN reading all of them by address
    resp = auth_client.get(url_for('groups.read_all_meetings_by_location', address_id=address_id_with_meetings))
    # THEN we expect the correct status code
    assert resp.status_code == 200

    meetings_count = auth_client.sqla.query(Meeting).filter_by(address_id=address_id_with_meetings).count()
    # THEN the number of meetings should agree with the number in the database
    assert len(resp.json) == meetings_count

    # THEN each one of them should correspond to something in the database
    for meeting in resp.json:
        keylist = ['active', 'address_id', 'group_id', 'id']
        filtered_meeting = {k: meeting[k] for k in meeting if k in keylist}
        assert auth_client.sqla.query(Meeting).filter_by(**filtered_meeting).count() == 1

    # WHEN the address has no meetings
    address_id_with_no_meetings = address_ids[1]
    resp = auth_client.get(url_for('groups.read_all_meetings_by_location', address_id=address_id_with_no_meetings))
    # THEN we expect an error
    assert resp.status_code == 404


@pytest.mark.smoke
def test_read_one_meeting(auth_client):
    # GIVEN a database with a number of meetings
    count = random.randint(3, 11)
    generate_managers(auth_client)
    create_multiple_groups(auth_client.sqla, count)
    create_multiple_meetings(auth_client.sqla, count)

    meeting = auth_client.sqla.query(Meeting).first()

    # WHEN we read one of them
    resp = auth_client.get(url_for('groups.read_one_meeting', meeting_id=meeting.id))
    # THEN we expect the correct status code
    assert resp.status_code == 200
    # THEN we expect the returned fields to be correct
    for attr in ['active', 'address_id', 'group_id']:
        assert resp.json[attr] == meeting.__dict__[attr]
    # WHEN we try to read a non-existant meeting
    resp = auth_client.get(url_for('groups.read_one_meeting', meeting_id=-1))
    # THEN we expect an error code
    assert resp.status_code == 404


@pytest.mark.smoke
def test_update_meeting(auth_client):
    # GIVEN a database with a number of meetings
    count = random.randint(3, 11)
    generate_managers(auth_client)
    create_multiple_groups(auth_client.sqla, count)
    create_multiple_meetings(auth_client.sqla, count)

    # WHEN we update one meeting
    meeting = auth_client.sqla.query(Meeting).first()

    payload = {}
    new_meeting = meeting_object_factory(auth_client.sqla)

    payload['group_id'] = new_meeting['group_id']
    payload['when'] = new_meeting['when']

    resp = auth_client.patch(url_for('groups.update_meeting', meeting_id=meeting.id), json=payload)

    # THEN we assume the correct status code
    assert resp.status_code == 200

    # THEN we assume the correct content in the returned object
    assert resp.json['group_id'] == payload['group_id']
    assert parser.parse(resp.json['when']).replace(tzinfo=None) == parser.parse(payload['when']).replace(tzinfo=None)

    resp = auth_client.patch(url_for('groups.update_meeting', meeting_id=500), json=payload)
    assert resp.status_code == 404


@pytest.mark.smoke
def test_invalid_update_meeting(auth_client):
    # GIVEN a database with a number of groups and meetings
    count = random.randint(3, 11)
    generate_managers(auth_client)
    create_multiple_groups(auth_client.sqla, count)
    create_multiple_meetings(auth_client.sqla, count)

    valid_meeting = meeting_object_factory(auth_client.sqla)

    # WHEN we try to update an invalid meeting
    resp = auth_client.patch(url_for('groups.update_meeting', meeting_id=-1), json=valid_meeting)
    # THEN we expect an error code
    assert resp.status_code == 404

    original_meeting = auth_client.sqla.query(Meeting).first()
    modified_meeting = valid_meeting
    modified_meeting['invalid_field'] = 4

    # WHEN we try to update an existing meeting with invalid payload
    resp = auth_client.patch(url_for('groups.update_meeting', meeting_id=original_meeting.id), json=modified_meeting)

    # THEN we assume the incorrect status code
    assert resp.status_code == 422


def test_delete_meeting(auth_client):
    # GIVEN a database with meetings and attendances
    count = random.randint(3, 11)
    generate_managers(auth_client)
    create_multiple_groups(auth_client.sqla, count)
    create_multiple_members(auth_client.sqla, count)
    create_multiple_meetings(auth_client.sqla, count)
    create_attendance(auth_client.sqla, 1)
    # WHEN we delete a meeting
    meeting_id = auth_client.sqla.query(Meeting.id).first()[0]
    resp = auth_client.delete(url_for('groups.delete_meeting', meeting_id=meeting_id))
    # THEN we assume the correct status code
    assert resp.status_code == 200
    # THEN we should not have that meeting in the database
    assert auth_client.sqla.query(Meeting).filter_by(id=meeting_id).count() == 0
    # THEN we should not have any attendances related to that meeting in the attendance table
    assert auth_client.sqla.query(Attendance).filter_by(meeting_id=meeting_id).count() == 0

    # WHEN we delete that meeting again
    resp = auth_client.delete(url_for('groups.delete_meeting', meeting_id=meeting_id))
    # THEN we should get an error code
    assert resp.status_code == 404


def test_activate_meeting(auth_client):
    # GIVEN a database with inactive meetings and attendances
    count = random.randint(3, 11)
    generate_managers(auth_client)
    create_multiple_groups(auth_client.sqla, count)
    inactive_meetings = []
    for _ in range(count):
        inactive_meeting = meeting_object_factory(auth_client.sqla)
        inactive_meeting["active"] = False
        valid_meeting = MeetingSchema().load(inactive_meeting)
        inactive_meetings.append(Meeting(**valid_meeting))
    auth_client.sqla.add_all(inactive_meetings)
    auth_client.sqla.commit()

    # WHEN we active one meeting
    meeting = auth_client.sqla.query(Meeting).filter_by(active=False).first()
    resp = auth_client.put(url_for('groups.activate_meeting', meeting_id=meeting.id))
    # THEN we expect the right status code
    assert resp.status_code == 200
    # THEN we expect the meeting to be activated
    assert auth_client.sqla.query(Meeting).filter_by(id=meeting.id).first().active == True

    # WHEN we activate a non-existant meeting
    resp = auth_client.put(url_for('groups.activate_meeting', meeting_id=-1))
    # THEN we expect an error code
    assert resp.status_code == 404


def test_deactivate_meeting(auth_client):
    # GIVEN a database with active meetings and attendances
    count = random.randint(3, 11)
    generate_managers(auth_client)
    create_multiple_groups(auth_client.sqla, count)
    active_meetings = []
    for _ in range(count):
        active_meeting = meeting_object_factory(auth_client.sqla)
        active_meeting["active"] = True
        valid_meeting = MeetingSchema().load(active_meeting)
        active_meetings.append(Meeting(**valid_meeting))
    auth_client.sqla.add_all(active_meetings)
    auth_client.sqla.commit()

    # WHEN we deactivate one meeting
    meeting = auth_client.sqla.query(Meeting).filter_by(active=True).first()
    resp = auth_client.put(url_for('groups.deactivate_meeting', meeting_id=meeting.id))
    # THEN we expect the right status code
    assert resp.status_code == 200
    # THEN we expect the meeting to be deactivated
    assert auth_client.sqla.query(Meeting).filter_by(id=meeting.id).first().active == False

    # WHEN we deactivate a non-existant meeting
    resp = auth_client.put(url_for('groups.deactivate_meeting', meeting_id=-1))
    # THEN we expect an error code
    assert resp.status_code == 404


# ---- Member


@pytest.mark.smoke
def test_create_member(auth_client):
    # GIVEN database with some groups and people
    count = random.randint(3, 11)
    generate_managers(auth_client)
    create_multiple_groups(auth_client.sqla, 2)

    # WHEN we try to create a member
    payload = member_object_factory(auth_client.sqla)
    resp = auth_client.post(url_for('groups.create_member'), json=payload)
    # THEN we expect the correct status code
    assert resp.status_code == 201
    # THEN we expect that member to be present in database
    assert 1 == auth_client.sqla.query(Member).filter_by( \
        person_id=payload["person_id"], \
        group_id=payload["group_id"], \
        ).count()

    # WHEN we try to create a member with an invalid payload
    invalid_payload = {'invalid_field': 1}
    resp = auth_client.post(url_for('groups.create_member'), json=invalid_payload)
    # THEN we expect an error
    assert resp.status_code == 422

    # WHEN we try to recreate the same member
    resp = auth_client.post(url_for('groups.create_member'), json=payload)
    # THEN we expect an error
    assert resp.status_code == 409


@pytest.mark.smoke
def test_read_all_members(auth_client):
    # Testing an empty Database
    resp = auth_client.get(url_for('groups.read_all_members'))
    assert resp.status_code == 404
    # GIVEN a database with some members
    generate_managers(auth_client)
    create_multiple_groups(auth_client.sqla, 4)
    create_multiple_people(auth_client.sqla, 4)
    create_multiple_members(auth_client.sqla, 4)
    members_count = auth_client.sqla.query(Member).count()
    # WHEN reading all of them
    resp = auth_client.get(url_for('groups.read_all_members'))
    # THEN we should get the correct code
    assert resp.status_code == 200
    # THEN we should get the correct count
    assert len(resp.json) == members_count
    # THEN each one of them should correspond to something in the database
    for member in resp.json:
        keylist = ['active', 'group_id', 'person_id', 'joined', 'id']
        filtered_member = {k: member[k] for k in member if k in keylist}
        assert auth_client.sqla.query(Member).filter_by(**filtered_member).count() == 1


@pytest.mark.smoke
def test_read_one_member(auth_client):
    # GIVEN a database with some members
    count = random.randint(3, 11)
    generate_managers(auth_client)
    create_multiple_groups(auth_client.sqla, count)
    create_multiple_members(auth_client.sqla, count)

    members = auth_client.sqla.query(Member).all()
    # WHEN we ask for the members one by one
    for member in members:
        resp = auth_client.get(url_for('groups.read_one_member', member_id=member.id))
        # THEN we expect the correct status code
        assert resp.status_code == 200
        # THEN we expect each of them to correspond to the member in the database
        keylist = ['active', 'group_id', 'person_id',
                   'id']  # skipping 'joined', because datetimes come back in a slightly different format, but information is the same.
        for attr in keylist:
            assert resp.json[attr] == member.__dict__[attr]
    # WHEN we ask for a non-existant member
    resp = auth_client.get(url_for('groups.read_one_member', member_id=-1))
    # THEN we expect an error code
    assert resp.status_code == 404


@pytest.mark.smoke
def test_update_member(auth_client):
    # GIVEN a database with a number of members
    count = random.randint(3, 11)
    generate_managers(auth_client)
    create_multiple_groups(auth_client.sqla, 3)
    create_multiple_members(auth_client.sqla, count)

    # WHEN we update one event
    member = auth_client.sqla.query(Member).first()
    payload = member_object_factory(auth_client.sqla)
    resp = auth_client.patch(url_for('groups.update_member', member_id=member.id), json=payload)
    # THEN we assume the correct status code
    assert resp.status_code == 200
    # THEN we assume the correct content in the returned object
    assert resp.json['group_id'] == payload['group_id']
    assert resp.json['person_id'] == payload['person_id']
    assert resp.json['joined'] == payload['joined']
    assert resp.json['active'] == payload['active']

    # WHEN we try to update a member with an invalid payload
    invalid_payload = {'invalid_field': 1}
    resp = auth_client.patch(url_for('groups.update_member', member_id=member.id), json=invalid_payload)
    # THEN we expect an error
    assert resp.status_code == 422

    # WHEN we try to update a nonexistent member
    auth_client.sqla.delete(member)
    auth_client.sqla.commit()
    resp = auth_client.patch(url_for('groups.update_member', member_id=member.id), json=payload)
    assert resp.status_code == 404


@pytest.mark.smoke
def test_activate_member(auth_client):
    # GIVEN a database with a number of members
    generate_managers(auth_client)
    create_multiple_groups(auth_client.sqla, 4)
    create_multiple_people(auth_client.sqla, 4)
    create_multiple_members(auth_client.sqla, 4)

    members = auth_client.sqla.query(Member).all()

    # WHEN member is changed to active
    for member in members:
        resp = auth_client.put(url_for('groups.activate_member', member_id=member.id))
        print(member)
        # THEN assert group is active
        assert resp.status_code == 200
        assert resp.json['active'] == True

    resp = auth_client.put(url_for('groups.activate_member', member_id=500))
    # THEN assert group is not found
    assert resp.status_code == 404


@pytest.mark.smoke
def test_deactivate_member(auth_client):
    # GIVEN a database with a number of members
    generate_managers(auth_client)
    create_multiple_groups(auth_client.sqla, 4)
    create_multiple_people(auth_client.sqla, 4)
    create_multiple_members(auth_client.sqla, 4)

    members = auth_client.sqla.query(Member).all()

    # WHEN member is changed to active
    for member in members:
        resp = auth_client.put(url_for('groups.deactivate_member', member_id=member.id))
        print(member)
        # THEN assert group is active
        assert resp.status_code == 200
        assert resp.json['active'] == False

    resp = auth_client.put(url_for('groups.activate_member', member_id=500))
    # THEN assert group is not found
    assert resp.status_code == 404


# ---- Attendance


@pytest.mark.smoke
def test_create_attendance(auth_client):
    # GIVEN a database with some members and meetings
    generate_managers(auth_client)
    create_multiple_groups(auth_client.sqla, 4)
    count_meetings = random.randint(15, 20)
    count_members = random.randint(3, 5)
    create_multiple_meetings(auth_client.sqla, count_meetings)
    create_multiple_members(auth_client.sqla, count_members)
    # WHEN we create a meeting to a member
    meeting_id = auth_client.sqla.query(Meeting.id).first()[0]
    member_id = auth_client.sqla.query(Meeting.id).first()[0]
    payload = {
        'member_id': member_id,
        'meeting_id': meeting_id
    }
    resp = auth_client.post(url_for('groups.create_attendance'), json=payload)
    # THEN we expect the right status code
    assert resp.status_code == 201
    # THEN we expect the entry to be created
    queried_attendance_count = auth_client.sqla.query(Attendance).filter(Attendance.meeting_id == payload['meeting_id'],
                                                                         Attendance.member_id == payload[
                                                                             'member_id']).count()
    assert queried_attendance_count == 1

    # WHEN we create an invalid meeting
    invalid_payload = {
        'member_id': member_id,
        'meeting_id': meeting_id,
        'invalid_field': 23
    }
    resp = auth_client.post(url_for('groups.create_attendance'), json=invalid_payload)
    # THEN we expect an error
    assert resp.status_code == 422

    # WHEN we create an existing attendance
    resp = auth_client.post(url_for('groups.create_attendance'), json=payload)
    # THEN we expect an error
    assert resp.status_code == 409


@pytest.mark.smoke
def test_read_all_attendance(auth_client):
    # Testing an empty Database
    resp = auth_client.get(url_for('groups.read_all_attendance'))
    assert resp.status_code == 404
    # GIVEN a database with some attendances
    generate_managers(auth_client)
    create_multiple_groups(auth_client.sqla, 4)
    create_multiple_people(auth_client.sqla, 4)
    create_multiple_members(auth_client.sqla, 4)
    create_multiple_meetings(auth_client.sqla, 4)
    create_attendance(auth_client.sqla, 0.75)
    attendances_count = auth_client.sqla.query(Attendance).count()
    # WHEN reading all of them
    resp = auth_client.get(url_for('groups.read_all_attendance'))
    # THEN we should get the correct code
    assert resp.status_code == 200
    # THEN we should get the correct count
    assert len(resp.json) == attendances_count
    # THEN each one of them should correspond to something in the database
    for attendance in resp.json:
        assert auth_client.sqla.query(Attendance).filter( \
            Attendance.member_id == attendance['member_id'], \
            Attendance.meeting_id == attendance['meeting_id'], \
            ).count() == 1


def test_read_attendance_by_member(auth_client):
    # Testing an empty Database
    resp = auth_client.get(url_for('groups.read_attendance_by_member', member_id=500))
    assert resp.status_code == 404
    # GIVEN a database with some attendances
    generate_managers(auth_client)
    create_multiple_groups(auth_client.sqla, 4)
    create_multiple_people(auth_client.sqla, 4)
    create_multiple_members(auth_client.sqla, 4)
    create_multiple_meetings(auth_client.sqla, 4)
    create_attendance(auth_client.sqla, 0.75)
    # WHEN we read attendances by member id
    member_id = auth_client.sqla.query(Member.id).first()[0]
    queried_attendance_count = auth_client.sqla.query(Attendance).filter_by(member_id=member_id).count()
    resp = auth_client.get(url_for('groups.read_attendance_by_member', member_id=member_id))
    # THEN we should get the correct code
    assert resp.status_code == 200
    # THEN the content returned should have the same length
    assert queried_attendance_count == len(resp.json)
    # THEN each of the attendance should correspond to one in the database
    for attendance in resp.json:
        assert 1 == auth_client.sqla.query(Attendance).filter_by(member_id=attendance["member_id"],
                                                                 meeting_id=attendance["meeting_id"]).count()


def test_read_attendance_by_meeting(auth_client):
    # Testing an empty Database
    resp = auth_client.get(url_for('groups.read_attendance_by_meeting', meeting_id=599))
    assert resp.status_code == 404
    # GIVEN a database with some attendances
    generate_managers(auth_client)
    create_multiple_groups(auth_client.sqla, 4)
    create_multiple_people(auth_client.sqla, 4)
    create_multiple_meetings(auth_client.sqla, 4)
    create_multiple_members(auth_client.sqla, 4)
    create_attendance(auth_client.sqla, 0.75)
    # WHEN we read attendances by meeting id
    meeting_id = auth_client.sqla.query(Meeting.id).first()[0]
    queried_attendance_count = auth_client.sqla.query(Attendance).filter_by(meeting_id=meeting_id).count()
    resp = auth_client.get(url_for('groups.read_attendance_by_meeting', meeting_id=meeting_id))
    # THEN we should get the correct code
    assert resp.status_code == 200
    # THEN the content returned should have the same length
    assert queried_attendance_count == len(resp.json)
    # THEN each of the attendance should correspond to one in the database
    for attendance in resp.json:
        assert 1 == auth_client.sqla.query(Attendance).filter_by(meeting_id=attendance["meeting_id"],
                                                                 member_id=attendance["member_id"]).count()


def test_delete_attendance(auth_client):
    # GIVEN a database with a number of attendance
    generate_managers(auth_client)
    create_multiple_groups(auth_client.sqla, 4)
    create_multiple_people(auth_client.sqla, 4)
    create_multiple_meetings(auth_client.sqla, 4)
    create_multiple_members(auth_client.sqla, 4)
    create_attendance(auth_client.sqla, 0.75)
    attendance_count = auth_client.sqla.query(Attendance).count()

    # WHEN we delete one attendance
    queried_attendance = auth_client.sqla.query(Attendance).first()
    payload = {
        'meeting_id': queried_attendance.meeting_id,
        'member_id': queried_attendance.member_id
    }
    resp = auth_client.delete(url_for('groups.delete_attendance'), json=payload)
    # THEN we expect the correct status code
    assert resp.status_code == 204
    # THEN the total number of attendance should be the right number
    assert attendance_count - 1 == auth_client.sqla.query(Attendance).count()
    # THEN the deleted attendance should be absent from the database
    assert auth_client.sqla.query(Attendance).filter_by( \
        meeting_id=queried_attendance.meeting_id, \
        member_id=queried_attendance.member_id).count() == 0

    # WHEN we delete with an invalid payload
    invalid_payload = {
        'invalid_field': 4,
        'meeting_id': queried_attendance.meeting_id,
        'member_id': queried_attendance.member_id
    }
    resp = auth_client.delete(url_for('groups.delete_attendance'), json=invalid_payload)
    # THEN we expect an error
    assert resp.status_code == 422

    # WHEN we delete a non-existant attendance (delete the same attendance again)
    resp = auth_client.delete(url_for('groups.delete_attendance'), json=payload)
    # THEN we expect an error
    assert resp.status_code == 404


@pytest.mark.smoke
def test_repr_group(auth_client):
    # GIVEN a DB with a manager
    # generate_managers(auth_client)
    group = Group()
    group.__repr__()


@pytest.mark.smoke
def test_repr_meeting(auth_client):
    # GIVEN a DB with a manager
    # generate_managers(auth_client)
    meeting = Meeting()
    meeting.__repr__()


@pytest.mark.smoke
def test_repr_member(auth_client):
    # GIVEN a DB with a manager
    # generate_managers(auth_client)
    member = Member()
    member.__repr__()


@pytest.mark.smoke
def test_repr_attendance(auth_client):
    # GIVEN a DB with a manager
    # generate_managers(auth_client)
    attendance = Attendance()
    attendance.__repr__()


@pytest.mark.smoke
def test_add_group_images(auth_client):
    # GIVEN a set of groups and images
    count = random.randint(3, 6)
    # create_multiple_managers(auth_client.sqla, count)
    create_multiple_groups(auth_client.sqla, count)
    create_test_images(auth_client.sqla)

    groups = auth_client.sqla.query(Group).all()
    images = auth_client.sqla.query(Image).all()

    # WHEN an image is requested to be tied to each group
    for i in range(count):
        print(i)
        resp = auth_client.post(url_for('groups.add_group_images', group_id=groups[i].id, image_id=images[i].id))

        # THEN expect the request to run OK
        assert resp.status_code == 201

        # THEN expect the group to have a single image
        assert len(auth_client.sqla.query(Group).filter_by(id=groups[i].id).first().images) == 1


@pytest.mark.smoke
def test_add_group_images_no_exist(auth_client):
    # GIVEN a set of groups and images
    count = random.randint(3, 6)
    create_multiple_groups(auth_client.sqla, count)
    create_test_images(auth_client.sqla)

    groups = auth_client.sqla.query(Group).all()
    images = auth_client.sqla.query(Image).all()

    # WHEN a no existant image is requested to be tied to an group
    resp = auth_client.post(url_for('groups.add_group_images', group_id=1, image_id=len(images) + 1))

    # THEN expect the image not to be found
    assert resp.status_code == 404

    # WHEN an image is requested to be tied to a no existant group
    resp = auth_client.post(url_for('groups.add_group_images', group_id=count + 1, image_id=1))

    # THEN expect the group not to be found
    assert resp.status_code == 404


@pytest.mark.smoke
def test_add_group_images_already_exist(auth_client):
    # GIVEN a set of groups, images, and group_image relationships
    count = random.randint(3, 6)
    create_multiple_groups(auth_client.sqla, count)
    create_test_images(auth_client.sqla)
    create_images_groups(auth_client.sqla)

    group_images = auth_client.sqla.query(ImageGroup).all()

    # WHEN existing group_image relationships are requested to be created
    for group_image in group_images:
        resp = auth_client.post(
            url_for('groups.add_group_images', group_id=group_image.group_id, image_id=group_image.image_id))

        # THEN expect the request to be unprocessable
        assert resp.status_code == 422


@pytest.mark.smoke
def test_delete_group_image(auth_client):
    # GIVEN a set of groups, images, and group_image relationships
    count = random.randint(3, 6)
    create_multiple_groups(auth_client.sqla, count)
    create_test_images(auth_client.sqla)
    create_images_groups(auth_client.sqla)

    valid_group_image = auth_client.sqla.query(ImageGroup).first()

    # WHEN the group_image relationships are requested to be deleted
    resp = auth_client.delete(
        url_for('groups.delete_group_image', group_id=valid_group_image.group_id, image_id=valid_group_image.image_id))

    # THEN expect the delete to run OK
    assert resp.status_code == 204


@pytest.mark.smoke
def test_delete_group_image_no_exist(auth_client):
    # GIVEN an empty database

    # WHEN a group_image relationship is requested to be deleted
    resp = auth_client.delete(
        url_for('groups.delete_group_image', group_id=random.randint(1, 8), image_id=random.randint(1, 8)))

    # THEN expect the requested row to not be found
    assert resp.status_code == 404


# # ---- Manager: Moved from people module
# 
# @pytest.mark.smoke
# def test_create_manager(auth_client):
#     # GIVEN an empty database
#     person_count = random.randint(10, 20)
#     manager_count = random.randint(5, person_count)
# 
#     # WHEN we create a random number of new managers and managers in the database
#     create_multiple_people(auth_client.sqla, person_count)
#     #create_multiple_accounts(auth_client.sqla, 1)
# 
#     for i in range(manager_count):
#         resp = auth_client.post(url_for('people.create_manager'),
#                                 json=manager_object_factory(auth_client.sqla, 'first level'))
#         assert resp.status_code == 201
# 
#     # THEN we end up with the proper number of managers in the database
#     assert auth_client.sqla.query(Manager).count() == manager_count
# 
# 
# @pytest.mark.smoke
# def test_create_manager_invalid(auth_client):
#     # GIVEN a set of people and accounts
#     count = random.randint(3, 6)
#     create_multiple_people(auth_client.sqla, count)
#     #create_multiple_accounts(auth_client.sqla, 1)
# 
#     persons = auth_client.sqla.query(Person).all()
# 
#     # GIVEN managers with bad data for each account
#     for person in persons:
#         new_manager = manager_object_factory(auth_client.sqla, fake.sentences(nb=1)[0])
#         new_manager[fake.word()] = fake.word()
# 
#         # WHEN a request is made to make a manager with bad data
#         resp = auth_client.post(url_for('people.create_manager'), json=new_manager)
# 
#         # THEN expect request to be unprocessable
#         assert resp.status_code == 422
# 
#     # THEN expect no managers to be created
#     assert auth_client.sqla.query(Manager).count() == 0
# 
# 
# @pytest.mark.smoke
# def test_read_all_managers(auth_client):
#     # GIVEN a DB with a collection of managers.
#     person_count = random.randint(10, 20)
#     manager_count = random.randint(5, person_count)
#     create_multiple_people(auth_client.sqla, person_count)
#     #create_multiple_accounts(auth_client.sqla, 1)
#     create_multiple_managers(auth_client.sqla, manager_count)
#     # WHEN we request all managers from the server
#     resp = auth_client.get(url_for('people.read_all_managers', locale='en-US'))
#     # THEN the count matches the number of entries in the database
#     assert resp.status_code == 200
#     assert len(resp.json) == manager_count
# 
# 
# @pytest.mark.smoke
# def test_read_one_manager(auth_client):
#     # GIVEN a DB with a collection of managers.
#     person_count = random.randint(10, 20)
#     manager_count = random.randint(5, person_count)
#     create_multiple_people(auth_client.sqla, person_count)
#     #create_multiple_accounts(auth_client.sqla, 1)
#     create_multiple_managers(auth_client.sqla, manager_count)
# 
#     # WHEN we ask for them all
#     managers = auth_client.sqla.query(Manager).all()
# 
#     # THEN we expect the same number
#     assert len(managers) == manager_count
# 
#     # WHEN we request each of them from the server
#     for manager in managers:
#         resp = auth_client.get(url_for('people.read_one_manager', manager_id=manager.id, locale='en-US'))
#         # THEN we find a matching manager
#         assert resp.status_code == 200
#         assert resp.json['person_id'] == manager.person_id
#         assert resp.json['manager_id'] == manager.manager_id
#         assert resp.json['description_i18n'] == manager.description_i18n
# 
# 
# @pytest.mark.smoke
# def test_read_one_manager_invalid(auth_client):
#     # GIVEN an empty database
# 
#     # WHEN a request is made to read a manager that does not exist
#     resp = auth_client.get(url_for('people.read_one_manager', manager_id=random.randint(1, 8)))
# 
#     # THEN expect requested manager not to be found
#     assert resp.status_code == 404
# 
# 
# @pytest.mark.smoke
# def test_update_manager(auth_client):
#     # GIVEN a DB with a collection of managers.
#     person_count = random.randint(10, 20)
#     manager_count = random.randint(5, person_count)
#     create_multiple_people(auth_client.sqla, person_count)
#     #create_multiple_accounts(auth_client.sqla, 1)
#     create_multiple_managers(auth_client.sqla, manager_count)
# 
#     managers = auth_client.sqla.query(Manager).all()
#     persons = auth_client.sqla.query(Person).all()
# 
#     update_manager = random.choice(managers)
# 
#     new_person_id = update_manager.person_id
#     while new_person_id == update_manager.person_id:
#         new_person_id = random.choice(persons).id
# 
#     new_manager_id = update_manager.manager_id
#     while new_manager_id == update_manager.manager_id or new_manager_id == update_manager.id:
#         new_manager_id = random.choice(managers).id
# 
#     update_json = {
#         'person_id': new_person_id,
#         'manager_id': new_manager_id,
#         'description_i18n': update_manager.description_i18n
#     }
# 
#     # WHEN
#     resp = auth_client.patch(url_for('people.update_manager', manager_id=update_manager.id), json=update_json)
#     # THEN
#     assert resp.status_code == 200
#     assert resp.json['person_id'] == new_person_id
#     assert resp.json['manager_id'] == new_manager_id
# 
# 
# @pytest.mark.smoke
# def test_update_manager_invalid(auth_client):
#     # GIVEN a set of people, accounts, and managers
#     count = random.randint(3, 6)
#     create_multiple_people(auth_client.sqla, count)
#     #create_multiple_accounts(auth_client.sqla, 1)
#     create_multiple_managers(auth_client.sqla, count)
# 
#     managers = auth_client.sqla.query(Manager).all()
# 
#     # GIVEN bad modification data
#     for manager in managers:
#         mod = {}
#         flips = (flip(), flip(), flip())
#         if flips[0]:
#             mod['person_id'] = None
#         if flips[1]:
#             mod['description_i18n'] = None
#         if flips[2] or not (flips[0] or flips[1]):
#             mod[fake.word()] = fake.word()
# 
#         # WHEN a manager is requested to be updated with bad data
#         resp = auth_client.patch(url_for('people.update_manager', manager_id=manager.id), json=mod)
# 
#         # THEN expect the request to be unprocessable
#         assert resp.status_code == 422
# 
# 
# @pytest.mark.smoke
# def test_delete_manager(auth_client):
#     # GIVEN a DB with a collection of managers.
#     person_count = random.randint(10, 20)
#     manager_count = random.randint(5, person_count)
#     create_multiple_people(auth_client.sqla, person_count)
#     #create_multiple_accounts(auth_client.sqla, 1)
#     create_multiple_managers(auth_client.sqla, manager_count)
# 
#     managers = auth_client.sqla.query(Manager).all()
#     persons = auth_client.sqla.query(Person).all()
# 
#     delete_manager = managers[0]
#     subordinate = managers[1]
# 
#     update_json = {
#         'manager_id': delete_manager.id
#     }
#     auth_client.patch(url_for('people.update_manager', manager_id=subordinate.id), json=update_json)
# 
#     # WHEN we delete the manager
#     resp = auth_client.delete(url_for('people.delete_manager', manager_id=delete_manager.id))
# 
#     # THEN the manager and all references to that manager are deleted
#     assert resp.status_code == 204
#     assert auth_client.sqla.query(Manager).filter_by(id=delete_manager.id).first() == None
#     assert auth_client.sqla.query(Manager).filter_by(id=subordinate.id).first().manager_id == None
# 
# 
# @pytest.mark.smoke
# def test_delete_manager_no_exist(auth_client):
#     # GIVEN an empty database
# 
#     # WHEN a manager is requested to be deleted
#     resp = auth_client.delete(url_for('people.delete_manager', manager_id=random.randint(1, 8)))
# 
#     # THEN expect the manager not to be found
#     assert resp.status_code == 404
# 
# 
# @pytest.mark.smoke
# def test_delete_manager_with_subordinate(auth_client):
#     # GIVEN a set of people, accounts, and managers
#     count = random.randint(3, 6)
#     create_multiple_people(auth_client.sqla, count * 2)
#     #create_multiple_accounts(auth_client.sqla, 1)
#     create_multiple_managers(auth_client.sqla, count * 2)
# 
#     # GIVEN half of the managers are subordinates of the others
#     for i in range(1, count + 1):
#         auth_client.sqla.query(Manager).filter(Manager.id == i).update({"manager_id": i + count})
#         auth_client.sqla.commit()
# 
#     # WHEN superiors are requested to be deleted
#     for i in range(1, count + 1):
#         resp = auth_client.delete(url_for('people.delete_manager', manager_id=i + count))
# 
#         # THEN expect the delete to run OK
#         assert resp.status_code == 204
# 
#         # THEN expect that superior was deleted
#         assert auth_client.sqla.query(Manager).count() == count * 2 - i
# 
#         # THEN expect relationship with subordinate to be broken
#         assert auth_client.sqla.query(Manager).filter(Manager.id == i).first().manager_id is None
# 
# 
# @pytest.mark.smoke
# def test_create_manager_with_superior(auth_client):
#     # GIVEN a set of people, accounts, and managers
#     count = random.randint(3, 6)
#     create_multiple_people(auth_client.sqla, count * 2)
#     #create_multiple_accounts(auth_client.sqla, 1)
#     create_multiple_managers(auth_client.sqla, count)
# 
#     superiors = auth_client.sqla.query(Manager).all()
# 
#     # GIVEN data for subordinate managers
#     for superior in superiors:
#         new_manager = manager_object_factory(auth_client.sqla, fake.sentences(nb=1)[0])
#         new_manager['manager_id'] = superior.id
# 
#         # WHEN subordinates are requested to be created
#         resp = auth_client.post(url_for('people.create_manager'), json=new_manager)
# 
#         # THEN expect the create to run OK
#         resp.status_code == 201
# 
#     # THEN expect the right number of managers to be created
#     assert auth_client.sqla.query(Manager).count() == count * 2
# 
# 
# @pytest.mark.smoke
# def test_repr_manager(auth_client):
#     # GIVEN a DB with a manager
#     create_multiple_people(auth_client.sqla, 1)
#     #create_multiple_accounts(auth_client.sqla, 1)
#     create_multiple_managers(auth_client.sqla, 1)
#     managers = auth_client.sqla.query(Manager).all()
#     managers[0].__repr__()
