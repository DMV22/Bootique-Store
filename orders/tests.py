from django.test import TestCase, Client
from .models import Payment, Order, OrderProduct
from store.models import Product
from carts.models import CartItem
from accounts.models import Account
from django.urls import reverse

# Create your tests here.


class PaymentModelTest(TestCase):
    def setUp(self):
        self.user = Account.objects.create(
            username='test_user', email='test@test.com', password='testpass123')
        self.payment = Payment.objects.create(
            user=self.user,
            payment_id='payment_123',
            payment_method='Stripe',
            amount_paid=100,
            status='Paid',
        )

    def test_payment_creation(self):
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(self.payment.payment_id, 'payment_123')
        self.assertEqual(self.payment.payment_method, 'Stripe')
        self.assertEqual(self.payment.amount_paid, 100)
        self.assertEqual(self.payment.status, 'Paid')


class OrderModelTest(TestCase):
    def setUp(self):
        self.user = Account.objects.create(
            username='test_user', email='test@test.com', password='testpass123')
        self.payment = Payment.objects.create(
            user=self.user,
            payment_id='payment_123',
            payment_method='Stripe',
            amount_paid=100,
            status='Paid',
        )
        self.order = Order.objects.create(
            user=self.user,
            payment=self.payment,
            order_number='order_123',
            first_name='John',
            last_name='Doe',
            phone='1234567890',
            email='johndoe@test.com',
            address_line_1='123 Main St',
            address_line_2='Apt 2B',
            country='US',
            state='NY',
            city='New York',
            order_note='Some notes',
            order_total=100,
            tax=10,
            status='New',
            ip='127.0.0.1',
            is_ordered=False,
        )

    def test_order_creation(self):
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(self.order.user, self.user)
        self.assertEqual(self.order.payment, self.payment)
        self.assertEqual(self.order.order_number, 'order_123')
        self.assertEqual(self.order.first_name, 'John')
        self.assertEqual(self.order.last_name, 'Doe')
        self.assertEqual(self.order.phone, '1234567890')
        self.assertEqual(self.order.email, 'johndoe@test.com')
        self.assertEqual(self.order.address_line_1, '123 Main St')
        self.assertEqual(self.order.address_line_2, 'Apt 2B')
        self.assertEqual(self.order.country, 'US')
        self.assertEqual(self.order.state, 'NY')
        self.assertEqual(self.order.city, 'New York')
        self.assertEqual(self.order.order_note, 'Some notes')
        self.assertEqual(self.order.order_total, 100)
        self.assertEqual(self.order.tax, 10)
        self.assertEqual(self.order.status, 'New')
        self.assertEqual(self.order.ip, '127.0.0.1')
        self.assertEqual(self.order.is_ordered, False)


class PaymentTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = Account.objects.create_user(
            first_name='John',
            last_name='Doe',
            email='johndoe@example.com',
            username='johndoe',
            password='password')
        self.product = Product.objects.create(
            product_name='Test Product', price=10, stock=10)
        self.cart_item = CartItem.objects.create(
            user=self.user, product=self.product, quantity=2)
        self.order = Order.objects.create(
            user=self.user, full_name='Test User', address='Test Address',
            phone='123456789', city='Test City', order_total=21.98,
            email='testuser@example.com', status='New', is_ordered=False,
            order_number='20220001')
        self.payment_data = {
            'transID': '123456789',
            'payment_method': 'Paypal',
            'status': 'Success',
            'orderID': '20220001'
        }

    def test_payment_process(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('payments'), data=self.payment_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('order_number'), '20220001')
        self.assertEqual(response.json().get('transID'), '123456789')
        payment = Payment.objects.get(payment_id='123456789')
        self.assertEqual(payment.payment_method, 'Paypal')
        self.assertEqual(payment.amount_paid, 21.98)
        self.assertEqual(payment.status, 'Success')
        self.assertTrue(payment.user, self.user)
        self.assertTrue(payment.order, self.order)
        order_products = OrderProduct.objects.filter(order_id=self.order.id)
        self.assertEqual(len(order_products), 1)
        order_product = order_products.first()
        self.assertEqual(order_product.product_id, self.product.id)
        self.assertEqual(order_product.quantity, 2)
        self.assertEqual(order_product.product_price, 10)
        self.assertTrue(order_product.user, self.user)
        self.assertTrue(order_product.payment, payment)
        self.assertTrue(order_product.ordered, True)
        self.assertEqual(self.product.stock, 8)

    def test_payment_process_with_empty_cart(self):
        CartItem.objects.all().delete()
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('payments'), data=self.payment_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json().get('error'), 'Your cart is empty.')
        self.assertEqual(Payment.objects.count(), 0)
        self.assertEqual(OrderProduct.objects.count(), 0)
        self.assertEqual(self.product.stock, 10)


