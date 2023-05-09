from django.test import TestCase
from store.models import Category
from django.urls import reverse

# Create your tests here.


class CategoryModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            category_name='Test Category',
            slug='test-category',
            description='This is a test category',
        )

    def test_category_model(self):
        category = self.category
        self.assertEqual(str(category), category.category_name)
        self.assertEqual(category.get_url(), reverse(
            'products_by_category', args=[category.slug]))
        self.assertTrue(isinstance(category, Category))
