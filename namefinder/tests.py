from django.test import TestCase, override_settings
from django.test import RequestFactory

from .forms import DeterminativeForm, InstanceInlineForm
from .models import Determinative, DeterminativeVariant, Fragment, Instance, Name, Series
from .views import index


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class DeterminativeNormalizationTests(TestCase):
    def test_form_normalizes_parent_determinative(self):
        form = DeterminativeForm(data={"name": "°[UR]U°", "is_active": True})
        self.assertTrue(form.is_valid())
        det = form.save()
        self.assertEqual(det.name, "URU")

    def test_instance_display_uses_variant_without_degree_marks(self):
        det = Determinative.objects.create(name="URU")
        variant = DeterminativeVariant.objects.create(
            determinative=det,
            value="°[UR]U°",
        )
        instance = Instance.objects.create(determinative_variant=variant)
        self.assertEqual(instance.display_determinative, "[UR]U")
        self.assertEqual(instance.determinative, det)

    def test_inline_form_resolves_variant_under_parent(self):
        det = Determinative.objects.create(name="URU")
        series = Series.objects.create(name="KUB")
        fragment = Fragment.objects.create(
            series=series,
            fragment_number="1.1",
            series_fragment="KUB 1.1",
        )
        form = InstanceInlineForm(data={
            "fragment": fragment.id,
            "line": "obv. 1",
            "spelling": "test",
            "determinative": det.id,
            "determinative_variant_value": "°[UR]U°",
        })
        self.assertTrue(form.is_valid(), form.errors)
        instance = form.save()
        self.assertEqual(instance.determinative.name, "URU")
        self.assertEqual(instance.display_determinative, "[UR]U")

    def test_name_search_filters_by_attested_determinative(self):
        det = Determinative.objects.create(name="URU")
        variant = DeterminativeVariant.objects.create(
            determinative=det,
            value="[UR]U",
        )
        other_det = Determinative.objects.create(name="KUR")
        other_variant = DeterminativeVariant.objects.create(
            determinative=other_det,
            value="KUR",
        )
        series = Series.objects.create(name="KBo")
        fragment = Fragment.objects.create(
            series=series,
            fragment_number="1.1",
            series_fragment="KBo 1.1",
        )
        matching_name = Name.objects.create(name="Lalla", query="lalla")
        other_name = Name.objects.create(name="Katapa", query="katapa")
        Instance.objects.create(name=matching_name, fragment=fragment, determinative_variant=variant)
        Instance.objects.create(name=other_name, fragment=fragment, determinative_variant=other_variant)

        request = RequestFactory().get("/", {"determinative": det.id})
        response = index(request)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("Lalla", content)
        self.assertNotIn("Katapa", content)
