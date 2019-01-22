
import math
import random

import pytest
from faker import Faker
from flask import url_for
from flask_jwt_extended import create_access_token
from werkzeug.datastructures import Headers
from werkzeug.security import check_password_hash

from .. import db

from .models import Location, Address, Area, Country, AreaSchema, LocationSchema, AddressSchema


area_schema = AreaSchema()

@pytest.mark.smoke
@pytest.mark.parametrize('code, name', [('US', 'United States'),
                                        ('EC', 'Ecuador'),
                                        ('TH', 'Thailand')])
def test_read_country(auth_client, code, name):
    count = Country.load_from_file()
    assert count > 0
    resp = auth_client.get(url_for('places.read_countries', country_code=code, locale='en-US'))
    assert resp.status_code == 200
    print("RESP", resp.json)
    assert resp.json['name'] == name


@pytest.mark.slow
def test_read_all_countries(auth_client):
    count = Country.load_from_file()
    assert count > 0
    resp = auth_client.get(url_for('places.read_countries', locale='en-US'))
    assert resp.status_code == 200
    assert len(resp.json) == count


@pytest.mark.smoke
def test_missing_locale(auth_client):
    resp = auth_client.get(url_for('places.read_countries'))
    assert resp.status_code == 400

    resp = auth_client.get(url_for('places.read_countries', country_code='US'))
    assert resp.status_code == 400

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

def area_factory(sqla):
    """Create a fake area."""
    countries = sqla.query(Country).all()
    area = {
        #using last_name for testing purposes, will be area name
        'name': rl_fake().last_name(),
        'country_code': random.choice(countries).code
    }

    return area
    areas = sqla.query(Area).all()

def address_factory(sqla):
    """Create a fake address."""
    fake = Faker()  # Use a generic one; others may not have all methods.
    addresslines = fake.address().splitlines()
    areas = sqla.query(Area).all()
    current_area = random.choice(areas)

    address = {
        'name': fake.name(),
        'address': addresslines[0],
        'city': addresslines[1].split(",")[0],
        'area_id': current_area.id,
        'country_code': current_area.country_code,
        'latitude':random.random() * 0.064116 + -2.933783,
        'longitude': random.random() * 0.09952 + -79.055411
    }
    return address

def location_factory(sqla):
    """Create a fake location"""
    fake = Faker()  # Use a generic one; others may not have all methods.
    addresses = sqla.query(Address).all()
    current_address = random.choice(addresses)

    location = {
        'description': fake.name(),
        'address_id': current_address.id
    }
    return location

def create_multiple_areas(sqla, n):
    """Commit `n` new areas to the database. Return their IDs."""
    area_schema = AreaSchema()
    new_areas = []
    for i in range(n):
        valid_area = area_schema.load(area_factory(sqla))
        new_areas.append(Area(**valid_area))
    sqla.add_all(new_areas)
    sqla.commit()

def create_multiple_addresses(sqla, n):
    """Commit `n` new addresses to the database. Return their IDs."""
    address_schema = AddressSchema()
    new_address = []
    for i in range(n):
        valid_address = address_schema.load(address_factory(sqla))
        new_address.append(Address(**valid_address))
    sqla.add_all(new_address)
    sqla.commit()

def create_multiple_locations(sqla, n):
    """Commit `n` new locations to the database. Return their IDs."""
    location_schema = LocationSchema()
    new_locations = []
    for i in range(n):
        valid_location = location_schema.load(location_factory(sqla))
        new_locations.append(Location(**valid_location))
    sqla.add_all(new_locations)
    sqla.commit()

def prep_database(sqla):
    """Prepare the database with a random number of people, some of which have accounts.
    Returns list of IDs of the new accounts.
    """
    create_multiple_areas(sqla, random.randint(5, 15))
    create_multiple_addresses(sqla, random.randint(5, 15))
    create_multiple_locations(sqla, random.randint(5, 15))
    return [area.id for area in sqla.query(Area.id).all()]


# ---- Area

