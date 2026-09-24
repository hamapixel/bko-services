from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient

from .models import City, Commune, Neighborhood, Region


class LocationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.bamako = City.objects.get(name="Bamako")
        self.commune = Commune.objects.create(city=self.bamako, name="Commune exemple")
        self.neighborhood = Neighborhood.objects.create(commune=self.commune, name="Quartier exemple")

    def test_public_lists_are_read_only_and_filtered_by_parent(self):
        other_region = Region.objects.create(name="Région exemple")
        other_city = City.objects.create(name="Ville exemple", region=other_region)
        other_commune = Commune.objects.create(city=other_city, name="Commune exemple")
        other_neighborhood = Neighborhood.objects.create(commune=other_commune, name="Quartier exemple")

        cities = self.client.get("/api/v1/locations/cities/")
        self.assertEqual(cities.status_code, 200)
        self.assertEqual(cities.json()["count"], 2)
        regions = self.client.get("/api/v1/locations/regions/")
        self.assertEqual(regions.json()["count"], 2)
        self.assertEqual(
            self.client.get(f"/api/v1/locations/cities/?region={self.bamako.region_id}").json()["count"], 1
        )

        communes = self.client.get(f"/api/v1/locations/communes/?city={self.bamako.pk}")
        self.assertIn(str(self.commune.pk), [row["id"] for row in communes.json()["results"]])
        neighborhoods = self.client.get(f"/api/v1/locations/neighborhoods/?commune={self.commune.pk}")
        self.assertEqual([row["id"] for row in neighborhoods.json()["results"]], [str(self.neighborhood.pk)])
        self.assertNotIn(str(other_neighborhood.pk), str(neighborhoods.json()))
        self.assertEqual(self.client.get("/api/v1/locations/communes/?city=bad").status_code, 400)
        self.assertEqual(self.client.get("/api/v1/locations/cities/?region=bad").status_code, 400)
        self.assertEqual(self.client.post("/api/v1/locations/cities/", {"name": "Fake"}).status_code, 405)

    def test_disabling_parent_hides_descendants(self):
        self.neighborhood.is_active = False
        self.neighborhood.save(update_fields=["is_active"])
        self.assertEqual(self.client.get(f"/api/v1/locations/neighborhoods/?commune={self.commune.pk}").json()["count"], 0)
        self.neighborhood.is_active = True
        self.neighborhood.save(update_fields=["is_active"])
        self.commune.is_active = False
        self.commune.save(update_fields=["is_active"])
        self.assertNotIn(str(self.commune.pk), str(self.client.get("/api/v1/locations/communes/").json()))
        self.assertEqual(self.client.get(f"/api/v1/locations/neighborhoods/?commune={self.commune.pk}").json()["count"], 0)
        self.bamako.is_active = False
        self.bamako.save(update_fields=["is_active"])
        self.assertEqual(self.client.get("/api/v1/locations/cities/").json()["count"], 0)
        self.bamako.is_active = True
        self.bamako.save(update_fields=["is_active"])
        self.bamako.region.is_active = False
        self.bamako.region.save(update_fields=["is_active"])
        self.assertEqual(self.client.get("/api/v1/locations/cities/").json()["count"], 0)
        self.assertEqual(self.client.get("/api/v1/locations/neighborhoods/").json()["count"], 0)

    def test_duplicate_names_are_rejected_within_same_parent(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            City.objects.create(name="bamako")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Commune.objects.create(city=self.bamako, name="commune EXEMPLE")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Neighborhood.objects.create(commune=self.commune, name="QUARTIER EXEMPLE")
