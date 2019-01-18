import math
import random

import pytest
from faker import Faker
from flask import url_for
from flask.json import jsonify
from flask_jwt_extended import create_access_token
from werkzeug.datastructures import Headers
from werkzeug.security import check_password_hash

from .models import Person, PersonSchema, AccountSchema, Account, RoleSchema, Role, Manager, ManagerSchema
from ..i18n.models import I18NKey, i18n_create, I18NLocale

class RandomLocaleFaker:
    """Generate multiple fakers for different locales."""

    def __init__(self, *locales):
        self.fakers = [Faker(loc) for loc in locales]

    def __call__(self):
        """Return a random faker."""
        return random.choice(self.fakers)


rl_fake = RandomLocaleFaker('en_US', 'es_MX')
fake = Faker()  # Generic faker; random-locale ones don't implement everything.


def flip():
    """Return true or false randomly."""
    return random.choice((True, False))


def person_object_factory():
    """Cook up a fake person."""
    person = {
        'lastName': rl_fake().last_name(),
        'secondLastName': rl_fake().last_name(),
        'gender': random.choice(('M', 'F')),
        'active': flip()
    }

    # Make the person's name match their gender.
    person['firstName'] = rl_fake().first_name_male(
    ) if person['gender'] == 'M' else rl_fake().first_name_female()
    person['active'] = True

    # These are all optional in the DB. Over time, we'll try all possibilities.
    if flip():
        person['birthday'] = rl_fake().date_of_birth(
            minimum_age=18).strftime('%Y-%m-%d')
    if flip():
        person['phone'] = rl_fake().phone_number()
    if flip():
        person['email'] = rl_fake().email()
    return person


def username_factory():
    return f"{fake.pystr(min_chars=5, max_chars=15)}{fake.pyint()}"


def account_object_factory(person_id):
    """Cook up a fake account."""
    fake = Faker()  # Use a generic one; others may not have all methods.
    account = {
        'username': username_factory(),
        'password': fake.password(),
        'personId': person_id
    }
    return account


def create_multiple_people(sqla, n):
    """Commit `n` new people to the database. Return their IDs."""
    person_schema = PersonSchema()
    new_people = []
    for i in range(n):
        valid_person = person_schema.load(person_object_factory())
        new_people.append(Person(**valid_person))
    sqla.add_all(new_people)
    sqla.commit()


def create_multiple_accounts(sqla, fraction=0.75):
    """Commit accounts for `fraction` of `people` in DB."""
    if fraction < 0.1 or fraction > 1.0:
        raise RuntimeError(f"Fraction ({fraction}) is out of bounds")

    all_people = sqla.query(Person).all()
    sample_people = random.sample(
        all_people, math.floor(len(all_people) * fraction))

    account_schema = AccountSchema()
    new_accounts = []
    for person in sample_people:
        valid_account = account_schema.load(account_object_factory(person.id))
        new_accounts.append(Account(**valid_account))
    sqla.add_all(new_accounts)
    sqla.commit()


# ---- Person

@pytest.mark.smoke
def test_read_person_fields(auth_client):
    # GIVEN

    # WHEN
    resp = auth_client.get(url_for('people.read_person_fields'))
    print(resp.json)
    # THEN the api response matches that of the database fields
    person_columns = Person.__table__.columns
    print("SQL:\n")
    print(person_columns)
    # TODO FINISH
    assert True

@pytest.mark.smoke
def test_create_person(auth_client):
    # GIVEN an empty database
    count = random.randint(5, 15)
    # WHEN we create a random number of new people
    for i in range(count):
        resp = auth_client.post(url_for('people.create_person'), json={
                                'person': person_object_factory(), 'attributesInfo': []})
        assert resp.status_code == 201
    # THEN we end up with the proper number of people in the database
    assert auth_client.sqla.query(Person).count() == count