@pytest.mark.smoke
def test_create_area(auth_client):
    # GIVEN an empty database
    Country.load_from_file()
    count = random.randint(10, 15)
    expected_count = count
    # WHEN we create a random number of new areas
    for i in range(count):
        area = area_factory(auth_client.sqla)
        expected_status_code = 201
        if flip():
            area['name'] = None
            expected_status_code = 422
            expected_count -= 1
        elif flip():
            area['country_code'] = None
            expected_status_code = 422
            expected_count -= 1
    
        resp = auth_client.post(url_for('places.create_area'), json=area)
        assert resp.status_code == expected_status_code
    # THEN we end up with the proper number of areas in the database
    assert auth_client.sqla.query(Area).count() == expected_count

@pytest.mark.smoke
def test_read_area(auth_client):
    # GIVEN an empty DB
    # WHEN we add a collection of areas
    Country.load_from_file()
    count = random.randint(3, 11)
    create_multiple_areas(auth_client.sqla, count)

    # WHEN we ask for them all
    areas = auth_client.sqla.query(Area).all()
    # THEN we expect the same number
    assert db.session.query(Area).count() == count

    # WHEN we request each of them from the server
    for area in areas:
        resp = auth_client.get(url_for('places.read_one_area', area_id=area.id))
        # THEN we find a matching person
        assert resp.status_code == 200
        assert resp.json['name'] == area.name
        assert resp.json['country_code'] == area.country_code

@pytest.mark.smoke
def test_read_all_areas(auth_client):
    # GIVEN an empty DB
    # WHEN we add a collection of areas.
    Country.load_from_file()
    count = random.randint(3, 11)
    create_multiple_areas(auth_client.sqla, count)
    assert count > 0
    
    # WHEN we request all areas from the server
    resp = auth_client.get(url_for('places.read_all_areas', locale='en-US'))
    # THEN the count matches the number of entries in the database
    assert resp.status_code == 200
    assert len(resp.json) == count

@pytest.mark.smoke
def test_replace_area(auth_client):
    # GIVEN an empty DB
    # WHEN we add a collection of areas.
    Country.load_from_file()
    count = random.randint(20, 25)
    create_multiple_areas(auth_client.sqla, count)

    # WHEN we grab one area (and a list of country_codes)
    areas = auth_client.sqla.query(Area).all()
    country_codes = auth_client.sqla.query(Country.code).all()
    for _ in range(count):
        expected_status_code = 200
        area_id = random.choice(areas).id
        area = area_factory(auth_client.sqla)
        # WHEN we modify that area
        if flip():
            area['name'] = fake.last_name()
        elif flip():
            area['country_code']= random.choice(country_codes)[0]
        elif flip():
            area['name'] = None
            if flip():
                area['country_code'] = None
            expected_status_code = 422
        else:
            area_id = -1
            expected_status_code = 404
        # WHEN we make a put request for that area
        resp = auth_client.put(url_for('places.replace_area', area_id = area_id), json = area)
        # THEN we expect the area to be updated and status to match expected status
        assert resp.status_code == expected_status_code
        if expected_status_code == 200:
            assert resp.json['name'] == area['name']
            assert resp.json['country_code'] == area['country_code']

@pytest.mark.smoke
def test_update_area(auth_client):
    # GIVEN an empty DB
    # WHEN we add a collection of areas.
    Country.load_from_file()
    count = random.randint(10, 15)
    create_multiple_areas(auth_client.sqla, count)

    # WHEN we grab one area
    areas = auth_client.sqla.query(Area).all()
    new_area = area_factory(auth_client.sqla)
    for area in areas:
        area_id = area.id
        payload = {}
        expected_status_code = 200
        # WHEN we modify that area
        if flip():
            payload['name'] = new_area['name']
            area.name = new_area['name']
        elif flip():
            payload['country_code'] = new_area['country_code']
            area.country_code = new_area['country_code']
        else:
            if flip():
                area_id = -1
                expected_status_code = 404
            else:
                payload['FAKE NEWS'] = None
                print(payload)
                expected_status_code = 422
            
        # WHEN we use a patch request on each of them
        resp = auth_client.patch(url_for('places.update_area', area_id = area_id), json = payload)
         # THEN we expect the area to be updated and status to match expected status
        assert resp.status_code == expected_status_code
        if expected_status_code == 200:
            print(resp.json)
            assert resp.json['name'] == area.name
            assert resp.json['country_code'] == area.country_code

