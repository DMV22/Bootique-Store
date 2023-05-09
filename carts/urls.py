from django.urls import path
from . import views

urlpatterns = [
    path('', views.cart, name='cart'),
    path('add_to_cart/<int:product_id>/',
         views.add_to_cart, name='add_to_cart'),
    path('subtract_from_cart/<int:product_id>/<int:cart_item_id>/',
         views.subtract_from_cart, name='subtract_from_cart'),
    path('remove_from_cart/<int:product_id>/<int:cart_item_id>/',
         views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
]
