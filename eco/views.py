from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.query_utils import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View, CreateView
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializer import ItemSerializer, OrderSerializer, OrderItemSerializer, AddressSerializer, PaymentSerializer, \
    CouponSerializer
from .forms import CheckoutForm, CouponForm, RefundForm, ReviewForm
from .models import Item, OrderItem, Order, Address, Payment, Coupon, Refund, Review

import random
import string

import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))


def is_valid_form(values):
    valid = True
    for field in values:
        if field == '':
            valid = False
    return valid


class CheckoutView(View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            form = CheckoutForm()
            context = {
                'form': form,
                'couponform': CouponForm(),
                'order': order,
                'DISPLAY_COUPON_FORM': True
            }

            shipping_address_qs = Address.objects.filter(
                user=self.request.user,
                address_type='S',
                default=True
            )
            if shipping_address_qs.exists():
                context.update(
                    {'default_shipping_address': shipping_address_qs[0]})

            billing_address_qs = Address.objects.filter(
                user=self.request.user,
                address_type='B',
                default=True
            )
            if billing_address_qs.exists():
                context.update(
                    {'default_billing_address': billing_address_qs[0]})

            return render(self.request, "checkout.html", context)
        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have an active order")
            return redirect("eco:checkout")

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():

                use_default_shipping = form.cleaned_data.get(
                    'use_default_shipping')
                if use_default_shipping:
                    print("Using the defualt shipping address")
                    address_qs = Address.objects.filter(
                        user=self.request.user,
                        address_type='S',
                        default=True
                    )
                    if address_qs.exists():
                        shipping_address = address_qs[0]
                        order.shipping_address = shipping_address
                        order.save()
                    else:
                        messages.info(
                            self.request, "No default shipping address available")
                        return redirect('eco:checkout')
                else:
                    print("User is entering a new shipping address")
                    shipping_address1 = form.cleaned_data.get(
                        'shipping_address')
                    shipping_address2 = form.cleaned_data.get(
                        'shipping_address2')
                    shipping_country = form.cleaned_data.get(
                        'shipping_country')
                    shipping_zip = form.cleaned_data.get('shipping_zip')

                    if is_valid_form([shipping_address1, shipping_country, shipping_zip]):
                        shipping_address = Address(
                            user=self.request.user,
                            street_address=shipping_address1,
                            apartment_address=shipping_address2,
                            country=shipping_country,
                            zip=shipping_zip,
                            address_type='S'
                        )
                        shipping_address.save()

                        order.shipping_address = shipping_address
                        order.save()

                        set_default_shipping = form.cleaned_data.get(
                            'set_default_shipping')
                        if set_default_shipping:
                            shipping_address.default = True
                            shipping_address.save()

                    else:
                        messages.info(
                            self.request, "Please fill in the required shipping address fields")

                use_default_billing = form.cleaned_data.get(
                    'use_default_billing')
                same_billing_address = form.cleaned_data.get(
                    'same_billing_address')

                if same_billing_address:
                    billing_address = shipping_address
                    billing_address.pk = None
                    billing_address.save()
                    billing_address.address_type = 'B'
                    billing_address.save()
                    order.billing_address = billing_address
                    order.save()

                elif use_default_billing:
                    print("Using the defualt billing address")
                    address_qs = Address.objects.filter(
                        user=self.request.user,
                        address_type='B',
                        default=True
                    )
                    if address_qs.exists():
                        billing_address = address_qs[0]
                        order.billing_address = billing_address
                        order.save()
                    else:
                        messages.info(
                            self.request, "No default billing address available")
                        return redirect('eco:checkout')
                else:
                    print("User is entering a new billing address")
                    billing_address1 = form.cleaned_data.get(
                        'billing_address')
                    billing_address2 = form.cleaned_data.get(
                        'billing_address2')
                    billing_country = form.cleaned_data.get(
                        'billing_country')
                    billing_zip = form.cleaned_data.get('billing_zip')

                    if is_valid_form([billing_address1, billing_country, billing_zip]):
                        billing_address = Address(
                            user=self.request.user,
                            street_address=billing_address1,
                            apartment_address=billing_address2,
                            country=billing_country,
                            zip=billing_zip,
                            address_type='B'
                        )
                        billing_address.save()

                        order.billing_address = billing_address
                        order.save()

                        set_default_billing = form.cleaned_data.get(
                            'set_default_billing')
                        if set_default_billing:
                            billing_address.default = True
                            billing_address.save()

                    else:
                        messages.info(self.request, "Please fill in the required billing address fields")

                payment_option = form.cleaned_data.get('payment_option')

                if payment_option == 'S':
                    return redirect('eco:payment', payment_option='stripe')
                elif payment_option == 'P':
                    return redirect('eco:payment', payment_option='paypal')
                else:
                    messages.warning(
                        self.request, "Invalid payment option selected")
                    return redirect('eco:checkout')
        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect("eco:order-summary")


class PaymentView(View):
    def get(self, *args, **kwargs):
        # order
        order = Order.objects.get(user=self.request.user, ordered=False)
        if order.billing_address:
            context = {
                'order': order,
                'DISPLAY_COUPON_FORM': False
            }
            return render(self.request, "payment.html", context)
        else:
            messages.warning(self.request, "You  have not added a billing address")
            return redirect("eco:checkout")

    def post(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        token = self.request.POST.get('stripeToken')
        amount = int(order.get_total() * 100)

        try:
            # Use Stripe's library to make requests...
            charge = stripe.Charge.create(
                amount=amount,  # cents
                currency="usd",
                source=token
            )

            # Create the payment
            payment = Payment()
            payment.stripe_charge_id = charge['id']
            payment.user = self.request.user
            payment.amount = order.get_total()
            payment.save()

            # assign the payment to the order
            order_items = order.items.all()
            order_items.update(ordered=True)
            for item in order_items:
                item.save()

            order.ordered = True
            order.payment = payment
            # TODO:assign ref code
            order.ref_code = create_ref_code()
            order.save()

            messages.success(self.request, "Your order was succesful!")
            return redirect("/")

        except stripe.error.CardError as e:
            # Since it's a decline, stripe.error.CardError will be caught
            body = e.json_body
            err = body.get('error', {})
            messages.warning(self.request, f" {err.get('message')}")
            return redirect("/")

        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            messages.warning(self.request, "Rate Limit Error")
            return redirect("/")

        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            messages.warning(self.request, "Invalid Parameters")
            return redirect("/")

        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            messages.warning(self.request, "Not Authenticated")
            return redirect("/")

        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            messages.warning(self.request, "Network Error")
            return redirect("/")

        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            messages.warning(self.request, "Something went wrong.You were not charged.Please try again.")
            return redirect("/")

        except Exception as e:
            # send an email to ourselves
            messages.warning(self.request, "A serious error occured.We have been noftified.")
            return redirect("/")


class HomeView(ListView):
    model = Item
    paginate_by = 10
    template_name = "home.html"


class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'object': order
            }
            return render(self.request, "order-summary.html", context)
        except ObjectDoesNotExist:
            messages.error(self.request, "You do not have an active order")
            return redirect("/")


def detail(req, slug):
    item = Item.objects.get(active=True, slug=slug)
    if req.method == "POST":
        form = ReviewForm(req.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.item = item
            review.user = req.user
            review.save()
            messages.success(req, "Review saved")
        else:
            messages.error(req, "Invalid form")
    else:
        form = ReviewForm()
    context = {"item": item,
               "form": form}
    return render(req, "product.html", context)


@login_required
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(item=item,
                                                          user=request.user,
                                                          ordered=False)
    # query set of the order
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "This item quantity  is updated.")
            return redirect("eco:order-summary")
        else:
            order.items.add(order_item)
            messages.info(request, "This item is added to your cart.")
            return redirect("eco:order-summary")
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(user=request.user,
                                     ordered_date=ordered_date)
        order.items.add(order_item)

        messages.info(request, "This item is added to your cart.")
        return redirect("eco:order-summary")


@login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            order.items.remove(order_item)
            messages.info(request, "This item is removed from your cart.")
            return redirect("eco:order-summary")
        else:
            messages.info(request, "This item is not in your cart.")
            return redirect("eco:product", slug=slug)
    else:
        messages.info(request, "You do not have an active order.")
        return redirect("eco:product", slug=slug)


@login_required
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)

            messages.info(request, "This item quantity iss updated.")
            return redirect("eco:order-summary")
        else:

            messages.info(request, "This item is not in your cart.")
            return redirect("eco:product", slug=slug)

    else:

        messages.info(request, "You do not have an active order.")
        return redirect("eco:product", slug=slug)


