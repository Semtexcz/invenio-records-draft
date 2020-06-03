from pprint import pprint

from marshmallow import Schema, fields, ValidationError
from marshmallow.validate import Length

from invenio_records_draft.utils import parse_marshmallow_messages


class UserSchema(Schema):
    name = fields.Str(validate=Length(min=3))
    email = fields.Email()
    children = fields.List(fields.Nested(lambda: UserSchema(exclude=("children",))))


def test_parse_marshmallow_messages_1():
    result = {}
    user = {
        "name": "James Lee",
        "email": "blah"
    }
    schema = UserSchema()
    try:
        schema.load(user)
    except ValidationError as e:
        result = parse_marshmallow_messages(e.messages)
    assert result == [{'field': 'email', 'message': 'Not a valid email address.'}]


def test_parse_marshmallow_messages_2():
    result = {}
    user = {
        "name": "JL",
        "email": "blah"
    }
    schema = UserSchema()
    try:
        schema.load(user)
    except ValidationError as e:
        result = parse_marshmallow_messages(e.messages)
    expected = [{'field': 'name', 'message': 'Shorter than minimum length 3.'},
                {'field': 'email', 'message': 'Not a valid email address.'}]
    for res in result:
        assert res in expected


def test_parse_marshmallow_messages_3():
    result = {}
    user = {
        "name": "James Lee",
        "email": "JL@example.com",
        "children": [{
            "name": "Thomas Lee",
            "email": "bla"
        }]
    }
    schema = UserSchema()
    try:
        schema.load(user)
    except ValidationError as e:
        result = parse_marshmallow_messages(e.messages)
    pprint(result)
    assert result == [{'field': 'children/0/email', 'message': 'Not a valid email address.'}]


def test_parse_marshmallow_messages_4():
    result = {}
    user = {
        "name": "JL",
        "email": "JL@example.com",
        "children": [
            {
                "name": "TL",
                "email": "bla"
            },
            {
                "name": "BL",
                "email": "bla"
            }
        ]
    }
    schema = UserSchema()
    try:
        schema.load(user)
    except ValidationError as e:
        result = parse_marshmallow_messages(e.messages)
    pprint(result)
    expected = [
        {'field': 'children/0/name', 'message': 'Shorter than minimum length 3.'},
        {'field': 'children/0/email', 'message': 'Not a valid email address.'},
        {'field': 'children/1/name', 'message': 'Shorter than minimum length 3.'},
        {'field': 'children/1/email', 'message': 'Not a valid email address.'},
        {'field': 'name', 'message': 'Shorter than minimum length 3.'}
    ]
    for res in result:
        assert res in expected