@pytest.mark.smoke
def test_delete_area(auth_client):
    # GIVEN an empty DB
    # WHEN we add a collection of areas.
    Country.load_from_file()
    count = random.randint(10, 15)
    create_multiple_areas(auth_client.sqla, count)
    # WHEN we grab one area
    areas = auth_client.sqla.query(Area).all()
    for area in areas:
        expected_status_code = 204
        area_id = area.id
        if flip():
            area_id = -1
            expected_status_code = 404
        # WHEN we send a delete request for the area
        resp = auth_client.delete(url_for('places.delete_area', area_id = area_id))
        # THEN we expect a delete status code and the area to be deleted from the DB
        assert resp.status_code == expected_status_code
        if expected_status_code == 204:
            assert 0 == len(auth_client.sqla.query(Area).filter_by(id = area_id).all())
        
# ---- Address

@pytest.mark.smoke
def test_create_address(auth_client):
    # GIVEN an empty database
    Country.load_from_file()
    count = random.randint(5, 15)
    create_multiple_areas(auth_client.sqla, count)
    
    # WHEN we create a random number of new addresses
    for i in range(count):
        resp = auth_client.post(url_for('places.create_address'), json=address_factory(db.session))
        assert resp.status_code == 201
    # THEN we end up with the proper number of addresses in the database
    assert auth_client.sqla.query(Address).count() == count

@pytest.mark.smoke
def test_create_address_invalid(auth_client):
    # GIVEN a set of areas
    Country.load_from_file()
    count = random.randint(5, 15)
    create_multiple_areas(auth_client.sqla, count)
    
    # WHEN a random number of addresses with bad data are requested to be created
    for i in range(count):
        new_address = address_factory(auth_client.sqla)
        new_address[fake.word()] = fake.word()
        resp = auth_client.post(url_for('places.create_address'), json = new_address)
        
        # THEN expect the requests to be unprocessable
        assert resp.status_code == 422

    # THEN expect there to be no addresses created
    assert len(auth_client.sqla.query(Address).all()) == 0

@pytest.mark.smoke
def test_read_address(auth_client):
    # GIVEN a DB with a collection addresses.
    Country.load_from_file()
    count = random.randint(3, 11)
    create_multiple_areas(auth_client.sqla, count)
    create_multiple_addresses(auth_client.sqla, count)

    # WHEN we ask for them all
    addresses = auth_client.sqla.query(Address).all()
    # THEN we exepct the same number
    assert db.session.query(Address).count() == count

    # WHEN we request each of them from the server
    for address in addresses:
        resp = auth_client.get(url_for('places.read_one_address', address_id=address.id))
        # THEN we find a matching address
        assert resp.status_code == 200
        assert resp.json['name'] == address.name
        assert resp.json['address'] == address.address
        assert resp.json['city'] == address.city
        assert resp.json['area_id'] == address.area_id
        assert resp.json['country_code'] == address.country_code
        assert resp.json['latitude'] == address.latitude
        assert resp.json['longitude'] == address.longitude


@pytest.mark.smoke
def test_read_all_addresses(auth_client):
    # GIVEN a DB with a collection of addresses.
    Country.load_from_file()
    count = random.randint(15, 20)
    create_multiple_areas(auth_client.sqla, count)
    create_multiple_addresses(auth_client.sqla, count)

    # WHEN we request all addresses from the server
    resp = auth_client.get(url_for('places.read_all_addresses', locale='en-US'))
    # THEN the count matches the number of entries in the database
    assert resp.status_code == 200
    assert len(resp.json) == count