@pytest.mark.smoke
def test_read_all_persons(auth_client):
    # GIVEN a DB with a collection people.
    count = random.randint(3, 11)
    create_multiple_people(auth_client.sqla, count)
    # WHEN the api call is made for read all persons
    resp = auth_client.get(url_for('people.read_all_persons'))
    assert resp.status_code == 200
    # THEN number of all persons returned match that of the DB
    people = auth_client.sqla.query(Person).all()
    assert len(resp.json) == len(people)

@pytest.mark.smoke
def test_read_one_person(auth_client):
    # GIVEN a DB with a collection people.
    count = random.randint(3, 11)
    create_multiple_people(auth_client.sqla, count)

    # WHEN we ask for them all
    people = auth_client.sqla.query(Person).all()
    # THEN we expect the same number
    assert len(people) == count

    # WHEN we request each of them from the server
    for person in people:
        resp = auth_client.get(
            url_for('people.read_one_person', person_id=person.id))
        # THEN we find a matching person
        assert resp.status_code == 200
        assert resp.json['firstName'] == person.first_name
        assert resp.json['lastName'] == person.last_name
        assert resp.json['secondLastName'] == person.second_last_name

@pytest.mark.smoke
def test_update_person(auth_client):
    # GIVEN a random person from collection of people.
    count = random.randint(3, 11)
    create_multiple_people(auth_client.sqla, count)
    randomId = random.randint(1, count)
    the_man = auth_client.sqla.query(Person).get(randomId)

    # WHEN we call api to update a random person's details
    new_first_name = "Really"
    new_last_name  = "Big"
    new_second_last_name = "Chungus"
    update_person_json = {
        "person": {
            "active": 'true',
            'firstName': new_first_name,
            'lastName': new_last_name,
            'secondLastName': new_second_last_name,
            'gender': "M"
        },
        "attributesInfo": []
    }
    resp = auth_client.put(url_for('people.update_person', person_id=randomId), json=update_person_json)
    assert resp.status_code == 200

    # THEN those updates are matched with the database
    the_man = auth_client.sqla.query(Person).get(randomId)
    assert the_man.first_name == new_first_name
    assert the_man.last_name  == new_last_name
    assert the_man.second_last_name == new_second_last_name

@pytest.mark.smoke
def test_deactivate_person(auth_client):
    # GIVEN a random person from collection of people.
    count = random.randint(3, 11)
    create_multiple_people(auth_client.sqla, count)
    randomId = random.randint(1, count)
    the_man = auth_client.sqla.query(Person).get(randomId)

    # WHEN we deactivate that person
    resp = auth_client.put(url_for('people.deactivate_person', person_id=the_man.id))
    assert resp.status_code == 200

    # THEN the person is marked as deactivated
    the_man = auth_client.sqla.query(Person).get(randomId)
    assert the_man.active == False

@pytest.mark.smoke
def test_activate_person(auth_client):
    # GIVEN a random person from a collection of people that is deactivated
    count = random.randint(3, 11)
    create_multiple_people(auth_client.sqla, count)
    randomId = random.randint(1, count)
    the_man = auth_client.sqla.query(Person).get(randomId)
    resp = auth_client.put(url_for('people.deactivate_person', person_id=the_man.id)) # deactivate person
    assert resp.status_code == 200
    # WHEN we activate that person
    resp = auth_client.put(url_for('people.activate_person', person_id=the_man.id)) # then activate person
    assert resp.status_code == 200

    # THEN the person is marked as active
    the_man = auth_client.sqla.query(Person).get(randomId)
    assert the_man.active == True


# ---- Account

