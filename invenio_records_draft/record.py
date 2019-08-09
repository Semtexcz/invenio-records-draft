import logging
import uuid

from invenio_db import db
from invenio_pidstore.errors import PIDDoesNotExistError
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_records_rest.loaders.marshmallow import MarshmallowErrors

logger = logging.getLogger('invenio-records-draft')


class DraftEnabledRecordMixin:

    def publish(self, draft_pid,
                published_record_class, published_pid_type,
                published_record_validator,
                remove_draft=True):

        return self.publish_record(
            self, draft_pid, published_record_class, published_pid_type,
            published_record_validator, remove_draft)

    def draft(self, published_pid, draft_record_class, draft_pid_type):
        return self.draft_record(self, published_pid, draft_record_class, draft_pid_type)

    def unpublish(self, published_pid, draft_record_class, draft_pid_type):
        return self.unpublish_record(self, published_pid, draft_record_class, draft_pid_type)

    @staticmethod
    def publish_record(draft_record, draft_pid,
                       published_record_class, published_pid_type,
                       published_record_validator, remove_draft):

        published_record, draft_record = DraftEnabledRecordMixin._publish_draft(
            draft_record, draft_pid, published_record_class, published_pid_type,
            published_record_validator)

        if remove_draft:
            # delete the record
            draft_record.delete()

            # mark all object pids as deleted
            all_pids = PersistentIdentifier.query.filter(
                PersistentIdentifier.object_type == draft_pid.object_type,
                PersistentIdentifier.object_uuid == draft_pid.object_uuid,
            ).all()
            for rec_pid in all_pids:
                if not rec_pid.is_deleted():
                    rec_pid.delete()

        return published_record, draft_record

    @staticmethod
    def _publish_draft(draft_record, draft_pid,
                       published_record_class, published_pid_type,
                       published_record_validator):

        # clone metadata
        metadata = dict(draft_record)
        published_record_validator(metadata)

        # note: the passed record must fill in the schema otherwise the published record will be
        # without any schema and will not get indexed
        metadata.pop('$schema', None)

        try:
            published_pid = PersistentIdentifier.get(published_pid_type, draft_pid.pid_value)

            if published_pid.status == PIDStatus.DELETED:
                # the draft is deleted, resurrect it
                # change the pid to registered
                published_pid.status = PIDStatus.REGISTERED
                db.session.add(published_pid)

                # and fetch the draft record and update its metadata
                return DraftEnabledRecordMixin._update_published_record(
                    draft_record, published_pid, metadata, None, published_record_class)

            elif published_pid.status == PIDStatus.REGISTERED:
                # fetch the draft record and update its metadata
                # if it is older than the published one
                return DraftEnabledRecordMixin._update_published_record(
                    draft_record, published_pid, metadata,
                    draft_record.updated, published_record_class)

            raise NotImplementedError('Can not unpublish record to draft record '
                                      'with pid status %s. Only registered or deleted '
                                      'statuses are implemented', published_pid.status)
        except PIDDoesNotExistError:
            pass

        # create a new draft record. Do not call minter as the pid value will be the
        # same as the pid value of the published record
        id = uuid.uuid4()
        published_record = published_record_class.create(metadata, id_=id)
        PersistentIdentifier.create(pid_type=published_pid_type,
                                    pid_value=draft_pid.pid_value, status=PIDStatus.REGISTERED,
                                    object_type='rec', object_uuid=id)
        return published_record, draft_record

    @staticmethod
    def _update_published_record(draft_record, published_pid, metadata,
                                 timestamp, published_record_class):
        published_record = published_record_class.get_record(published_pid.object_uuid,
                                                             with_deleted=True)
        # if deleted, revert to last non-deleted revision
        revision_id = published_record.revision_id
        while published_record.model.json is None and revision_id > 0:
            revision_id -= 1
            published_record.revert(revision_id)

        if not timestamp or published_record.updated < timestamp:
            published_record.update(metadata)
            published_record.commit()
            if not published_record['$schema']:  # pragma no cover
                logger.warning('Updated draft record does not have a $schema metadata. '
                               'Please use a Record implementation that adds $schema '
                               '(for example in validate() method). Draft PID Type %s',
                               published_pid.pid_type)

        return published_record, draft_record

    @staticmethod
    def draft_record(published_record, published_pid,
                     draft_record_class, draft_pid_type):
        metadata = dict(published_record)
        # note: the passed record must fill in the schema otherwise the draft will be
        # without any schema and will not get indexed
        metadata.pop('$schema', None)

        try:
            draft_pid = PersistentIdentifier.get(draft_pid_type, published_pid.pid_value)
            if draft_pid.status == PIDStatus.DELETED:
                # the draft is deleted, resurrect it
                # change the pid to registered
                draft_pid.status = PIDStatus.REGISTERED
                db.session.add(draft_pid)

                # and fetch the draft record and update its metadata
                return DraftEnabledRecordMixin._update_draft_record(
                    published_record, draft_pid, metadata, None, draft_record_class)

            elif draft_pid.status == PIDStatus.REGISTERED:
                # fetch the draft record and update its metadata
                # if it is older than the published one
                return DraftEnabledRecordMixin._update_draft_record(
                    published_record, draft_pid, metadata,
                    published_record.updated, draft_record_class)

            raise NotImplementedError('Can not unpublish record to draft record '
                                      'with pid status %s. Only registered or deleted '
                                      'statuses are implemented', draft_pid.status)
        except PIDDoesNotExistError:
            pass

        # create a new draft record. Do not call minter as the pid value will be the
        # same as the pid value of the published record
        id = uuid.uuid4()
        draft_record = draft_record_class.create(metadata, id_=id)
        PersistentIdentifier.create(pid_type=draft_pid_type,
                                    pid_value=published_pid.pid_value, status=PIDStatus.REGISTERED,
                                    object_type='rec', object_uuid=id)
        return published_record, draft_record

    @staticmethod
    def _update_draft_record(record, draft_pid, metadata, timestamp, draft_record_class):
        draft_record = draft_record_class.get_record(draft_pid.object_uuid,
                                                     with_deleted=True)

        # if deleted, revert to last non-deleted revision
        revision_id = draft_record.revision_id
        while draft_record.model.json is None and revision_id > 0:
            revision_id -= 1
            draft_record.revert(revision_id)

        if not timestamp or draft_record.updated < timestamp:
            draft_record.update(metadata)
            draft_record.commit()
            if not draft_record['$schema']:  # pragma no cover
                logger.warning('Updated draft record does not have a $schema metadata. '
                               'Please use a Record implementation that adds $schema '
                               '(for example in validate() method). Draft PID Type %s',
                               draft_pid.pid_type)

        return record, draft_record

    @staticmethod
    def unpublish_record(published_record, published_pid,
                         draft_record_class, draft_pid_type):
        published_record, draft_record = \
            DraftEnabledRecordMixin.draft_record(published_record, published_pid,
                                                 draft_record_class, draft_pid_type)

        # delete the record
        published_record.delete()

        # mark all object pids as deleted
        all_pids = PersistentIdentifier.query.filter(
            PersistentIdentifier.object_type == published_pid.object_type,
            PersistentIdentifier.object_uuid == published_pid.object_uuid,
        ).all()
        for rec_pid in all_pids:
            if not rec_pid.is_deleted():
                rec_pid.delete()

        return published_record, draft_record

    @staticmethod
    def marshmallow_validator(marshmallow_schema_class):
        def validate(record):
            context = {}

            result = marshmallow_schema_class(context=context).load(dict(record))

            if result.errors:
                raise MarshmallowErrors(result.errors)
            return result.data

        return validate