def query_address_with_params(auth_client, query_dict):
    result = auth_client.sqla.query(Address)
    print(query_dict.keys())
    if 'name' in query_dict.keys():
        result = result.filter_by(name=query_dict['name'])

    if 'address' in query_dict.keys():
        result = result.filter_by(address=query_dict['address'])

    if 'city' in query_dict.keys():
        result = result.filter_by(city=query_dict['city'])

    if 'area_id' in query_dict.keys():
        result = result.filter_by(area_id=query_dict['area_id'])   

    if 'country_code' in query_dict.keys():
        result = result.filter_by(country_code=query_dict['country_code'])

    if 'lat_start' in query_dict.keys():
        result = result.filter(Address.latitude > query_dict['lat_start'])

    if 'lat_end' in query_dict.keys():
        result = result.filter(Address.latitude < query_dict['lat_end'])

    if 'lon_start' in query_dict.keys():
        result = result.filter(Address.longitude > query_dict['lon_start'])

    if 'lon_end' in query_dict.keys():
        result = result.filter(Address.longitude < query_dict['lon_end']) 
    print(result)
    result = result.all()

    return result

@pytest.mark.smoke
def test_read_all_addresses_with_query(auth_client):
    # GIVEN a DB with a collection of addresses.
    Country.load_from_file()
    count = random.randint(15, 20)
    create_multiple_areas(auth_client.sqla, count)
    create_multiple_addresses(auth_client.sqla, count)

    for i in range(count):
        # WHEN queried for all addresses matching a flag
        query_string = dict()
        addresses = auth_client.sqla.query(Address).all()
        address = random.choice(addresses)

        if flip():
            query_string['name'] = address.name

        if flip():
            query_string['address'] = address.address

        if flip():
            query_string['city'] = address.city
        
        if flip():
            query_string['area_id'] = address.area_id
        
        if flip():
            query_string['country_code'] = address.country_code

        if flip():
            query_string['lat_start'] = address.latitude - 1

        if flip():
            query_string['lat_end'] = address.latitude + 1

        if flip():
            query_string['lon_start'] = address.longitude - 1
        
        if flip():
            query_string['lon_end'] = address.longitude + 1

        filtered_results = query_address_with_params(auth_client, query_string)

        # WHEN we request all addresses from the server
        resp = auth_client.get(url_for('places.read_all_addresses'), query_string=query_string)
        # THEN the count matches the number of entries in the database
        assert resp.status_code == 200
        assert len(filtered_results) == len(resp.json)


        # assert len(resp.json) == 1

        # for event in resp.json:
        #     if 'return_group' in query_string:
        #         if query_string['return_group'] == 'inactive':
        #             assert event['active'] == False
        #     else:
        #         assert event['active'] == True

        #     if 'start' in query_string:
        #         assert datetime.datetime.strptime(event['start'][:event['start'].index('T')], '%Y-%m-%d') >= datetime.datetime.strptime(query_string['start'], '%Y-%m-%d')
        #     if 'end' in query_string:
        #         assert datetime.datetime.strptime(event['end'][:event['end'].index('T')], '%Y-%m-%d') <= datetime.datetime.strptime(query_string['end'], '%Y-%m-%d')

        #     if 'title' in query_string:
        #         assert query_string['title'].lower() in event['title'].lower()

        #     if 'location_id' in query_string:
        #         assert event['location_id'] == query_string['location_id']