class TestPlaceOrder(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = Account.objects.create_user(
            first_name='John',
            last_name='Doe',
            email='johndoe@example.com',
            username='johndoe',
            password='password')
        self.client.login(username='testuser', password='testpass123')
        self.product = Product.objects.create(
            product_name='Test Product', price=10, stock=10)
        self.cart_item = CartItem.objects.create(
            user=self.user, product=self.product, quantity=1)

    def test_place_order_with_empty_cart(self):
        CartItem.objects.all().delete()
        response = self.client.get(reverse('place_order'))
        self.assertRedirects(response, reverse('store'))

    def test_place_order_with_nonempty_cart(self):
        response = self.client.get(reverse('place_order'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'orders/checkout.html')
        self.assertContains(response, 'form')

    def test_place_order_post(self):
        form_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'phone': '+123456789',
            'email': 'testuser@example.com',
            'address_line_1': 'Test Address 1',
            'address_line_2': 'Test Address 2',
            'country': 'Test Country',
            'state': 'Test State',
            'city': 'Test City',
            'order_note': 'Test Note',
        }
        response = self.client.post(reverse('place_order'), data=form_data)
        self.assertRedirects(response, reverse('payments'))
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.first()
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.first_name, form_data['first_name'])
        self.assertEqual(order.last_name, form_data['last_name'])
        self.assertEqual(order.phone, form_data['phone'])
        self.assertEqual(order.email, form_data['email'])
        self.assertEqual(order.address_line_1, form_data['address_line_1'])
        self.assertEqual(order.address_line_2, form_data['address_line_2'])
        self.assertEqual(order.country, form_data['country'])
        self.assertEqual(order.state, form_data['state'])
        self.assertEqual(order.city, form_data['city'])
        self.assertEqual(order.order_note, form_data['order_note'])
        self.assertEqual(order.order_total, self.cart_item.product.price)
        self.assertEqual(order.tax, (2 * self.cart_item.product.price)/100)
        self.assertEqual(order.ip, '127.0.0.1')
        self.assertEqual(order.order_number,
                         order.created_at.strftime('%Y%m%d') + str(order.id))


class TestOrderComplete(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = Account.objects.create_user(
            first_name='John',
            last_name='Doe',
            email='johndoe@example.com',
            username='johndoe',
            password='password')
        self.order = Order.objects.create(
            user=self.user,
            first_name='John',
            last_name='Doe',
            phone='1234567890',
            email='johndoe@example.com',
            address_line_1='123 Main St',
            address_line_2='',
            country='US',
            state='NY',
            city='New York',
            order_total=100,
            tax=2,
            order_number='202305091',
            ip='127.0.0.1',
            is_ordered=True
        )
        self.product = Product.objects.create(
            product_name='Test Product',
            slug='test-product',
            price=10,
            description='Test description',
            stock=10,
            is_available=True
        )
        self.order_product = OrderProduct.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            product_price=10
        )
        self.payment = Payment.objects.create(
            user=self.user,
            payment_id='123',
            payment_method='PayPal',
            amount_paid=102,
            status='COMPLETED'
        )

    def test_order_complete_with_valid_order_number_and_payment_id(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('order_complete') + '?order_number=202305091&payment_id=123')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'orders/order_complete.html')
        self.assertEqual(response.context['order'], self.order)
        self.assertEqual(list(response.context['ordered_products']), [
                         self.order_product])
        self.assertEqual(response.context['subtotal'], 20)
        self.assertEqual(response.context['order_number'], '202305091')
        self.assertEqual(response.context['transID'], '123')
        self.assertEqual(response.context['payment'], self.payment)

    def test_order_complete_with_invalid_order_number(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('order_complete') + '?order_number=12345&payment_id=123')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('home'))

    def test_order_complete_with_invalid_payment_id(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('order_complete') + '?order_number=202305091&payment_id=12345')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('home'))

    def test_order_complete_with_unauthenticated_user(self):
        response = self.client.get(
            reverse('order_complete') + '?order_number=202305091&payment_id=123')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse(
            'login') + '?next=' + reverse('order_complete') + '?order_number=202305091&#payment_id=123')