def test_create_account(auth_client):
    # GIVEN some randomly created people
    count = random.randint(8, 19)
    create_multiple_people(auth_client.sqla, count)
    create_role(auth_client.sqla)

    # WHEN we retrieve them all
    people = auth_client.sqla.query(Person).all()
    # THEN we get the expected number
    assert len(people) == count

    # WHEN we create accounts for each person
    for person in people:
        account = account_object_factory(person.id)
        resp = auth_client.post(url_for('people.create_account'), json=account)
        # THEN we expect them to be created
        assert resp.status_code == 201
        # AND the account exists in the database
        new_account = auth_client.sqla.query(
            Account).filter_by(person_id=person.id).first()
        assert new_account is not None
        # And the password is properly hashed (refer to docs for generate_password_hash)
        method, salt, hash = new_account.password_hash.split('$')
        key_deriv, hash_func, iters = method.split(':')
        assert key_deriv == 'pbkdf2'
        assert hash_func == 'sha256'
        assert int(iters) >= 50000
        assert len(salt) == 8
        assert len(hash) == 64  # SHA 256 / 4 bits per hex value
    # AND we end up with the proper number of accounts.
    assert auth_client.sqla.query(Account).count() == count


def prep_database(sqla):
    """Prepare the database with a random number of people, some of which have accounts.
    Returns list of IDs of the new accounts.
    """
    create_multiple_people(sqla, random.randint(5, 15))
    create_multiple_accounts(sqla)
    return [account.id for account in sqla.query(Account.id).all()]

def prep_accounts_with_roles(sqla, roles):
    """Prepare the database with a random number of people, all of which have accounts.
    Returns list of IDs of the new accounts.
    """
    create_multiple_people(sqla, random.randint(5, 15))
    create_multiple_accounts(sqla)
    return [account.id for account in sqla.query(Account.id).all()]

@pytest.mark.smoke
def test_read_all_accounts(auth_client):
    # GIVEN a collection of accounts
    prep_database(auth_client.sqla)

    # WHEN we request all accounts with the api
    resp = auth_client.get(url_for('people.read_all_accounts'))
    assert resp.status_code == 200 # Check Response

    # THEN the number of results match the request from the database
    sqlResp = auth_client.sqla.query(Account).all()
    assert len(resp.json) == len(sqlResp)


@pytest.mark.smoke
def test_read_one_account(auth_client):
    # GIVEN a collection of accounts
    prep_database(auth_client.sqla)

    for account in auth_client.sqla.query(Account).all():
        # WHEN we request one
        resp = auth_client.get(
            url_for('people.read_one_account', account_id=account.id))
        # THEN we find the matching account
        assert resp.status_code == 200
        assert resp.json['username'] == account.username
        assert 'password' not in resp.json  # Shouldn't be exposed by API
        assert resp.json['active'] == True

@pytest.mark.smoke
def test_read_one_account_by_username(auth_client):
    # GIVEN an account from the database of accounts
    account_ids = prep_database(auth_client.sqla)
    random_id = account_ids[random.randint(0,len(account_ids)-1)] # Random account id to test
    account = auth_client.sqla.query(Account).get(random_id)
    # WHEN searched for by username
    resp = auth_client.get(url_for('people.read_one_account_by_username', username=account.username))
    assert resp.status_code == 200 # check response
    # THEN the api response matches the database account
    assert account.id == resp.json['id'] # check db id vs api id

    # GIVEN an account name that doesn't exist in the database
    impossible_account_name = "BigChungus&UgandianKnuckles4Lyfe"
    # WHEN the api call is made for the non-existent username
    resp = auth_client.get(url_for('people.read_one_account_by_username', username=impossible_account_name))
    assert resp.status_code == 200  # check response
    # THEN the api should respond with an empty json respnse
    assert resp.json == {}

@pytest.mark.smoke
def test_read_person_account(auth_client):
    # GIVEN an account with a person
    account_ids = prep_database(auth_client.sqla)
    random_id = account_ids[random.randint(0, len(account_ids) - 1)]  # Random account id to test
    account = auth_client.sqla.query(Account).get(random_id)

    # WHEN the api call for reading the person account is made
    resp = auth_client.get(url_for('people.read_person_account', person_id=account.person.id))
    assert resp.status_code == 200  # check response

    # THEN the details match those of the db
    account = auth_client.sqla.query(Account).get(random_id)
    assert resp.json['id']       == account.id
    assert resp.json['username'] == account.username
    assert resp.json["personId"] == account.person.id