@pytest.mark.smoke
def test_replace_address(auth_client):
    # GIVEN a set of areas and addresses
    Country.load_from_file()
    count = random.randint(3, 11)
    create_multiple_areas(auth_client.sqla, count)
    create_multiple_addresses(auth_client.sqla, count)

    addresses = auth_client.sqla.query(Address).all()

    # GIVEN replacement addresses
    for address in addresses:
        new_address = address_factory(auth_client.sqla)

        # WHEN replace requests is made with new addresses
        resp = auth_client.put(url_for('places.replace_address', address_id = address.id), json = new_address)

        # THEN expect the requests to run OK
        assert resp.status_code == 200
        
        # THEN expect address to be updated
        if not new_address['name'] == address.name:
            assert not resp.json['name'] == address.name
        else:
            assert resp.json['name'] == address.name
        if not new_address['address'] == address.address:
            assert not resp.json['address'] == address.address
        else:
            assert resp.json['address'] == address.address
        if not new_address['city'] == address.city:
            assert not resp.json['city'] == address.city
        else:
            assert resp.json['city'] == address.city
        if not new_address['area_id'] == address.area_id:
            assert not resp.json['area_id'] == address.area_id
        else:
            assert resp.json['area_id'] == address.area_id
        if not new_address['country_code'] == address.country_code:
            assert not resp.json['country_code'] == address.country_code
        else:
            assert resp.json['country_code'] == address.country_code
        if not new_address['latitude'] == address.latitude:
            assert not resp.json['latitude'] == address.latitude
        else:
            assert resp.json['latitude'] == address.latitude
        if not new_address['longitude'] == address.longitude:
            assert not resp.json['longitude'] == address.longitude
        else:
            assert resp.json['longitude'] == address.longitude


@pytest.mark.smoke
def test_replace_address_invalid(auth_client):
    # GIVEN a set of areas and addresses
    Country.load_from_file()
    count = random.randint(3, 11)
    create_multiple_areas(auth_client.sqla, count)
    create_multiple_addresses(auth_client.sqla, count)

    addresses = auth_client.sqla.query(Address).all()

    # GIVEN replacement addresses with bad data
    for address in addresses:
        new_address = address_factory(auth_client.sqla)
        new_address[fake.word()] = fake.word()

        # WHEN replace requests is made with bad data
        resp = auth_client.put(url_for('places.replace_address', address_id = address.id), json = new_address)

        # THEN expect the requests to be unprocessable
        assert resp.status_code == 422
        

@pytest.mark.smoke
def test_update_address(auth_client):
    # GIVEN a set of areas and addresses
    Country.load_from_file()
    count = random.randint(3, 11)
    create_multiple_areas(auth_client.sqla, count)
    create_multiple_addresses(auth_client.sqla, count)

    addresses = auth_client.sqla.query(Address).all()

    # GIVEN modification data
    for address in addresses:
        new_address = address_factory(auth_client.sqla)
        mod = {}
        flips = (flip(), flip(), flip(), flip(), flip(), flip(), flip())
        if flips[0]:
            mod['name'] = new_address['name']
        if flips[1]:
            mod['address'] = new_address['address']
        if flips[2]:
            mod['city'] = new_address['city']
        if flips[3]:
            mod['area_id'] = new_address['area_id']
        if flips[4]:
            mod['country_code'] = new_address['country_code']
        if flips[5]:
            mod['latitude'] = new_address['latitude']
        if flips[6]:
            mod['longitude'] = new_address['longitude']

        # WHEN an update request is made with the modification data
        resp = auth_client.patch(url_for('places.update_address', address_id = address.id), json = mod)

        # THEN expect the request to run OK
        assert resp.status_code == 200
        
        # THEN expect address to be updated
        if flips[0] and not mod['name'] == address.name:
            assert not resp.json['name'] == address.name
        else:
            assert resp.json['name'] == address.name
        if flips[1] and not mod['address'] == address.address:
            assert not resp.json['address'] == address.address
        else:
            assert resp.json['address'] == address.address
        if flips[2] and not mod['city'] == address.city:
            assert not resp.json['city'] == address.city
        else:
            assert resp.json['city'] == address.city
        if flips[3] and not mod['area_id'] == address.area_id:
            assert not resp.json['area_id'] == address.area_id
        else:
            assert resp.json['area_id'] == address.area_id
        if flips[4] and not mod['country_code'] == address.country_code:
            assert not resp.json['country_code'] == address.country_code
        else:
            assert resp.json['country_code'] == address.country_code
        if flips[5] and not mod['latitude'] == address.latitude:
            assert not resp.json['latitude'] == address.latitude
        else:
            assert resp.json['latitude'] == address.latitude
        if flips[6] and not mod['longitude'] == address.longitude:
            assert not resp.json['longitude'] == address.longitude
        else:
            assert resp.json['longitude'] == address.longitude


