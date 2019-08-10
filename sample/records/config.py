# -*- coding: utf-8 -*-
#
# Copyright (C) 2019 CERN.
#
# My site is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Default configuration."""

from __future__ import absolute_import, print_function

from flask_login import current_user
from invenio_jsonschemas import current_jsonschemas
from invenio_records import Record
from invenio_records_rest.facets import terms_filter

from invenio_records_draft.endpoints import draft_enabled_endpoint
from sample.records.marshmallow import MetadataSchemaV1, RecordSchemaV1


def _(x):
    """Identity function for string extraction."""
    return x


def allow_authenticated(*args, **kwargs):
    """Return permission that always allow an access.

    :returns: A object instance with a ``can()`` method.
    """
    return type('Allow', (), {'can': lambda self: current_user.is_authenticated})()


class DraftRecord(Record):
    def validate(self, **kwargs):
        self['$schema'] = current_jsonschemas.path_to_url('draft/records/record-v1.0.0.json')
        return super().validate(**kwargs)


class PublishedRecord(Record):
    def validate(self, **kwargs):
        self['$schema'] = current_jsonschemas.path_to_url('records/record-v1.0.0.json')
        return super().validate(**kwargs)


RECORDS_REST_ENDPOINTS = draft_enabled_endpoint(
    url_prefix='records',
    record_marshmallow=RecordSchemaV1,
    metadata_marshmallow=MetadataSchemaV1,
    search_index='records-record-v1.0.0',
    draft_pid_type='drecid',
    draft_allow_patch=True,
    publish_permission_factory=allow_authenticated,
    unpublish_permission_factory=allow_authenticated,
    edit_permission_factory=allow_authenticated,
    draft_record_class=DraftRecord,
    published_record_class=PublishedRecord,
    published_jsonschema='records/record-v1.0.0.json'
)

"""REST API for my-site."""

RECORDS_UI_ENDPOINTS = {
    'recid': {
        'pid_type': 'recid',
        'route': '/records/<pid_value>',
        'template': 'records/record.html',
    },
}
"""Records UI for my-site."""

SEARCH_UI_JSTEMPLATE_RESULTS = 'templates/records/results.html'
"""Result list template."""

PIDSTORE_RECID_FIELD = 'id'

RECORDS_ENDPOINTS_ENABLED = True
"""Enable/disable automatic endpoint registration."""

RECORDS_REST_FACETS = dict(
    records=dict(
        aggs=dict(
            type=dict(terms=dict(field='type')),
            keywords=dict(terms=dict(field='keywords'))
        ),
        post_filters=dict(
            type=terms_filter('type'),
            keywords=terms_filter('keywords'),
        )
    )
)
"""Introduce searching facets."""

RECORDS_REST_SORT_OPTIONS = dict(
    records=dict(
        bestmatch=dict(
            title=_('Best match'),
            fields=['_score'],
            default_order='desc',
            order=1,
        ),
        mostrecent=dict(
            title=_('Most recent'),
            fields=['-_created'],
            default_order='asc',
            order=2,
        ),
    )
)
"""Setup sorting options."""

RECORDS_REST_DEFAULT_SORT = dict(
    records=dict(
        query='bestmatch',
        noquery='mostrecent',
    )
)
"""Set default sorting options."""

INVENIO_RECORD_DRAFT_SCHEMAS = [
    'records/record-v1.0.0.json'
]