def test_get_accounts_by_role(auth_client):
    # GIVEN an account with a role
    role_count = random.randint(8, 19)
    role_ids = create_roles(auth_client.sqla, role_count) # Create x Roles and return their id's
    # TODO Create random number of accounts who have random roles
    account_ids = prep_accounts_with_roles(auth_client.sqla, "roles")
    print("account_ids Created: " + str(account_ids))
    roles = auth_client.sqla.query(Role).all()
    print("Roles Before: "+ str(roles))



    random_id = account_ids[random.randint(0, len(account_ids) - 1)]  # Random account id to test
    roles = auth_client.sqla.query(Role).all()
    print("Roles After Creation: " + str(roles))
    print("First Role : " + str(auth_client.sqla.query(Role).get(3)))

    # WHEN the api call for getting accounts by role is called
    # THEN the results match the database
    # TODO Write
    # TODO Iterate through roles and use api to compare to db
    # TODO Generate new role names with a random number of different roles possibility
    assert False

def test_update_account(auth_client):
    """Test that we can update the password"""
    # Seed the database and fetch the IDs for the new accounts.
    account_ids = prep_database(auth_client.sqla)

    # Create different passwords for each account.
    password_by_id = {}

    # GIVEN a collection of accounts
    for account_id in account_ids:
        # WHEN we update the password via the API
        new_password = password_by_id[account_id] = fake.password()
        resp = auth_client.patch(url_for('people.update_account', account_id=account_id),
                                 json={'password': new_password})
        # THEN the update worked
        assert resp.status_code == 200
        # AND the password was not returned
        assert 'password' not in resp.json

    # GIVEN a collection of accounts
    for account_id in account_ids:
        # WHEN we retrieve account details from the database
        updated_account = auth_client.sqla.query(
            Account).filter_by(id=account_id).first()
        assert updated_account is not None
        # THEN the (account-specific) password is properly hashed
        password_hash = updated_account.password_hash
        assert check_password_hash(password_hash, password_by_id[account_id])

    """Test that we can update fields _other_ than password."""
    account_ids = prep_database(auth_client.sqla)

    # For each of the accounts, grab the current value of the "other" fields.
    expected_by_id = {}
    for account_id in account_ids:
        current_account = auth_client.sqla.query(
            Account).filter_by(id=account_id).first()
        expected_by_id[account_id] = {
            'username': current_account.username,
            'active': current_account.active
        }

    for account_id in account_ids:
        payload = {}

        if flip():
            # Randomly update the username.
            new_username = username_factory()
            expected_by_id[account_id]['username'] = new_username
            payload['username'] = new_username
        if flip():
            # Randomly update the active flag.
            new_active = flip()
            expected_by_id[account_id]['active'] = new_active
            payload['active'] = new_active

        # At this point, we'll have constructed a payload that might have zero of more
        # of the fields. This lets us test various combinations of update requests.
        # The expected_by_id dictionary stores the values we expect to see in the database,
        # whether the original value retrieve earlier or the newly updated on just
        # created.

        # It's possible that none of the fields will have been selected for update,
        # which doesn't make much sense, but we'll still test for that possibility.

        resp = auth_client.patch(
            url_for('people.update_account', account_id=account_id), json=payload)
        assert resp.status_code == 200

    for account_id in account_ids:
        updated_account = auth_client.sqla.query(
            Account).filter_by(id=account_id).first()
        assert updated_account is not None
        assert updated_account.username == expected_by_id[account_id]['username']
        assert updated_account.active == expected_by_id[account_id]['active']


#   -----   __repr__

@pytest.mark.smoke
def test_repr_person(auth_client):
    person = Person()
    person.__repr__()


@pytest.mark.smoke
def test_repr_account(auth_client):
    create_multiple_people(auth_client.sqla, 4)
    create_multiple_accounts(auth_client.sqla, 1)
    account = auth_client.sqla.query(Account).all()
    account[0].__repr__()


@pytest.mark.smoke
def test_repr_role(auth_client):
    role = Role()
    role.__repr__()


