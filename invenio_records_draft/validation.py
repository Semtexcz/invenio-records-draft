import copy

from invenio_pidstore.models import PersistentIdentifier
from invenio_records_rest.loaders.marshmallow import MarshmallowErrors
from jsonschema import ValidationError


def validate(record, marshmallow_schema_class, published_record_class):

    if record:
            as_published = copy.deepcopy(dict(record))
            as_published.pop('$schema')
            if published_jsonschema:
                as_published['$schema'] = published_jsonschema
            pid = PersistentIdentifier.get_by_object(
                pid_type=draft_pid_type,
                object_type='rec', object_uuid=record.model.id)
            as_published = published_record_validator(as_published, pid)
            rec = published_record_class(as_published)
            rec.validate()
