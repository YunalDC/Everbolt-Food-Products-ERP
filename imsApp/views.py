from email import message
from unicodedata import category
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from django.utils import timezone
from ims_django.settings import MEDIA_ROOT, MEDIA_URL
from imsApp.forms import (
    SaveStock, UserRegistration, UpdateProfile, UpdatePasswords,
    SaveCategory, SaveProduct, SaveInvoice, SaveInvoiceItem
)
from imsApp.models import Category, Product, Stock, Invoice, Invoice_Item
from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib import messages
from decimal import Decimal
import json
import base64

context = {
    'page_title': 'File Management System',
}


# Login
def login_user(request):
    logout(request)
    resp = {"status": 'failed', 'msg': ''}
    username = ''
    password = ''

    if request.POST:
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                resp['status'] = 'success'
            else:
                resp['msg'] = "Incorrect username or password"
        else:
            resp['msg'] = "Incorrect username or password"

    return HttpResponse(json.dumps(resp), content_type='application/json')


# Logout
def logoutuser(request):
    logout(request)
    return redirect('/')


@login_required
def home(request):
    context['page_title'] = 'Home'
    context['categories'] = Category.objects.count()
    context['products'] = Product.objects.count()
    context['sales'] = Invoice.objects.count()
    return render(request, 'dashboard/home.html', context)


def registerUser(request):
    user = request.user
    if user.is_authenticated:
        return redirect('home-page')

    context['page_title'] = "Register User"

    if request.method == 'POST':
        data = request.POST
        form = UserRegistration(data)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            pwd = form.cleaned_data.get('password1')
            loginUser = authenticate(username=username, password=pwd)
            login(request, loginUser)
            return redirect('home-page')
        else:
            context['reg_form'] = form

    return render(request, 'accounts/register.html', context)


