from decimal import Decimal
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db.models import Sum,Avg,Q
from store import models as store_models
from store.models import Product 
from customer import models as customer_models 
from django.contrib import messages
from django.conf import settings
import requests
from plugin.tax_calculation import tax_calculation

EXCHANGE_RATE = 132


def index(request):
    products= store_models.Product.objects.filter(status="Published")
    return render(request, "store/index.html",{"products": products})

def product_detail(request, slug):
    product = store_models.Product.objects.get(slug=slug, status="Published")
    related_product = store_models.Product.objects.filter(category= product.category,status="Published").exclude(id=product.id)
    product_stock_range= range(1,product.stock +1)

    context = {
        "product": product,
        "related_product":related_product,
        "product_stock_range": product_stock_range,
    }
    return render(request, "store/product_detail.html", context)




def add_to_cart(request):
    id = request.GET.get("id")
    qty = request.GET.get("qty")
    color = request.GET.get("color")
    size = request.GET.get("size")
    cart_id = request.GET.get("cart_id")

    request.session['cart_id'] = cart_id

    if not id or not qty or not cart_id:
        return JsonResponse({"error": "No id, qty, or cart_id"}, status=400)
    
    try:
        product = store_models.Product.objects.get(status="Published", id=id)
    except store_models.Product.DoesNotExist:
        return JsonResponse({"error": "Product not found"}, status=404)
    
    existing_cart_items = store_models.Cart.objects.filter(cart_id=cart_id, product=product).first()

    if int(qty) > product.stock:
        return JsonResponse({"error": "Quantity exceeds available stock"}, status=400)
    
    if not existing_cart_items:
        cart = store_models.Cart(
            product=product,
            qty=int(qty),
            price=product.price,
            color=color,
            size=size,
            sub_total=Decimal(product.price) * Decimal(qty),
            shipping=Decimal(product.shipping) * Decimal(qty),
            total=(Decimal(product.price) * Decimal(qty)) + (Decimal(product.shipping) * Decimal(qty)),
            user=request.user if request.user.is_authenticated else None,
            cart_id=cart_id
        )
        cart.save()
        message = "Item added to cart"
    else:
        existing_cart_items.qty = int(qty)
        existing_cart_items.sub_total = Decimal(product.price) * Decimal(qty)
        existing_cart_items.shipping = Decimal(product.shipping) * Decimal(qty)
        existing_cart_items.total = existing_cart_items.sub_total + existing_cart_items.shipping
        existing_cart_items.save()
        message = "Cart updated"

    total_cart_items = store_models.Cart.objects.filter(cart_id=cart_id).count()
    cart_sub_total = store_models.Cart.objects.filter(cart_id=cart_id).aggregate(sub_total=Sum("sub_total"))["sub_total"] or Decimal(0)

    return JsonResponse({
        "message": message,
        "total_cart_items": total_cart_items,
        "cart_sub_total": "{:,.2f}".format(cart_sub_total),
        "item_sub_total": "{:,.2f}".format(existing_cart_items.sub_total if existing_cart_items else cart_sub_total)
    })

def cart(request):
    if "cart_id" in request.session:
        cart_id = request.session["cart_id"]
    else:
        cart_id = None

    items = store_models.Cart.objects.filter( Q(cart_id=cart_id) | Q(user= request.user) if request.user.is_authenticated else Q(cart_id=cart_id))
    cart_sub_total= store_models.Cart.objects.filter( Q(cart_id=cart_id) |  Q(user= request.user) if request.user.is_authenticated else Q(cart_id=cart_id)).aggregate(sub_total= Sum("sub_total"))['sub_total']

    try:
        addresses = customer_models.Address.objects.filter(user=request.user)
    except:
        addresses = None
    
    if not items:
        messages.warning(request,"No items in cart")
        return redirect("store:index")
    
    context = {
        "items": items,
        "cart_sub_total": cart_sub_total,
        "addresses": addresses,
    }

    return render(request,"store/cart.html", context)

def delete_cart_item(request):
    id= request.GET.get("id")
    item_id = request.GET.get("item_id")
    cart_id = request.GET.get("cart_id")

    if not id and not item_id and not cart_id:
        return JsonResponse({"error":"item or Product Id not found"},status= 400)
    
    try:
        product = store_models.Product.objects.get(status="Published", id=id)
    except store_models.Product.DoesNotExist:
        return JsonResponse({"error":"Product not found"},status= 404)

    item = store_models.Cart.objects.get(product=product,id = item_id)
    item.delete()

    total_cart_items=store_models.Cart.objects.filter( Q(cart_id=cart_id) | Q(user= request.user))
    cart_sub_total= store_models.Cart.objects.filter( Q(cart_id=cart_id) | Q(user= request.user)).aggregate(sub_total= Sum("sub_total"))['sub_total']

    return JsonResponse({
        "message":"Item deleted",
        "total_cart_items": total_cart_items.count(),
        "cart_sub_total" : "{:,.2f}".format(cart_sub_total) if cart_sub_total else 0.00
    })