@pytest.mark.smoke
def test_update_address_invalid(auth_client):
    # GIVEN a set of areas
    Country.load_from_file()
    count = random.randint(3, 11)
    create_multiple_areas(auth_client.sqla, count)

    # GIVEN modification data with bad data
    new_address = address_factory(auth_client.sqla)
    mod = {}
    flips = (flip(), flip(), flip(), flip(), flip(), flip(), flip())
    if flips[0]:
        mod['name'] = new_address['name']
    if flips[1]:
        mod['address'] = new_address['address']
    if flips[2]:
        mod['city'] = new_address['city']
    if flips[3]:
        mod['area_id'] = new_address['area_id']
    if flips[4]:
        mod['country_code'] = new_address['country_code']
    if flips[5]:
        mod['latitude'] = new_address['latitude']
    if flips[6]:
        mod['longitude'] = new_address['longitude']
    mod[fake.word()] = fake.word()

    # WHEN a request to update an address is made
    resp = auth_client.patch(url_for('places.update_address', address_id = random.randint(1,8)), json = mod)

    # THEN expect request to not be processable
    assert resp.status_code == 422


@pytest.mark.smoke
def test_delete_address(auth_client):
    # GIVEN a set of areas and addresses
    Country.load_from_file()
    count = random.randint(3, 11)
    create_multiple_areas(auth_client.sqla, count)
    create_multiple_addresses(auth_client.sqla, count)

    addresses = auth_client.sqla.query(Address).all()

    # WHEN addresses are deleted at random
    deleted = 0
    for address in addresses:
        if flip():
            resp = auth_client.delete(url_for('places.delete_address', address_id = address.id))
            deleted += 1

            # THEN expect each delete to run OK
            assert resp.status_code == 204

    # THEN expect the correct number of addresses were deleted
    addresses = auth_client.sqla.query(Address).all()
    assert len(addresses) == count - deleted


@pytest.mark.smoke
def test_delete_address_no_exist(auth_client):
    # GIVEN an empty database

    # WHEN an address is requested to be deleted
    resp = auth_client.delete(url_for('places.delete_address', address_id = random.randint(1, 8)))
    
    # THEN expect row not to be found
    assert resp.status_code == 404


# ---- Location

@pytest.mark.smoke
def test_create_location(auth_client):
    # GIVEN an empty database
    Country.load_from_file()
    count = random.randint(5, 15)
    create_multiple_areas(auth_client.sqla, count)
    create_multiple_addresses(auth_client.sqla, count)

    # WHEN we create a random number of new locations
    for i in range(count):
        resp = auth_client.post(url_for('places.create_location'), json=location_factory(db.session))
        assert resp.status_code == 201
    # THEN we end up with the proper number of locations in the database
    assert auth_client.sqla.query(Location).count() == count


@pytest.mark.smoke
def test_create_location_invalid(auth_client):
    # GIVEN a set of areas and addresses
    Country.load_from_file()
    count = random.randint(5, 15)
    create_multiple_areas(auth_client.sqla, count)
    create_multiple_addresses(auth_client.sqla, count)

    # GIVEN new locations with bad data
    for i in range(count):
        new_location = location_factory(auth_client.sqla)
        new_location[fake.word()] = fake.word()
        
        # WHEN locations with bad data are requested to be created
        resp = auth_client.post(url_for('places.create_location'), json = new_location)
        
        # THEN expect requests to be unprocessable
        assert resp.status_code == 422

    # THEN expect no locations to be created
    assert auth_client.sqla.query(Location).count() == 0