@login_required
def update_profile(request):
    context['page_title'] = 'Update Profile'
    user = User.objects.get(id=request.user.id)

    if request.method != 'POST':
        form = UpdateProfile(instance=user)
        context['form'] = form
    else:
        form = UpdateProfile(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile has been updated")
            return redirect("profile")
        else:
            context['form'] = form

    return render(request, 'accounts/manage_profile.html', context)


@login_required
def update_password(request):
    context['page_title'] = "Update Password"

    if request.method == 'POST':
        form = UpdatePasswords(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your Account Password has been updated successfully")
            update_session_auth_hash(request, form.user)
            return redirect("profile")
        else:
            context['form'] = form
    else:
        form = UpdatePasswords(request.POST)
        context['form'] = form

    return render(request, 'accounts/update_password.html', context)


@login_required
def profile(request):
    context['page_title'] = 'Profile'
    return render(request, 'accounts/profile.html', context)


# Category
@login_required
def category_mgt(request):
    context['page_title'] = "Product Categories"
    context['categories'] = Category.objects.all()
    return render(request, 'inventory/category_mgt.html', context)

@login_required
def inventory_list(request):
    products = Product.objects.all().order_by('name')

    context = {
        'products': products
    }
    return render(request, 'inventory/inventory_list.html', context)


@login_required
def save_category(request):
    resp = {'status': 'failed', 'msg': ''}

    if request.method == 'POST':
        if (request.POST['id']).isnumeric():
            category = Category.objects.get(pk=request.POST['id'])
        else:
            category = None

        if category is None:
            form = SaveCategory(request.POST)
        else:
            form = SaveCategory(request.POST, instance=category)

        if form.is_valid():
            form.save()
            messages.success(request, 'Category has been saved successfully.')
            resp['status'] = 'success'
        else:
            for fields in form:
                for error in fields.errors:
                    resp['msg'] += str(error + "<br>")
    else:
        resp['msg'] = 'No data has been sent.'

    return HttpResponse(json.dumps(resp), content_type='application/json')


@login_required
def manage_category(request, pk=None):
    context['page_title'] = "Manage Category"

    if pk is not None:
        context['category'] = Category.objects.get(id=pk)
    else:
        context['category'] = {}

    return render(request, 'inventory/manage_category.html', context)


@login_required
def delete_category(request):
    resp = {'status': 'failed', 'msg': ''}

    if request.method == 'POST':
        try:
            category = Category.objects.get(id=request.POST['id'])
            category.delete()
            messages.success(request, 'Category has been deleted successfully')
            resp['status'] = 'success'
        except Exception as err:
            resp['msg'] = 'Category has failed to delete'
            print(err)
    else:
        resp['msg'] = 'Category has failed to delete'

    return HttpResponse(json.dumps(resp), content_type="application/json")


# Product
@login_required
def product_mgt(request):
    context['page_title'] = "Product List"
    context['products'] = Product.objects.all()
    return render(request, 'inventory/product_mgt.html', context)


@login_required
def save_product(request):
    resp = {'status': 'failed', 'msg': ''}

    if request.method == 'POST':
        prod_id = request.POST.get('id', '').strip()
        product = None

        if prod_id.isnumeric():
            try:
                product = Product.objects.get(pk=prod_id)
            except Product.DoesNotExist:
                product = None

        if product is None:
            form = SaveProduct(request.POST, request.FILES)
        else:
            form = SaveProduct(request.POST, request.FILES, instance=product)

        if form.is_valid():
            form.save()
            messages.success(request, 'Product has been saved successfully.')
            resp['status'] = 'success'
        else:
            msg = ''
            for field in form:
                for error in field.errors:
                    msg += f'{error}<br>'
            for error in form.non_field_errors():
                msg += f'{error}<br>'
            resp['msg'] = msg
    else:
        resp['msg'] = 'No data has been sent.'

    return HttpResponse(json.dumps(resp), content_type='application/json')


@login_required
def manage_product(request, pk=None):
    context['page_title'] = "Manage Product"
    context['categories'] = Category.objects.filter(status='1').order_by('name')

    if pk is not None:
        context['product'] = get_object_or_404(Product, id=pk)
    else:
        context['product'] = {}

    return render(request, 'inventory/manage_product.html', context)


@login_required
def delete_product(request):
    resp = {'status': 'failed', 'msg': ''}

    if request.method == 'POST':
        try:
            product = Product.objects.get(id=request.POST['id'])
            product.delete()
            messages.success(request, 'Product has been deleted successfully')
            resp['status'] = 'success'
        except Exception as err:
            resp['msg'] = 'Product has failed to delete'
            print(err)
    else:
        resp['msg'] = 'Product has failed to delete'

    return HttpResponse(json.dumps(resp), content_type="application/json")


# Inventory
@login_required
def inventory(request):
    context['page_title'] = 'Inventory'
    context['products'] = Product.objects.all()
    return render(request, 'inventory/inventory.html', context)


# Inventory History
@login_required
def inv_history(request, pk=None):
    context['page_title'] = 'Inventory History'

    if pk is None:
        messages.error(request, "Product ID is not recognized")
        return redirect('inventory-page')

    product = Product.objects.get(id=pk)
    stocks = Stock.objects.filter(product=product).all()
    context['product'] = product
    context['stocks'] = stocks

    return render(request, 'inventory/inventory-history.html', context)


# Stock Form
@login_required
def manage_stock(request, pid=None, pk=None):
    if pid is None:
        messages.error(request, "Product ID is not recognized")
        return redirect('inventory-page')

    product = get_object_or_404(Product, id=pid)

    context['pid'] = pid
    context['product'] = product

    if pk is None:
        context['page_title'] = "Add New Stock"
        context['stock'] = None
    else:
        context['page_title'] = "Manage Stock"
        context['stock'] = get_object_or_404(Stock, id=pk, product=product)

    return render(request, 'inventory/manage_stock.html', context)


@login_required
def save_stock(request):
    resp = {'status': 'failed', 'msg': ''}

    if request.method != 'POST':
        resp['msg'] = 'No data has been sent.'
        return HttpResponse(json.dumps(resp), content_type='application/json')

    stock_id = request.POST.get('id', '').strip()
    instance = None

    if stock_id.isnumeric():
        instance = get_object_or_404(Stock, pk=stock_id)

    form = SaveStock(request.POST, instance=instance)

    if form.is_valid():
        form.save()
        messages.success(request, 'Stock has been saved successfully.')
        resp['status'] = 'success'
    else:
        errors = []
        for field, field_errors in form.errors.items():
            for err in field_errors:
                errors.append(err)
        resp['msg'] = '<br>'.join(errors)

    return HttpResponse(json.dumps(resp), content_type='application/json')


@login_required
def delete_stock(request):
    resp = {'status': 'failed', 'msg': ''}

    if request.method != 'POST':
        resp['msg'] = 'Stock has failed to delete'
        return HttpResponse(json.dumps(resp), content_type='application/json')

    stock_id = request.POST.get('id', '').strip()

    try:
        stock = Stock.objects.get(id=stock_id)
        stock.delete()
        messages.success(request, 'Stock has been deleted successfully')
        resp['status'] = 'success'
    except Stock.DoesNotExist:
        resp['msg'] = 'Stock record not found'
    except Exception as err:
        print(err)
        resp['msg'] = 'Stock has failed to delete'

    return HttpResponse(json.dumps(resp), content_type='application/json')


@login_required
def stock_page(request):
    context['page_title'] = "Stock"
    context['products'] = Product.objects.filter(status='1').order_by('name')
    context['categories'] = Category.objects.filter(status='1').order_by('name')
    return render(request, 'inventory/manage_stock.html', context)


@login_required
def sales_mgt(request):
    context['page_title'] = 'Sales'
    context['products'] = Product.objects.filter(status=1).all()
    return render(request, 'sales/sales.html', context)


def get_product(request, pk=None):
    resp = {'status': 'failed', 'data': {}, 'msg': ''}

    if pk is None:
        resp['msg'] = 'Product ID is not recognized'
    else:
        product = Product.objects.get(id=pk)
        resp['data']['product'] = str(product.code + " - " + product.name)
        resp['data']['id'] = product.id
        resp['data']['price'] = product.price
        resp['status'] = 'success'

    return HttpResponse(json.dumps(resp), content_type="application/json")


@login_required
def save_sales(request):
    if request.method != "POST":
        return JsonResponse(
            {"status": "failed", "msg": "Invalid request method"},
            status=405,
        )

    try:
        data = json.loads(request.body.decode("utf-8"))
    except ValueError:
        return JsonResponse(
            {"status": "failed", "msg": "Invalid JSON payload"},
            status=400,
        )

    customer = (data.get("customer") or "").strip()
    items = data.get("items") or []

    if not customer:
        return JsonResponse(
            {"status": "failed", "msg": "Customer name is required"},
            status=400,
        )

    if not items:
        return JsonResponse(
            {"status": "failed", "msg": "At least one item is required"},
            status=400,
        )

    total = Decimal("0")
    for item in items:
        price = Decimal(str(item.get("price", 0)))
        qty = Decimal(str(item.get("quantity", 0)))
        total += price * qty

    try:
        with transaction.atomic():
            invoice = Invoice.objects.create(
                transaction="TEMP",
                customer=customer,
                total=float(total),
                date_created=timezone.now(),
            )

            invoice.transaction = f"EFI {invoice.id:06d}"
            invoice.save(update_fields=["transaction"])

            for item in items:
                product_id = item.get("id")
                if not product_id:
                    continue

                try:
                    product = Product.objects.get(pk=product_id)
                except Product.DoesNotExist:
                    continue

                qty = float(item.get("quantity", 0)) or 0
                price = float(item.get("price", 0)) or 0

                if qty <= 0:
                    continue

                Invoice_Item.objects.create(
                    invoice=invoice,
                    product=product,
                    price=price,
                    quantity=qty,
                )

    except Exception as e:
        return JsonResponse(
            {"status": "failed", "msg": str(e)},
            status=500,
        )

    return JsonResponse(
        {
            "status": "success",
            "invoice_id": invoice.id,
            "transaction": invoice.transaction,
        }
    )


@login_required
def invoices(request):
    context['page_title'] = 'Invoices'
    context['invoices'] = Invoice.objects.all()
    return render(request, 'sales/invoices.html', context)


def invoice_print(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    items = Invoice_Item.objects.filter(invoice=invoice).select_related('product')

    subtotal = 0
    for item in items:
        subtotal += (item.price or 0) * (item.quantity or 0)

    tax_rate = 0.18
    tax = subtotal * tax_rate
    delivery_fee = 0
    discount = 0
    total = subtotal + tax + delivery_fee - discount

    invoice_context = {
        "invoice": invoice,
        "items": items,
        "subtotal": subtotal,
        "tax": tax,
        "delivery_fee": delivery_fee,
        "discount": discount,
        "total": total,
        "tax_rate_percent": int(tax_rate * 100),
    }
    return render(request, "invoices/invoice_print.html", invoice_context)


@login_required
def delete_invoice(request):
    resp = {'status': 'failed', 'msg': ''}

    if request.method == 'POST':
        try:
            invoice = Invoice.objects.get(id=request.POST['id'])
            invoice.delete()
            messages.success(request, 'Invoice has been deleted successfully')
            resp['status'] = 'success'
        except Exception as err:
            resp['msg'] = 'Invoice has failed to delete'
            print(err)
    else:
        resp['msg'] = 'Invoice has failed to delete'

    return HttpResponse(json.dumps(resp), content_type="application/json")