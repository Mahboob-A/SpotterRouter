"""Base repository abstractions for ORM-backed data access."""

from typing import Generic, TypeVar

from django.db.models import Model, QuerySet

ModelT = TypeVar("ModelT", bound=Model)


class BaseRepository(Generic[ModelT]):
    """Keeps shared ORM access rules in one testable base class."""

    model: type[ModelT]

    def all(self) -> QuerySet[ModelT]:
        """Return the base query set for repository-specific filtering."""
        return self.model.objects.all()

    def get_by_id(self, object_id: object) -> ModelT | None:
        """Return one model instance without leaking DoesNotExist to callers."""
        try:
            return self.model.objects.get(pk=object_id)
        except self.model.DoesNotExist:
            return None