@pytest.mark.smoke
def test_create_location_nested(auth_client):
    # GIVEN with some countries
    Country.load_from_file()
    # WHEN we send a request with nested information
    payload = {
            'country_code': 'US',
            'area_name': 'area name',
            'latitude': 0,
            'longitude': 0,
            'city': 'Upland',
            'address': '236 W. Reade Ave.',
            'address_name': 'Taylor University',
            'description': 'Euler 217'
    }
    resp = auth_client.post(url_for('places.create_location'), json = payload)
    # THEN we expect the correct status code
    assert resp.status_code == 201
    # WHEN we expect an area being created
    assert auth_client.sqla.query(Area).count() == 1
    # THEN we expect an address to be created
    assert auth_client.sqla.query(Address).count() == 1
    # THEN we expect a location to be created
    assert auth_client.sqla.query(Location).count() == 1

    # WHEN we send another request with existing area and addresses
    resp = auth_client.post(url_for('places.create_location'), json = payload)
    # THEN we expect the correct status code
    assert resp.status_code == 201
    # WHEN we expect no area being created
    assert auth_client.sqla.query(Area).count() == 1
    # THEN we expect no address to be created
    assert auth_client.sqla.query(Address).count() == 1
    # THEN we expect 2 locations in total in the database
    assert auth_client.sqla.query(Location).count() == 2

    # WHEN we send an incomplete request
    incomplete_payload = {
            'country_code': 'US',
            'latitude': 0,
            'longitude': 0,
            'city': 'Upland',
            'address': '236 W. Reade Ave.',
            'address_name': 'Taylor University',
            'description': 'Euler 217'
    }
    resp = auth_client.post(url_for('places.create_location'), json = incomplete_payload)
    # THEN we expect an error
    assert resp.status_code == 422
    




@pytest.mark.smoke
def test_read_all_locations(auth_client):
    # GIVEN a DB with a collection of addresses.
    Country.load_from_file()
    count = random.randint(3, 11)
    create_multiple_areas(auth_client.sqla, count)
    create_multiple_addresses(auth_client.sqla, count)
    create_multiple_locations(auth_client.sqla, count)
    assert count > 0

    # WHEN we request all addresses from the server
    resp = auth_client.get(url_for('places.read_all_locations', locale='en-US'))
    # THEN the count matches the number of entries in the database
    assert resp.status_code == 200
    assert len(resp.json) == count


@pytest.mark.smoke
def test_read_one_location(auth_client):
    # GIVEN a DB with a collection locations.
    Country.load_from_file()
    count = random.randint(3, 11)
    create_multiple_areas(auth_client.sqla, count)
    create_multiple_addresses(auth_client.sqla, count)
    create_multiple_locations(auth_client.sqla, count)

    # WHEN we ask for them all
    locations = auth_client.sqla.query(Location).all()
    # THEN we exepct the same number
    assert db.session.query(Location).count() == count

    # WHEN we request each of them from the server
    for location in locations:
        resp = auth_client.get(url_for('places.read_one_location', location_id=location.id))
        # THEN we find a matching location
        assert resp.status_code == 200
        assert resp.json['description'] == location.description
        assert resp.json['address_id'] == location.address_id


@pytest.mark.smoke
def test_replace_location(auth_client):
    # GIVEN a set of areas, addresses, and locations
    Country.load_from_file()
    count = random.randint(3, 11)
    create_multiple_areas(auth_client.sqla, count)
    create_multiple_addresses(auth_client.sqla, count)
    create_multiple_locations(auth_client.sqla, count)

    locations = auth_client.sqla.query(Location).all()
    
    # GIVEN replacement locations
    for location in locations:
        new_location = location_factory(auth_client.sqla)

        # WHEN locations are requested to be replaced
        resp = auth_client.put(url_for('places.replace_location', location_id = location.id), json = new_location)

        # THEN expect an OK response
        assert resp.status_code == 200

        # THEN expect locations to be replaced but with consistent ids
        assert resp.json['id'] == location.id

        if not location.description == new_location['description']:
            assert not resp.json['description'] == location.description
        else:
            assert resp.json['description'] == location.description

        if not location.address_id == new_location['address_id']:
            assert not resp.json['address_id'] == location.address_id
        else:
            assert resp.json['address_id'] == location.address_id