def create_order(request):
    if request.method== "POST":
        address_id = request.POST.get("address")

        if not address_id:
            messages.warning(request,"Please select an address to continue")
            return redirect("store:cart")
        
        address = customer_models.Address.objects.filter(user=request.user, id= address_id).first()

        if 'cart_id' in request.session:
            cart_id= request.session['cart_id']
        else:
            cart_id= None

        items = store_models.Cart.objects.filter(Q(cart_id=cart_id) | Q(user= request.user) if request.user.is_authenticated else Q(cart_id=cart_id))
        cart_sub_total = store_models.Cart.objects.filter(Q(cart_id=cart_id) | Q(user= request.user) if request.user.is_authenticated else Q(cart_id=cart_id)).aggregate(sub_total = Sum("sub_total"))["sub_total"]
        cart_shipping_total = store_models.Cart.objects.filter(Q(cart_id=cart_id) | Q(user= request.user) if request.user.is_authenticated else Q(cart_id=cart_id)).aggregate(shipping = Sum("shipping"))["shipping"]

        order = store_models.Order()
        order.sub_total = cart_sub_total
        order.customer = request.user or None
        order.address= address
        order.shipping = cart_shipping_total
        order.tax = tax_calculation(address.country, cart_sub_total)
        order.total = order.sub_total + order.shipping+ Decimal (order.tax)
        order.initial_total= order.total
        order.save()

        for i in items:
            store_models.OrderItem.objects.create(
                order= order,
                product=i.product,
                qty=i.qty,
                color= i.color,
                size=i.size,
                price= i.price,
                sub_total=i.sub_total,
                shipping=i.shipping,
                tax= tax_calculation(address.country, i.sub_total),
                total= i.total,
                initial_total=i.total,
                vendor=i.product.vendor
            )

            order.vendors.add(i.product.vendor)

    return redirect("store:checkout", order.order_id)

def checkout(request, order_id):
     order = store_models.Order.objects.get(order_id= order_id)
     total_in_usd = round(order.total / EXCHANGE_RATE, 2)

     context = {
         "order":order,
         "paypal_client_id" : settings.PAYPAL_CLIENT_ID,
         'total_in_usd': total_in_usd,
     }
     return render(request,"store/checkout.html", context)

def coupon_apply(request, order_id):
    print("Order Id ========", order_id)
    
    try:
        order = store_models.Order.objects.get(order_id=order_id)
        order_items = store_models.OrderItem.objects.filter(order=order)
    except store_models.Order.DoesNotExist:
        messages.error(request, "Order not found")
        return redirect("store:cart")

    if request.method == 'POST':
        coupon_code = request.POST.get("coupon_code")
        
        if not coupon_code:
            messages.error(request, "No coupon entered")
            return redirect("store:checkout", order.order_id)
            
        try:
            coupon = store_models.Coupon.objects.get(code=coupon_code)
        except store_models.Coupon.DoesNotExist:
            messages.error(request, "Coupon does not exist")
            return redirect("store:checkout", order.order_id)
        
        if coupon in order.coupons.all():
            messages.warning(request, "Coupon already activated")
            return redirect("store:checkout", order.order_id)
        else:
            # Assuming coupon applies to specific vendor items, not globally
            total_discount = 0
            for item in order_items:
                if coupon.vendor == item.product.vendor and coupon not in item.coupon.all():
                    item_discount = item.total * coupon.discount / 100  
                    total_discount += item_discount

                    item.coupon.add(coupon) 
                    item.total -= item_discount
                    item.saved += item_discount
                    item.save()

            # Apply total discount to the order after processing all items
            if total_discount > 0:
                order.coupons.add(coupon)
                order.total -= total_discount
                order.sub_total -= total_discount
                order.saved += total_discount
                order.save()
        
        messages.success(request, "Coupon Activated")
        return redirect("store:checkout", order.order_id)
    
def clear_cart_items(request):
    try:
        cart_id = request.session['cart_id']
        store_models.Cart.objects.filter(cart_id=cart_id).delete()
    except:
        pass
    return
    
def get_paypal_access_token():
    token_url = 'https://api.sandbox.paypal.com/v1/oauth2/token'
    data = {'grant_type': 'client_credentials'}
    auth = (settings.PAYPAL_CLIENT_ID, settings.PAYPAL_SECRET_ID)
    response = requests.post(token_url, data=data, auth=auth)

    if response.status_code == 200:
        return response.json()['access_token']
    else:
        raise Exception(f'Failed to get access token from PayPal. Status code: {response.status_code}') 

def paypal_payment_verify(request, order_id):
    order = store_models.Order.objects.get(order_id=order_id)

    transaction_id = request.GET.get("transaction_id")
    paypal_api_url = f'https://api-m.sandbox.paypal.com/v2/checkout/orders/{transaction_id}'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {get_paypal_access_token()}',
    }
    response = requests.get(paypal_api_url, headers=headers)

    if response.status_code == 200:
        paypal_order_data = response.json()
        paypal_payment_status = paypal_order_data['status']
        payment_method = "PayPal"
        if paypal_payment_status == 'COMPLETED':
            if order.payment_status == "Processing":
                order.payment_status = "Paid"
                order.payment_method = payment_method
                order.save() 

                clear_cart_items(request)
                return redirect(f"/payment_status/{order.order_id}/?payment_status=paid")
    else:
        return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")
    

    
def payment_status(request, order_id):
    order = store_models.Order.objects.get(order_id=order_id)
    payment_status = request.GET.get("payment_status")

    context = {
        "order": order,
        "payment_status": payment_status
    }
    return render(request, "store/payment_status.html", context)