#   -----   _init

@pytest.mark.smoke
def test_init_person(auth_client):
    person = Person()
    person._init(auth_client.sqla)


#   -----   Account Passwords
@pytest.mark.smoke
def test_password_account(auth_client):
    account = Account()
    try:
        account.password()
    except:
        assert True


@pytest.mark.smoke
def test_verify_password_account(auth_client):
    create_multiple_people(auth_client.sqla, 4)
    create_multiple_accounts(auth_client.sqla, 1)
    account = auth_client.sqla.query(Account).all()
    account[0].password = "test"
    account[0].verify_password("test")


#   -----   Roles

def role_object_factory(role_name = 'role.test_role'):
    """Cook up a fake role."""
    role = {
        'nameI18n': role_name,
        'active' : 1
    }
    return role

def create_role(sqla):
    """Commit new role to the database. Return ID."""
    role_schema = RoleSchema()

    valid_role_object = role_schema.load(role_object_factory())
    valid_role_row = Role(**valid_role_object)
    sqla.add(valid_role_row)
    sqla.commit()
    return valid_role_row.id

def create_roles(sqla, n):
    """Commit `n` new roles to the database. Return their IDs."""
    role_schema = RoleSchema()
    role_ids = []

    for x in range(0, n):
        role_ids.append(create_role(sqla))

    return role_ids

#
# def test_create_role(auth_client):
#     # GIVEN some randomly created role
#     create_role(auth_client.sqla)
#
#     # WHEN we retrieve them all
#     role = auth_client.sqla.query(Role).all()
#     # THEN we get the expected number
#     assert len(role) == 1

# ---- Manager

def manager_object_factory(sqla, description, next_level = None, locale_code='en-US'):
    """Cook up a fake person."""
    description_i18n = f'manager.description.{description.replace(" ","_")}'

    if not sqla.query(I18NLocale).get(locale_code):
        sqla.add(I18NLocale(code=locale_code, desc='English US'))

    if not sqla.query(I18NKey).get(description_i18n):
        i18n_create(description_i18n, 'en-US',
                    description, description=f"Manager {description}")

    all_account = sqla.query(Account).all()

    manager = {

        'account_id': random.choice(all_accounts).id,
        'description_i18n': description_i18n
    }
    all_managers = sqla.query(Manager).all()

    if next_level is not None:
        next_level_description_i18n = f'manager.description.{next_level.replace(" ","_")}'
        next_level_managers = sqla.query(Manager).filter(Manager.description_i18n==next_level_description_i18n).all()
        if (len(next_level_managers) > 0):
            manager['manager_id'] = random.choice(next_level_managers).id

    return manager


def create_multiple_managers (sqla, n, description, next_level = None):
    """Commit `n` new people to the database. Return their IDs."""
    manager_schema = ManagerSchema()
    new_managers = []
    for i in range(n):
        valid_manager = manager_schema.load(manager_object_factory(sqla, description, next_level))
        new_managers.append(Manager(**valid_manager))
    sqla.add_all(new_managers)
    sqla.commit()


@pytest.mark.smoke
def test_create_manager(auth_client):
    # GIVEN an empty database
    person_count = random.randint(10,20)
    manager_count = random.randint(5, person_count)

    # WHEN we create a random number of new managers and managers in the database
    create_multiple_people(auth_client.sqla, person_count)
    create_multiple_accounts(auth_client.sqla, 1)

    for i in range(manager_count):
        resp = auth_client.post(url_for('people.create_manager'), json=manager_object_factory(auth_client.sqla, 'first level'))
        assert resp.status_code == 201

    # THEN we end up with the proper number of managers in the database
    assert auth_client.sqla.query(Manager).count() == manager_count

