"""Base repository abstractions for ORM-backed data access."""

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Manager, Model, QuerySet


class BaseRepository[ModelT: Model]:
    """Keeps shared ORM access rules in one testable base class."""

    model: type[ModelT]

    def _manager(self) -> Manager[ModelT]:
        return self.model._default_manager

    def all(self) -> QuerySet[ModelT]:
        """Return the base query set for repository-specific filtering."""
        return self._manager().all()

    def get_by_id(self, object_id: object) -> ModelT | None:
        """Return one model instance without leaking DoesNotExist to callers."""
        try:
            return self._manager().get(pk=object_id)
        except ObjectDoesNotExist:
            return None
