from django.test import Client, TestCase
from .views import _cart_id, subtract_from_cart, remove_from_cart
from .models import Cart, CartItem
from store.models import Product, Variation
from category.models import Category
from accounts.models import Account
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from django.urls import reverse

# Create your tests here.


class CartModelTest(TestCase):
    def test_cart_creation(self):
        cart = Cart.objects.create(cart_id='test_cart')
        self.assertTrue(isinstance(cart, Cart))
        self.assertEqual(cart.__str__(), 'test_cart')

    def test_cart_item_creation(self):
        user = Account.objects.create(
            username='testuser', email='testuser@gmail.com')
        product = Product.objects.create(product_name='test_product', price=10)
        cart = Cart.objects.create(cart_id='test_cart')
        cart_item = CartItem.objects.create(
            user=user, product=product, cart=cart, quantity=2)
        self.assertTrue(isinstance(cart_item, CartItem))
        self.assertEqual(cart_item.sub_total(), 20)
        self.assertEqual(cart_item.__unicode__(), 'test_product')

    def test_cart_item_with_variations_creation(self):
        user = Account.objects.create(
            username='testuser', email='testuser@gmail.com')
        product = Product.objects.create(product_name='test_product', price=10)
        variation = Variation.objects.create(
            product=product, name='test_variation', price=5)
        cart = Cart.objects.create(cart_id='test_cart')
        cart_item = CartItem.objects.create(
            user=user, product=product, cart=cart, quantity=2)
        cart_item.variations.add(variation)
        self.assertEqual(cart_item.sub_total(), 25)


class TestCartViews(TestCase):
    def setUp(self):
        self.client = Client()
        self.cart_url = reverse('cart')
        self.product1 = Product.objects.create(
            product_name='Product 1',
            price=100,
            slug='product-1',
        )
        self.variation1 = Variation.objects.create(
            product=self.product1,
            variation_category='color',
            variation_value='red'
        )
        self.product2 = Product.objects.create(
            product_name='Product 2',
            price=50,
            slug='product-2',
        )
        self.variation2 = Variation.objects.create(
            product=self.product2,
            variation_category='size',
            variation_value='medium'
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpass123'
        )
        self.cart = Cart.objects.create(
            cart_id='test_cart_id'
        )
        self.cart_item1 = CartItem.objects.create(
            product=self.product1,
            quantity=2,
            cart=self.cart,
            user=self.user
        )
        self.cart_item1.variations.add(self.variation1)
        self.cart_item2 = CartItem.objects.create(
            product=self.product2,
            quantity=1,
            cart=self.cart,
            user=self.user
        )
        self.cart_item2.variations.add(self.variation2)

    def test__cart_id(self):
        request = self.client.get('/')
        middleware = SessionMiddleware()
        middleware.process_request(request)
        request.session.save()
        self.assertEqual(_cart_id(request), request.session.session_key)

    def test_add_to_cart_authenticated_user(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('add_to_cart', args=[self.product1.id]), {
            'color': 'red'
        })
        cart_items = CartItem.objects.filter(
            product=self.product1, user=self.user)
        self.assertEqual(cart_items.count(), 1)
        self.assertEqual(cart_items.first().quantity, 3)
        response = self.client.post(reverse('add_to_cart', args=[self.product2.id]), {
            'size': 'medium'
        })
        cart_items = CartItem.objects.filter(
            product=self.product2, user=self.user)
        self.assertEqual(cart_items.count(), 1)
        self.assertEqual(cart_items.first().quantity, 2)

    def test_add_to_cart_unauthenticated_user(self):
        response = self.client.post(reverse('add_to_cart', args=[self.product1.id]), {
            'color': 'red'
        })
        session = SessionStore(session_key=_cart_id(response.wsgi_request))
        cart_id = session['cart_id']
        cart = Cart.objects.get(cart_id=cart_id)
        cart_items = CartItem.objects.filter(
            product=self.product1, cart=cart)
        self.assertEqual(cart_items.count(), 1)
        self.assertEqual(cart_items.first().quantity, 1)
        response = self.client.post(reverse('add_to_cart', args=[self.product2.id]), {
            'size': 'medium'
        })
        session = SessionStore(session_key=_cart_id(response.wsgi_request))
        cart_id = session['cart_id']
        cart = Cart.objects.get(cart_id=cart_id)
        cart_items = CartItem.objects.filter(
            product=self.product2, cart=cart)

        self.assertEqual(cart_items.count(), 1)
        self.assertEqual(cart_items.first().quantity, 1)


class CartItemTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', email='testuser@gmail.com', password='testpass')
        self.category = Category.objects.create(product_name='Test Category')
        self.product = Product.objects.create(
            product_name='Test Product',
            description='Test description',
            category=self.category,
            price=20,
            image='test_image.jpg'
        )
        self.cart = Cart.objects.create(cart_id='123')
        self.cart_item = CartItem.objects.create(
            product=self.product,
            cart=self.cart,
            user=self.user,
            quantity=2
        )

    def test_subtract_from_cart_authenticated_user(self):
        request = self.factory.post(
            reverse('subtract_from_cart', args=[self.product.id, self.cart_item.id]))
        request.user = self.user
        response = subtract_from_cart(
            request, self.product.id, self.cart_item.id)
        self.assertRedirects(response, reverse('cart'))
        cart_item = CartItem.objects.get(id=self.cart_item.id)
        self.assertEqual(cart_item.quantity, 1)

    def test_subtract_from_cart_unauthenticated_user(self):
        request = self.factory.post(
            reverse('subtract_from_cart', args=[self.product.id, self.cart_item.id]))
        response = subtract_from_cart(
            request, self.product.id, self.cart_item.id)
        self.assertRedirects(response, reverse('cart'))
        cart_item = CartItem.objects.get(id=self.cart_item.id)
        self.assertEqual(cart_item.quantity, 1)

    def test_remove_from_cart_authenticated_user(self):
        request = self.factory.post(reverse('remove_from_cart', args=[
                                    self.product.id, self.cart_item.id]))
        request.user = self.user
        response = remove_from_cart(
            request, self.product.id, self.cart_item.id)
        self.assertRedirects(response, reverse('cart'))
        with self.assertRaises(CartItem.DoesNotExist):
            CartItem.objects.get(id=self.cart_item.id)

    def test_remove_from_cart_unauthenticated_user(self):
        request = self.factory.post(reverse('remove_from_cart', args=[
                                    self.product.id, self.cart_item.id]))
        response = remove_from_cart(
            request, self.product.id, self.cart_item.id)
        self.assertRedirects(response, reverse('cart'))
        with self.assertRaises(CartItem.DoesNotExist):
            CartItem.objects.get(id=self.cart_item.id)


class CartСheckoutTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.product1 = Product.objects.create(
            product_name='Product 1', price=100, stock=10)
        self.product2 = Product.objects.create(
            product_name='Product 2', price=150, stock=15)
        self.user = User.objects.create_user(
            username='testuser', email='testuser@test.com', password='testpass')

    def test_cart_unauthenticated_user(self):
        response = self.client.get(reverse('cart'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/cart.html')
        self.assertEqual(response.context['total'], 0)
        self.assertEqual(response.context['quantity'], 0)
        self.assertEqual(len(response.context['cart_items']), 0)
        self.assertEqual(response.context['tax'], 0)
        self.assertEqual(response.context['grand_total'], 0)

    def test_cart_authenticated_user(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('cart'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/cart.html')
        self.assertEqual(response.context['total'], 0)
        self.assertEqual(response.context['quantity'], 0)
        self.assertEqual(len(response.context['cart_items']), 0)
        self.assertEqual(response.context['tax'], 0)
        self.assertEqual(response.context['grand_total'], 0)

    def test_checkout_unauthenticated_user(self):
        response = self.client.get(reverse('checkout'))
        self.assertRedirects(
            response, '/accounts/login/?next=/checkout/', fetch_redirect_response=False)

    def test_checkout_authenticated_user(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('checkout'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/checkout.html')
        self.assertEqual(response.context['total'], 0)
        self.assertEqual(response.context['quantity'], 0)
        self.assertEqual(len(response.context['cart_items']), 0)
        self.assertEqual(response.context['tax'], 0)
        self.assertEqual(response.context['grand_total'], 0)