@pytest.mark.slow
def test_create_manager_with_manager(auth_client):
    # GIVEN an empty databaseZ
    person_count = random.randint(10,20)
    manager_count = random.randint(5, person_count)

    # WHEN we create a random number of new managers and managers in the database
    create_multiple_people(auth_client.sqla, person_count)
    create_multiple_accounts(auth_client.sqla, 1)
    create_multiple_managers(auth_client.sqla, manager_count, 'second level')

    for i in range(manager_count):
        resp = auth_client.post(url_for('people.create_manager'), json=manager_object_factory(auth_client.sqla, 'first level', next_level='second_level'))
        assert resp.status_code == 201

    # THEN we end up with the proper number of managers in the database
    managers = auth_client.sqla.query(Manager).all()
    level1_count = 0
    level2_count = 0
    for manager in managers:
        if manager.description_i18n == 'manager.description.first_level':
            level1_count = level1_count+1
            assert manager.manager_id is not None
        else:
            level2_count = level2_count+1
            assert manager.manager_id is None

    assert level1_count == manager_count
    assert level2_count == manager_count


@pytest.mark.smoke
def test_create_manager_invalid(auth_client):
    # GIVEN a set of accounts, and people
    count = random.randint(3, 6)
    create_multiple_people(auth_client.sqla, count + 3)
    create_multiple_accounts(auth_client.sqla)

    accounts = auth_client.sqla.query(Account).all()

    # GIVEN managers with bad data for each account
    for account in accounts:
        new_manager = manager_object_factory(auth_client.sqla, fake.sentences(nb=1)[0])
        new_manager[fake.word()] = fake.word()
        
        # WHEN a request is made to make a manager with bad data
        resp = auth_client.post(url_for('people.create_manager'), json = new_manager)

        # THEN expect request to be unprocessable
        assert resp.status_code == 422

    # THEN expect no managers to be created
    assert auth_client.sqla.query(Manager).count() == 0


@pytest.mark.slow
def test_read_all_managers(auth_client):
    # GIVEN a DB with a collection of managers.
    person_count = random.randint(10, 20)
    manager_count = random.randint(5, person_count)
    create_multiple_people(auth_client.sqla, person_count)
    create_multiple_accounts(auth_client.sqla, 1)
    create_multiple_managers(auth_client.sqla, manager_count, 'test manager')
    # WHEN we request all managers from the server
    resp = auth_client.get(url_for('people.read_all_managers', locale='en-US'))
    # THEN the count matches the number of entries in the database
    assert resp.status_code == 200
    assert len(resp.json) == manager_count


@pytest.mark.slow
def test_read_one_manager(auth_client):
    # GIVEN a DB with a collection of managers.
    person_count = random.randint(10, 20)
    manager_count = random.randint(5, person_count)
    create_multiple_people(auth_client.sqla, person_count)
    create_multiple_accounts(auth_client.sqla, 1)
    create_multiple_managers(auth_client.sqla, manager_count, 'test manager')

    # WHEN we ask for them all
    managers = auth_client.sqla.query(Manager).all()

    # THEN we expect the same number
    assert len(managers) == manager_count

    # WHEN we request each of them from the server
    for manager in managers:
        resp = auth_client.get(url_for('people.read_one_manager', manager_id=manager.id, locale='en-US'))
        # THEN we find a matching manager
        assert resp.status_code == 200
        assert resp.json['account_id'] == manager.account_id
        assert resp.json['manager_id'] == manager.manager_id
        assert resp.json['description_i18n'] == manager.description_i18n


@pytest.mark.slow
def test_update_manager(auth_client):
    # GIVEN a DB with a collection of managers.
    person_count = random.randint(10, 20)
    manager_count = random.randint(5, person_count)
    create_multiple_people(auth_client.sqla, person_count)
    create_multiple_accounts(auth_client.sqla, 1)
    create_multiple_managers(auth_client.sqla, manager_count, 'test manager')

    managers = auth_client.sqla.query(Manager).all()
    accounts = auth_client.sqla.query(Account).all()

    update_manager = random.choice(managers)

    new_account_id = update_manager.account_id
    while new_account_id == update_manager.account_id:
        new_account_id = random.choice(accounts).id

    new_manager_id = update_manager.manager_id
    while new_manager_id == update_manager.manager_id or new_manager_id == update_manager.id:
        new_manager_id = random.choice(managers).id

    update_json = {
        'account_id': new_account_id,
        'manager_id': new_manager_id,
        'description_i18n': update_manager.description_i18n
    }

    # WHEN
    resp = auth_client.patch(url_for('people.update_manager', manager_id=update_manager.id), json=update_json)
    # THEN
    assert resp.status_code == 200
    assert resp.json['account_id'] == new_account_id
    assert resp.json['manager_id'] == new_manager_id