@pytest.mark.smoke
def test_replace_location_invalid(auth_client):
    # GIVEN a set of areas, addresses, and locations
    Country.load_from_file()
    count = random.randint(3, 11)
    create_multiple_areas(auth_client.sqla, count)
    create_multiple_addresses(auth_client.sqla, count)
    create_multiple_locations(auth_client.sqla, count)

    locations = auth_client.sqla.query(Location).all()
    
    # Given replacement locations with bad data
    for location in locations:
        new_location = location_factory(auth_client.sqla)
        new_location[fake.word()] = fake.word()

        # WHEN locations are requested to be replaced
        resp = auth_client.put(url_for('places.replace_location', location_id = location.id), json = new_location)

        # THEN expect request to be unprocessable
        assert resp.status_code == 422


@pytest.mark.smoke
def test_delete_location(auth_client):
    # GIVEN a set of areas, addresses, and locations
    Country.load_from_file()
    count = random.randint(8, 11)
    create_multiple_areas(auth_client.sqla, count)
    create_multiple_addresses(auth_client.sqla, count)
    create_multiple_locations(auth_client.sqla, count)

    locations = auth_client.sqla.query(Location).all()
    
    # WHEN a random portion of locations are deleted
    deleted = 0
    for location in locations:
        if flip():
            resp = auth_client.delete(url_for('places.delete_location', location_id = location.id))
            deleted += 1

            # THEN for each delete expect delete to run OK
            assert resp.status_code == 204

    # THEN expect the correct number of locations remaining
    locations = auth_client.sqla.query(Location).all()
    assert len(locations) == count - deleted


@pytest.mark.smoke
def test_delete_location_no_exist(auth_client):
    # GIVEN an empty database
    
    # WHEN a location is requested to be deleted
    resp = auth_client.delete(url_for('places.delete_location', location_id = 1))
    
    # THEN expect row not to be found
    assert resp.status_code == 404


@pytest.mark.smoke
def test_update_location(auth_client):
    # GIVEN a set of areas, addresses, and locations
    Country.load_from_file()
    count = random.randint(3, 11)
    create_multiple_areas(auth_client.sqla, count)
    create_multiple_addresses(auth_client.sqla, count)
    create_multiple_locations(auth_client.sqla, count)

    locations = auth_client.sqla.query(Location).all()
    
    # GIVEN modification data
    for location in locations:
        mod = {}
        flips = (flip(), flip())
        if flips[0]:
            mod['description'] = fake.sentences(nb=1)[0]
        if flips[1]:
            mod['address_id'] = random.randint(1, count + 1)

        # WHEN locations are updated with modification data
        resp = auth_client.patch(url_for('places.update_location', location_id = location.id), json = mod)

        # THEN expect an OK response
        assert resp.status_code == 200

        # THEN expect rows to be updated
        if flips[0] and not location.description == mod['description']:
            assert not resp.json['description'] == location.description
        else:
            assert resp.json['description'] == location.description

        if flips[1] and not location.address_id == mod['address_id']:
            assert not resp.json['address_id'] == location.address_id
        else:
            assert resp.json['address_id'] == location.address_id


@pytest.mark.smoke
def test_update_location_invalid(auth_client):
    # GIVEN a set of areas, addresses, and locations
    Country.load_from_file()
    count = random.randint(3, 11)
    create_multiple_areas(auth_client.sqla, count)
    create_multiple_addresses(auth_client.sqla, count)
    create_multiple_locations(auth_client.sqla, count)

    locations = auth_client.sqla.query(Location).all()
    
    # WHEN locations are updated with bad data
    for location in locations:
        resp = auth_client.patch(url_for('places.update_location', location_id = location.id), json = {fake.word(): fake.word()})

        #THEN expect the request to be unprocessable
        assert resp.status_code == 422


@pytest.mark.smoke
def test_update_location_no_exist(auth_client):
    # GIVEN no data in the database and some modification data
    mod = {}
    flips = (flip(), flip())
    if flips[0]:
        mod['description'] = fake.sentences(nb=1)[0]
    if flips[1]:
       mod['address_id'] = random.randint(1, 8)
        
    # WHEN update_location is called with mod data on a location
    resp = auth_client.patch(url_for('places.update_location', location_id = random.randint(1, 8)), json = mod)
    
    # THEN expect the location not to be found
    assert resp.status_code == 404
