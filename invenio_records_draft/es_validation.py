import copy
import functools

from invenio_indexer.signals import before_record_index
from invenio_pidstore.models import PersistentIdentifier
from invenio_records_rest.loaders.marshmallow import MarshmallowErrors
from jsonschema import ValidationError


def register_elasticsearch_signals(draft_index, published_record_validator,
                                   published_jsonschema,
                                   published_record_class, draft_pid_type):
    def handler(sender, json=None, record=None, index=None, **kwargs):
        app = sender

        if index != app.config.get('SEARCH_INDEX_PREFIX', '') + draft_index:
            return

        if record:
            try:
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
            except MarshmallowErrors as e:
                json['invenio_draft_validation'] = {
                    'valid': False,
                    'errors': {
                        'marshmallow': e.errors
                    }
                }
            except ValidationError as e:
                json['invenio_draft_validation'] = {
                    'valid': False,
                    'errors': {
                        'jsonschema': [
                            {
                                'field': '.'.join(e.path),
                                'message': e.message
                            }
                        ]
                    }
                }
            except Exception as e:
                json['invenio_draft_validation'] = {
                    'valid': False,
                    'errors': {
                        'other': str(e)
                    }
                }
            else:
                json['invenio_draft_validation'] = {
                    'valid': True
                }

    if hasattr(before_record_index, 'dynamic_connect'):
        connect = functools.partial(before_record_index.dynamic_connect, index=draft_index)
    else:
        connect = before_record_index.connect

    connect(handler, weak=False)
