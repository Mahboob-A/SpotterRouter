from django.db.models import QuerySet

from core.repositories import BaseRepository
from stations.models import Station


class StationRepository(BaseRepository[Station]):
    model = Station

    def get_by_opis_id(self, opis_id: str) -> Station | None:
        return self.model.objects.filter(opis_id=opis_id).first()

    def needing_geocoding(self) -> QuerySet[Station]:
        return self.model.objects.filter(location__isnull=True).order_by("opis_id")
