from django.test import TestCase, Client
from .models import Product, Variation, ReviewRating, ProductGallery
from accounts.models import Account
from category.models import Category
from carts.models import Cart, CartItem
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

# Create your tests here.


class ProductModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            category_name='test_category', slug='test_category')
        self.product = Product.objects.create(
            product_name='Test Product',
            slug='test-product',
            description='Test description',
            price=100,
            stock=10,
            category=self.category
        )

    def test_product_model(self):
        self.assertEqual(str(self.product), 'Test Product')
        self.assertEqual(self.product.get_url(),
                         '/test_category/test-product')
        self.assertEqual(self.product.averageReview(), 0)
        self.assertEqual(self.product.countReview(), 0)


class VariationModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            category_name='test_category', slug='test_category')
        self.product = Product.objects.create(
            product_name='Test Product',
            slug='test-product',
            description='Test description',
            price=100,
            stock=10,
            category=self.category
        )
        self.variation = Variation.objects.create(
            product=self.product,
            variation_category='color',
            variation_value='red',
            is_active=True
        )

    def test_variation_model(self):
        self.assertEqual(str(self.variation), 'red')
        self.assertEqual(Variation.objects.colors().count(), 1)
        self.assertEqual(Variation.objects.sizes().count(), 0)


class ReviewRatingModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            category_name='test_category', slug='test_category')
        self.product = Product.objects.create(
            product_name='Test Product',
            slug='test-product',
            description='Test description',
            price=100,
            stock=10,
            category=self.category
        )
        self.user = Account.objects.create(
            email='testuser@test.com', username='testuser')
        self.review_rating = ReviewRating.objects.create(
            product=self.product,
            user=self.user,
            subject='Test Subject',
            review='Test review',
            rating=4,
            ip='127.0.0.1',
            status=True
        )

    def test_review_rating_model(self):
        self.assertEqual(str(self.review_rating), 'Test Subject')


class ProductGalleryModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            category_name='test_category', slug='test_category')
        self.product = Product.objects.create(
            product_name='Test Product',
            slug='test-product',
            description='Test description',
            price=100,
            stock=10,
            category=self.category
        )
        self.product_gallery = ProductGallery.objects.create(
            product=self.product,
            image='test_image.jpg'
        )

    def test_product_gallery_model(self):
        self.assertEqual(str(self.product_gallery), 'Test Product')


class StoreViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(
            category_name='Test category', slug='test-category')
        self.product = Product.objects.create(
            product_name='Test product',
            slug='test-product',
            price=100,
            description='This is a test product',
            category=self.category,
            images=SimpleUploadedFile("test_image.jpg", b"test_image_content")
        )
        self.review = ReviewRating.objects.create(
            user=self.user,
            product=self.product,
            rating=5,
            review='Test review'
        )
        self.gallery = ProductGallery.objects.create(
            product=self.product,
            image=SimpleUploadedFile("test_image.jpg", b"test_image_content")
        )

    def test_store_view_with_category(self):
        response = self.client.get(reverse('store', args=['test-category']))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/store.html')
        self.assertContains(response, self.product.product_name)

    def test_store_view_without_category(self):
        response = self.client.get(reverse('store'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/store.html')
        self.assertContains(response, self.product.product_name)

    def test_product_detail_view(self):
        response = self.client.get(reverse('product_detail', args=[
                                   'test-category', 'test-product']))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/product_detail.html')
        self.assertContains(response, self.product.product_name)
        self.assertContains(response, self.review.review)
        self.assertContains(response, self.gallery.image.url)


class ProductDetailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(category_name='Test category')
        self.product = Product.objects.create(
            product_name='Test product',
            category=self.category,
            price=10,
            stock=1,
            description='Test product description',
        )
        self.product_detail_url = reverse(
            'product_detail', args=[self.category.slug, self.product.slug])

    def test_product_detail_view(self):
        response = self.client.get(self.product_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/product_detail.html')
        self.assertContains(response, 'Test product')
        self.assertContains(response, 'Test category')
        self.assertContains(response, 'Test product description')
        self.assertContains(response, 10)

    def test_product_detail_view_with_cart(self):
        cart = Cart.objects.create(cart_id='test')
        cart_item = CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=1,
        )
        response = self.client.get(self.product_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/product_detail.html')
        self.assertContains(response, 'Test product')
        self.assertContains(response, 'Test category')
        self.assertContains(response, 'Test product description')
        self.assertContains(response, 10)
        self.assertContains(response, 'In Cart')