def test_delete_manager(auth_client):
    # GIVEN a DB with a collection of managers.
    person_count = random.randint(10, 20)
    manager_count = random.randint(5, person_count)
    create_multiple_people(auth_client.sqla, person_count)
    create_multiple_accounts(auth_client.sqla, 1)
    create_multiple_managers(auth_client.sqla, manager_count, 'test manager')

    managers = auth_client.sqla.query(Manager).all()
    accounts = auth_client.sqla.query(Account).all()

    delete_manager = managers[0]
    subordinate = managers[1]

    update_json = {
        'manager_id': delete_manager.id
    }
    auth_client.patch(url_for('people.update_manager', manager_id=subordinate.id), json=update_json)

    # WHEN we delete the manager
    resp = auth_client.delete(url_for('people.delete_manager', manager_id=delete_manager.id))

    # THEN the manager and all references to that manager are deleted
    assert resp.status_code == 200
    assert auth_client.sqla.query(Manager).filter_by(id=delete_manager.id).first() == None
    assert auth_client.sqla.query(Manager).filter_by(id=subordinate.id).first().manager_id == None


@pytest.mark.smoke
def test_repr_manager(auth_client):
    # GIVEN a DB with a manager
    create_multiple_people(auth_client.sqla, 1)
    create_multiple_accounts(auth_client.sqla, 1)
    create_multiple_managers(auth_client.sqla, 1, 'test manager')
    managers = auth_client.sqla.query(Manager).all()
    managers[0].__repr__()


@pytest.mark.smoke
def test_update_account(auth_client):
    # GIVEN
    # WHEN
    # THEN

    # TODO FINISH
    assert False

@pytest.mark.smoke
def test_deactivate_account(auth_client):
    # GIVEN
    # WHEN
    # THEN

    # TODO FINISH
    assert False

@pytest.mark.smoke
def test_activate_account(auth_client):
    # GIVEN
    # WHEN
    # THEN

    # TODO FINISH
    assert False

# ---- Role

@pytest.mark.smoke
def test_create_role(auth_client):
    # GIVEN
    # WHEN
    # THEN

    # TODO FINISH
    assert False

@pytest.mark.smoke
def test_read_all_roles(auth_client):
    # GIVEN
    # WHEN
    # THEN

    # TODO FINISH
    assert False

@pytest.mark.smoke
def test_get_roles_for_account(auth_client):
    # GIVEN
    # WHEN
    # THEN

    # TODO FINISH
    assert False

@pytest.mark.smoke
def test_read_one_role(auth_client):
    # GIVEN
    # WHEN
    # THEN

    # TODO FINISH
    assert False


@pytest.mark.smoke
def test_replace_role(auth_client):
    # GIVEN
    # WHEN
    # THEN

    # TODO FINISH
    assert False


@pytest.mark.smoke
def test_update_role(auth_client):
    # GIVEN
    # WHEN
    # THEN

    # TODO FINISH
    assert False


@pytest.mark.smoke
def test_delete_role(auth_client):
    # GIVEN
    # WHEN
    # THEN

    # TODO FINISH
    assert False

@pytest.mark.smoke
def test_add_role_to_account(auth_client):
    # GIVEN
    # WHEN
    # THEN

    # TODO FINISH
    assert False

@pytest.mark.smoke
def test_remove_role_from_account(auth_client):
    # GIVEN
    # WHEN
    # THEN

    # TODO FINISH
    assert False


