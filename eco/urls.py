import allauth
from django.urls import path


from .views import (
    HomeView,
    googlemap,
    CheckoutView,
    OrderSummaryView,
    add_to_cart,
    remove_from_cart,
    remove_single_item_from_cart,
    PaymentView,
    AddCouponView,
    RequestRefundView, api_items, api_order, api_order_items, api_address, api_payment, api_coupons, search,
    detail,)

app_name = 'eco'
urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('order-summary/', OrderSummaryView.as_view(), name='order-summary'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('product/<slug>/', detail, name='product'),
    path('add-to-cart/<slug>/', add_to_cart, name='add-to-cart'),
    path('remove-from-cart/<slug>/', remove_from_cart, name='remove-from-cart'),
    path('remove-single-item-from-cart/<slug>/', remove_single_item_from_cart, name='remove-single-item-from-cart'),
    path('payment/<payment_option>/', PaymentView.as_view(), name='payment'),
    path('add-coupon/', AddCouponView.as_view(), name='add-coupon'),
    path('request-refund/', RequestRefundView.as_view(), name='request-refund'),
    path('api/items/', api_items, name="api-items"),
    path('api/orders/', api_order, name="api-orders"),
    path('api/order-items/', api_order_items, name="api-order-items"),
    path('api/address/', api_address, name="api-address"),
    path('api/payment/', api_payment, name="api-payment"),
    path('api/coupons/', api_coupons, name="api-coupons"),
    path('search/', search, name="search"),
    path('googlemap/', googlemap, name='googlemap'),

]