def get_coupon(request, code):
    try:
        coupon = Coupon.objects.get(code=code)
        return coupon
    except ObjectDoesNotExist:
        messages.info(request, "This coupon does not exist")
        return redirect("eco:checkout")


class AddCouponView(View):
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code = form.cleaned_data.get('code')
                order = Order.objects.get(user=self.request.user, ordered=False)
                order.coupon = get_coupon(self.request, code)
                order.save()
                messages.success(self.request, "Successfully added coupon")
                return redirect("eco:checkout")
            except ObjectDoesNotExist:
                messages.info(self.request, "You do not have an active order")
                return redirect("eco:checkout")


class RequestRefundView(View):
    def get(self, *args, **kwargs):
        form = RefundForm()
        context = {
            'form': form
        }
        return render(self.request, "request_refund.html", context)

    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST)
        if form.is_valid():
            ref_code = form.cleaned_data.get('ref_code')
            message = form.cleaned_data.get('message')
            email = form.cleaned_data.get('email')
            # edit the order
            try:
                order = Order.objects.get(ref_code=ref_code)
                order.refund_requested = True
                order.save()

                # store the refund
                refund = Refund()
                refund.order = order
                refund.reason = message
                refund.email = email
                refund.save()

                messages.info(self.request, "Your request is received.")
                return redirect("eco:request-refund")

            except ObjectDoesNotExist:
                messages.info(self.request, "This order does not exist.")
                return redirect("eco:request-refund")


def search(req):
    q = req.GET["q"]
    items = Item.objects.filter(title__icontains=q)
    context = {'items': items,
               'title': q + " - search"}
    return render(req, "list.html", context)


def googlemap(req):
    return render(req, "map.html", {})


@api_view(['GET'])
def api_items(req):
    items = Item.objects.filter(Q())
    serializer = ItemSerializer(items, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def api_order(req):
    items = Order.objects.filter(Q())
    serializer = OrderSerializer(items, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def api_order_items(req):
    items = OrderItem.objects.filter(Q())
    serializer = OrderItemSerializer(items, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def api_address(req):
    items = Address.objects.filter(Q())
    serializer = AddressSerializer(items, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def api_payment(req):
    items = Payment.objects.filter(Q())
    serializer = PaymentSerializer(items, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def api_coupons(req):
    items = Coupon.objects.filter(Q())
    serializer = CouponSerializer(items, many=True)
    return Response(serializer.data)



