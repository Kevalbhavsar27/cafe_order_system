from decimal import Decimal

from django.utils import timezone
from django.db.models import Sum
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpResponseForbidden
import csv
from django.http import HttpResponse
import json
from django.core.serializers.json import DjangoJSONEncoder
import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import os
import shutil
from django.http import FileResponse
from datetime import datetime
from django.core.files.storage import FileSystemStorage

from rest_framework.views import APIView
from rest_framework.response import Response

from accounts.models import UserProfile
from tables.models import CafeTable
from menu.models import Category, MenuItem
from orders.models import Order, OrderItem
from billing.models import Bill
from settingsapp.models import CafeSetting

from orders.serializers import OrderSerializer
from .permissions import IsAdminUserProfile
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta

# =========================
# ROLE HELPERS
# =========================

def get_user_role(user):
    if not user.is_authenticated:
        return None

    profile, created = UserProfile.objects.get_or_create(
        user=user,
        defaults={"role": "ADMIN" if user.is_superuser else "COUNTER"}
    )
    return profile.role


def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("staff_login")

        role = get_user_role(request.user)

        if request.user.is_superuser or role == "ADMIN":
            return view_func(request, *args, **kwargs)

        return HttpResponseForbidden("You are not allowed to access admin page")

    return wrapper


def counter_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("staff_login")

        role = get_user_role(request.user)

        if request.user.is_superuser or role in ["ADMIN", "COUNTER"]:
            return view_func(request, *args, **kwargs)

        return HttpResponseForbidden("You are not allowed to access counter page")

    return wrapper


def kitchen_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("staff_login")

        role = get_user_role(request.user)

        if request.user.is_superuser or role in ["ADMIN", "KITCHEN"]:
            return view_func(request, *args, **kwargs)

        return HttpResponseForbidden("You are not allowed to access kitchen page")

    return wrapper


# =========================
# LOGIN / LOGOUT
# =========================

def staff_login(request):
    if request.user.is_authenticated:
        role = get_user_role(request.user)

        if role == "ADMIN":
            return redirect("admin_dashboard")
        elif role == "COUNTER":
            return redirect("staff_panel")
        elif role == "KITCHEN":
            return redirect("kitchen_panel")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            role = get_user_role(user)

            if role == "ADMIN":
                return redirect("admin_dashboard")
            elif role == "COUNTER":
                return redirect("staff_panel")
            elif role == "KITCHEN":
                return redirect("kitchen_panel")

            messages.error(request, "Invalid user role")
            return redirect("staff_login")

        messages.error(request, "Invalid username or password")

    return render(request, "login.html")


def staff_logout(request):
    logout(request)
    return redirect("staff_login")


@counter_required
def staff_panel(request):
    return redirect("counter_orders")


@kitchen_required
def kitchen_panel(request):
    return redirect("kitchen_orders")


# =========================
# ADMIN DASHBOARD
# =========================

@admin_required
def admin_dashboard(request):
    context = {
        "total_staff": UserProfile.objects.count(),
        "total_admin": UserProfile.objects.filter(role="ADMIN").count(),
        "total_counter": UserProfile.objects.filter(role="COUNTER").count(),
        "total_kitchen": UserProfile.objects.filter(role="KITCHEN").count(),
        "total_tables": CafeTable.objects.count(),
        "total_menu_items": MenuItem.objects.count(),
        "total_orders": Order.objects.count(),
        "pending_orders": Order.objects.filter(status="PENDING").count(),
        "recent_orders": Order.objects.select_related("table").order_by("-created_at")[:10],
    }

    return render(request, "dashboard/admin_dashboard.html", context)

@admin_required
def export_orders_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="orders_report.csv"'

    writer = csv.writer(response)

    writer.writerow([
        "Order ID",
        "Table",
        "Customer Name",
        "Customer Mobile",
        "Status",
        "Payment Status",
        "Payment Method",
        "Total Amount",
        "Date",
    ])

    orders = Order.objects.select_related("table").order_by("-created_at")

    for order in orders:
        writer.writerow([
            order.id,
            order.table.table_number,
            order.customer_name or "Guest",
            order.customer_mobile or "",
            order.status,
            order.payment_status,
            order.payment_method,
            order.total_amount,
            order.created_at.strftime("%d-%m-%Y %I:%M %p"),
        ])

    return response

@admin_required
def download_backup(request):
    db_path = settings.DATABASES["default"]["NAME"]

    filename = f"cafe_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite3"

    return FileResponse(
        open(db_path, "rb"),
        as_attachment=True,
        filename=filename
    )
@admin_required
def export_bills_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="bills_report.csv"'

    writer = csv.writer(response)

    writer.writerow([
        "Bill Number",
        "Order ID",
        "Table",
        "Subtotal",
        "Tax",
        "Discount",
        "Grand Total",
        "Payment Status",
        "Date",
    ])

    bills = Bill.objects.select_related("order", "order__table").order_by("-created_at")

    for bill in bills:
        writer.writerow([
            bill.bill_number,
            bill.order.id,
            bill.order.table.table_number,
            bill.subtotal,
            bill.tax_amount,
            bill.discount_amount,
            bill.grand_total,
            bill.payment_status,
            bill.created_at.strftime("%d-%m-%Y %I:%M %p"),
        ])

    return response


@admin_required
def export_reports_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="sales_summary_report.csv"'

    writer = csv.writer(response)

    total_orders = Order.objects.count()
    paid_orders = Order.objects.filter(payment_status="PAID").count()
    unpaid_orders = Order.objects.filter(payment_status="UNPAID").count()
    cancelled_orders = Order.objects.filter(status="CANCELLED").count()

    total_revenue = Bill.objects.filter(
        payment_status="PAID"
    ).aggregate(total=Sum("grand_total"))["total"] or 0

    writer.writerow(["Cafe Sales Summary"])
    writer.writerow([])

    writer.writerow(["Total Orders", total_orders])
    writer.writerow(["Paid Orders", paid_orders])
    writer.writerow(["Unpaid Orders", unpaid_orders])
    writer.writerow(["Cancelled Orders", cancelled_orders])
    writer.writerow(["Total Revenue", total_revenue])

    writer.writerow([])
    writer.writerow(["Top Selling Items"])
    writer.writerow(["Item", "Quantity Sold", "Total Sales"])

    top_items = OrderItem.objects.values(
        "menu_item__name"
    ).annotate(
        total_qty=Sum("quantity"),
        total_sales=Sum("subtotal")
    ).order_by("-total_qty")[:20]

    for item in top_items:
        writer.writerow([
            item["menu_item__name"],
            item["total_qty"],
            item["total_sales"],
        ])

    return response

@admin_required
def order_history(request):
    orders = Order.objects.select_related("table").prefetch_related("items__menu_item").order_by("-created_at")

    status = request.GET.get("status")
    payment = request.GET.get("payment")
    date_filter = request.GET.get("date_filter")
    search = request.GET.get("search")

    today = timezone.localdate()

    if status:
        orders = orders.filter(status=status)

    if payment:
        orders = orders.filter(payment_status=payment)

    if date_filter == "today":
        orders = orders.filter(created_at__date=today)

    elif date_filter == "yesterday":
        yesterday = today - timedelta(days=1)
        orders = orders.filter(created_at__date=yesterday)

    elif date_filter == "week":
        week_start = today - timedelta(days=7)
        orders = orders.filter(created_at__date__gte=week_start)

    elif date_filter == "month":
        month_start = today.replace(day=1)
        orders = orders.filter(created_at__date__gte=month_start)

    if search:
        orders = orders.filter(
            id__icontains=search
        )

    context = {
        "orders": orders,
        "status": status,
        "payment": payment,
        "date_filter": date_filter,
        "search": search,
    }

    return render(request, "dashboard/order_history.html", context)

# =========================
# STAFF MANAGEMENT - ADMIN ONLY
# =========================

@admin_required
def staff_list(request):
    staff = UserProfile.objects.select_related("user").order_by("-created_at")
    return render(request, "dashboard/staff_list.html", {"staff": staff})


@admin_required
def staff_add(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        phone = request.POST.get("phone")
        role = request.POST.get("role")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect("staff_add")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=True,
        )

        UserProfile.objects.create(
            user=user,
            phone=phone,
            role=role,
        )

        messages.success(request, "Staff added successfully")
        return redirect("staff_list")

    return render(request, "dashboard/staff_add.html")


@admin_required
def staff_edit(request, id):
    profile = get_object_or_404(UserProfile, id=id)

    if request.method == "POST":
        profile.user.username = request.POST.get("username")
        profile.user.email = request.POST.get("email")
        profile.phone = request.POST.get("phone")
        profile.role = request.POST.get("role")
        profile.user.is_active = request.POST.get("is_active") == "on"

        password = request.POST.get("password")
        if password:
            profile.user.set_password(password)

        profile.user.save()
        profile.save()

        messages.success(request, "Staff updated successfully")
        return redirect("staff_list")

    return render(request, "dashboard/staff_edit.html", {"profile": profile})


@admin_required
def staff_delete(request, id):
    profile = get_object_or_404(UserProfile, id=id)

    if profile.user == request.user:
        messages.error(request, "You cannot delete your own account")
        return redirect("staff_list")

    profile.user.delete()
    messages.success(request, "Staff deleted successfully")
    return redirect("staff_list")


# =========================
# TABLES - ADMIN ONLY
# =========================

@admin_required
def tables_list(request):
    tables = CafeTable.objects.all().order_by("table_number")
    return render(request, "dashboard/tables_list.html", {"tables": tables})


@admin_required
def table_add(request):
    if request.method == "POST":
        table_number = request.POST.get("table_number")
        table_name = request.POST.get("table_name")
        capacity = request.POST.get("capacity")
        is_active = request.POST.get("is_active") == "on"

        if CafeTable.objects.filter(table_number=table_number).exists():
            messages.error(request, "Table number already exists")
            return redirect("table_add")

        CafeTable.objects.create(
            table_number=table_number,
            table_name=table_name,
            capacity=capacity,
            is_active=is_active,
        )

        messages.success(request, "Table added successfully")
        return redirect("tables_list")

    return render(request, "dashboard/table_add.html")


@admin_required
def table_edit(request, id):
    table = get_object_or_404(CafeTable, id=id)

    if request.method == "POST":
        table.table_number = request.POST.get("table_number")
        table.table_name = request.POST.get("table_name")
        table.capacity = request.POST.get("capacity")
        table.is_active = request.POST.get("is_active") == "on"
        table.status = request.POST.get("status")
        table.save()

        messages.success(request, "Table updated successfully")
        return redirect("tables_list")

    return render(request, "dashboard/table_edit.html", {"table": table})


@admin_required
def table_delete(request, id):
    table = get_object_or_404(CafeTable, id=id)
    table.delete()
    messages.success(request, "Table deleted successfully")
    return redirect("tables_list")


@admin_required
def table_qr_print(request, id):
    table = get_object_or_404(CafeTable, id=id)

    if not table.qr_code:
        table.generate_qr_code()
        table.save()

    return render(request, "dashboard/table_qr_print.html", {"table": table})


# =========================
# CATEGORY - ADMIN ONLY
# =========================

@admin_required
def category_list(request):
    categories = Category.objects.all().order_by("name")
    return render(request, "dashboard/category_list.html", {"categories": categories})


@admin_required
def category_add(request):
    if request.method == "POST":
        Category.objects.create(
            name=request.POST.get("name"),
            description=request.POST.get("description"),
            image=request.FILES.get("image"),
            is_active=True,
        )

        messages.success(request, "Category added successfully")
        return redirect("category_list")

    return render(request, "dashboard/category_add.html")


@admin_required
def category_edit(request, id):
    category = get_object_or_404(Category, id=id)

    if request.method == "POST":
        category.name = request.POST.get("name")
        category.description = request.POST.get("description")
        category.is_active = request.POST.get("is_active") == "on"

        image = request.FILES.get("image")
        if image:
            category.image = image

        category.save()

        messages.success(request, "Category updated successfully")
        return redirect("category_list")

    return render(request, "dashboard/category_edit.html", {"category": category})


@admin_required
def category_delete(request, id):
    category = get_object_or_404(Category, id=id)

    if category.menu_items.exists():
        messages.error(request, "Cannot delete category because it has menu items")
        return redirect("category_list")

    category.delete()
    messages.success(request, "Category deleted successfully")
    return redirect("category_list")


@admin_required
def category_toggle(request, id):
    category = get_object_or_404(Category, id=id)
    category.is_active = not category.is_active
    category.save()

    messages.success(request, "Category status updated")
    return redirect("category_list")


# =========================
# MENU - ADMIN ONLY
# =========================
@admin_required
def reports_dashboard(request):
    today = timezone.localdate()
    week_start = today - timedelta(days=7)
    month_start = today.replace(day=1)

    today_orders = Order.objects.filter(created_at__date=today)
    week_orders = Order.objects.filter(created_at__date__gte=week_start)
    month_orders = Order.objects.filter(created_at__date__gte=month_start)

    today_revenue = Bill.objects.filter(
        created_at__date=today,
        payment_status="PAID"
    ).aggregate(total=Sum("grand_total"))["total"] or 0

    week_revenue = Bill.objects.filter(
        created_at__date__gte=week_start,
        payment_status="PAID"
    ).aggregate(total=Sum("grand_total"))["total"] or 0

    month_revenue = Bill.objects.filter(
        created_at__date__gte=month_start,
        payment_status="PAID"
    ).aggregate(total=Sum("grand_total"))["total"] or 0

    top_items = OrderItem.objects.values(
        "menu_item__name"
    ).annotate(
        total_qty=Sum("quantity"),
        total_sales=Sum("subtotal")
    ).order_by("-total_qty")[:10]

    table_report = Order.objects.values(
        "table__table_number"
    ).annotate(
        total_orders=Count("id"),
        total_amount=Sum("total_amount")
    ).order_by("-total_orders")[:10]

    order_status_chart = {
        "Pending": Order.objects.filter(status="PENDING").count(),
        "Accepted": Order.objects.filter(status="ACCEPTED").count(),
        "Preparing": Order.objects.filter(status="PREPARING").count(),
        "Ready": Order.objects.filter(status="READY").count(),
        "Served": Order.objects.filter(status="SERVED").count(),
        "Cancelled": Order.objects.filter(status="CANCELLED").count(),
    }

    revenue_chart = {
        "Today": float(today_revenue),
        "Last 7 Days": float(week_revenue),
        "This Month": float(month_revenue),
    }

    top_items_chart = list(
        OrderItem.objects.values("menu_item__name")
        .annotate(total_qty=Sum("quantity"))
        .order_by("-total_qty")[:7]
    )
    context = {
        "today": today,

        "today_orders_count": today_orders.count(),
        "week_orders_count": week_orders.count(),
        "month_orders_count": month_orders.count(),

        "today_revenue": today_revenue,
        "week_revenue": week_revenue,
        "month_revenue": month_revenue,

        "pending_orders": Order.objects.filter(status="PENDING").count(),
        "accepted_orders": Order.objects.filter(status="ACCEPTED").count(),
        "preparing_orders": Order.objects.filter(status="PREPARING").count(),
        "ready_orders": Order.objects.filter(status="READY").count(),
        "served_orders": Order.objects.filter(status="SERVED").count(),
        "cancelled_orders": Order.objects.filter(status="CANCELLED").count(),

        "paid_orders": Order.objects.filter(payment_status="PAID").count(),
        "unpaid_orders": Order.objects.filter(payment_status="UNPAID").count(),

        "top_items": top_items,
        "table_report": table_report,

        "order_status_chart": json.dumps(order_status_chart, cls=DjangoJSONEncoder),
        "revenue_chart": json.dumps(revenue_chart, cls=DjangoJSONEncoder),
        "top_items_chart": json.dumps(top_items_chart, cls=DjangoJSONEncoder),
    }

    return render(request, "dashboard/reports_dashboard.html", context)

@admin_required
def menu_list(request):
    items = MenuItem.objects.select_related("category").order_by("name")
    return render(request, "dashboard/menu_list.html", {"items": items})


@admin_required
def menu_add(request):
    categories = Category.objects.filter(is_active=True)

    if request.method == "POST":
        MenuItem.objects.create(
            category_id=request.POST.get("category"),
            name=request.POST.get("name"),
            description=request.POST.get("description"),
            price=request.POST.get("price"),
            preparation_time=request.POST.get("preparation_time"),
            image=request.FILES.get("image"),
            is_available=True,
        )

        messages.success(request, "Menu item added successfully")
        return redirect("menu_list")

    return render(request, "dashboard/menu_add.html", {"categories": categories})


@admin_required
def menu_edit(request, id):
    item = get_object_or_404(MenuItem, id=id)
    categories = Category.objects.filter(is_active=True)

    if request.method == "POST":
        item.category_id = request.POST.get("category")
        item.name = request.POST.get("name")
        item.description = request.POST.get("description")
        item.price = request.POST.get("price")
        item.preparation_time = request.POST.get("preparation_time")
        item.is_available = request.POST.get("is_available") == "on"

        image = request.FILES.get("image")
        if image:
            item.image = image

        item.save()

        messages.success(request, "Menu item updated successfully")
        return redirect("menu_list")

    return render(request, "dashboard/menu_edit.html", {
        "item": item,
        "categories": categories,
    })


@admin_required
def menu_toggle(request, id):
    item = get_object_or_404(MenuItem, id=id)
    item.is_available = not item.is_available
    item.save()

    messages.success(request, "Menu item status updated")
    return redirect("menu_list")


@admin_required
def menu_delete(request, id):
    item = get_object_or_404(MenuItem, id=id)
    item.delete()

    messages.success(request, "Menu item deleted successfully")
    return redirect("menu_list")

@admin_required
def table_mark_available(request, id):
    table = get_object_or_404(CafeTable, id=id)
    table.status = "AVAILABLE"
    table.save()

    messages.success(request, "Table marked as available")
    return redirect("tables_list")


@admin_required
def table_mark_cleaning(request, id):
    table = get_object_or_404(CafeTable, id=id)
    table.status = "CLEANING"
    table.save()

    messages.success(request, "Table marked as cleaning")
    return redirect("tables_list")

@admin_required
def cafe_settings(request):
    setting = CafeSetting.get_settings()

    if request.method == "POST":
        setting.cafe_name = request.POST.get("cafe_name")
        setting.address = request.POST.get("address")
        setting.phone = request.POST.get("phone")
        setting.gst_number = request.POST.get("gst_number")
        setting.invoice_footer = request.POST.get("invoice_footer")

        logo = request.FILES.get("logo")
        if logo:
            setting.logo = logo

        setting.save()

        messages.success(request, "Cafe settings updated successfully")
        return redirect("cafe_settings")

    return render(request, "dashboard/cafe_settings.html", {
        "setting": setting
    })

@admin_required
def backup_restore(request):
    db_path = settings.DATABASES["default"]["NAME"]

    if request.method == "POST":
        backup_file = request.FILES.get("backup_file")

        if not backup_file:
            messages.error(request, "Please upload backup file")
            return redirect("backup_restore")

        if not backup_file.name.endswith(".sqlite3") and not backup_file.name.endswith(".db"):
            messages.error(request, "Only .sqlite3 or .db files are allowed")
            return redirect("backup_restore")

        backup_dir = os.path.join(settings.BASE_DIR, "backups")
        os.makedirs(backup_dir, exist_ok=True)

        fs = FileSystemStorage(location=backup_dir)
        filename = fs.save(backup_file.name, backup_file)
        uploaded_path = os.path.join(backup_dir, filename)

        current_backup_path = os.path.join(backup_dir, "before_restore_db.sqlite3")
        shutil.copy2(db_path, current_backup_path)

        shutil.copy2(uploaded_path, db_path)

        messages.success(request, "Database restored successfully. Please restart server.")
        return redirect("backup_restore")

    return render(request, "dashboard/backup_restore.html")

# =========================
# COUNTER - ADMIN + COUNTER
# =========================
@counter_required
def razorpay_payment_page(request, id):
    order = get_object_or_404(Order, id=id)

    bill = Bill.objects.filter(order=order).first()

    if not bill:
        subtotal = order.total_amount
        tax_amount = Decimal("0.00")
        discount_amount = Decimal("0.00")
        grand_total = subtotal + tax_amount - discount_amount

        bill = Bill.objects.create(
            order=order,
            bill_number=Bill.generate_bill_number(),
            subtotal=subtotal,
            tax_amount=tax_amount,
            discount_amount=discount_amount,
            grand_total=grand_total,
            payment_status=order.payment_status,
        )

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    amount_paise = int(bill.grand_total * 100)

    razorpay_order = client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "payment_capture": 1,
    })

    bill.razorpay_order_id = razorpay_order["id"]
    bill.save()

    return render(request, "dashboard/razorpay_payment.html", {
        "order": order,
        "bill": bill,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "razorpay_order_id": razorpay_order["id"],
        "amount_paise": amount_paise,
    })


@csrf_exempt
def razorpay_verify_payment(request, id):
    order = get_object_or_404(Order, id=id)
    bill = get_object_or_404(Bill, order=order)

    if request.method == "POST":
        razorpay_order_id = request.POST.get("razorpay_order_id")
        razorpay_payment_id = request.POST.get("razorpay_payment_id")
        razorpay_signature = request.POST.get("razorpay_signature")

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        try:
            client.utility.verify_payment_signature({
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            })

            bill.razorpay_order_id = razorpay_order_id
            bill.razorpay_payment_id = razorpay_payment_id
            bill.razorpay_signature = razorpay_signature
            bill.payment_status = "PAID"
            bill.save()

            order.payment_status = "PAID"
            order.payment_method = "UPI"
            order.save()

            order.table.status = "CLEANING"
            order.table.save()

            messages.success(request, "Online payment successful")
            return redirect("billing_detail", id=order.id)

        except Exception:
            messages.error(request, "Payment verification failed")
            return redirect("billing_detail", id=order.id)

    return redirect("billing_detail", id=order.id)

@counter_required
def bill_generate(request, id):
    order = get_object_or_404(Order, id=id)

    tax_percent = Decimal(request.POST.get("tax_percent", "0"))
    discount_amount = Decimal(request.POST.get("discount_amount", "0"))
    service_charge = Decimal(request.POST.get("service_charge", "0"))

    subtotal = order.total_amount
    tax_amount = (subtotal * tax_percent) / Decimal("100")
    grand_total = subtotal + tax_amount + service_charge - discount_amount

    if grand_total < 0:
        messages.error(request, "Grand total cannot be negative")
        return redirect("billing_detail", id=order.id)

    bill = Bill.objects.filter(order=order).first()

    if bill:
        bill.subtotal = subtotal
        bill.tax_percent = tax_percent
        bill.tax_amount = tax_amount
        bill.service_charge = service_charge
        bill.discount_amount = discount_amount
        bill.grand_total = grand_total
        bill.payment_status = order.payment_status
        bill.save()

        messages.success(request, "Bill updated successfully")
    else:
        Bill.objects.create(
            order=order,
            bill_number=Bill.generate_bill_number(),
            subtotal=subtotal,
            tax_percent=tax_percent,
            tax_amount=tax_amount,
            service_charge=service_charge,
            discount_amount=discount_amount,
            grand_total=grand_total,
            payment_status=order.payment_status,
        )

        messages.success(request, "Bill generated successfully")

    return redirect("billing_detail", id=order.id)

@counter_required
def counter_orders(request):
    today = timezone.localdate()

    orders = Order.objects.select_related("table").prefetch_related("items__menu_item").filter(
        status__in=["PENDING", "ACCEPTED", "READY", "SERVED"]
    ).order_by("-created_at")

    pending_orders_count = Order.objects.filter(status="PENDING").count()
    ready_orders_count = Order.objects.filter(status="READY").count()
    unpaid_orders_count = Order.objects.filter(payment_status="UNPAID").count()
    paid_today_count = Order.objects.filter(
        payment_status="PAID",
        created_at__date=today
    ).count()

    today_sales = Bill.objects.filter(
        payment_status="PAID",
        created_at__date=today
    ).aggregate(total=Sum("grand_total"))["total"] or 0

    running_tables = CafeTable.objects.filter(
        status__in=["OCCUPIED", "BILL_PENDING"]
    ).count()

    context = {
        "orders": orders,
        "pending_orders_count": pending_orders_count,
        "ready_orders_count": ready_orders_count,
        "unpaid_orders_count": unpaid_orders_count,
        "paid_today_count": paid_today_count,
        "today_sales": today_sales,
        "running_tables": running_tables,
    }

    return render(request, "dashboard/counter_orders.html", context)


@counter_required
def order_accept(request, id):
    order = get_object_or_404(Order, id=id)

    if order.status == "PENDING":
        order.status = "ACCEPTED"
        order.save()
        messages.success(request, "Order accepted successfully")
    else:
        messages.error(request, "Only pending orders can be accepted")

    return redirect("counter_orders")


@counter_required
def order_served(request, id):
    order = get_object_or_404(Order, id=id)

    if order.status == "READY":
        order.status = "SERVED"
        order.save()

        order.table.status = "BILL_PENDING"
        order.table.save()

        messages.success(request, "Order marked as served")
    else:
        messages.error(request, "Only ready orders can be served")

    return redirect("counter_orders")


@counter_required
def order_paid(request, id):
    order = get_object_or_404(Order, id=id)

    payment_method = request.POST.get("payment_method", "CASH")

    if payment_method not in ["CASH", "UPI", "CARD"]:
        payment_method = "CASH"

    order.payment_status = "PAID"
    order.payment_method = payment_method
    order.save()

    order.table.status = "CLEANING"
    order.table.save()

    bill = Bill.objects.filter(order=order).first()

    if bill:
        bill.payment_status = "PAID"
        bill.save()

    messages.success(request, f"Order marked as paid by {payment_method}")
    return redirect("counter_orders")


@counter_required
def order_cancel(request, id):
    order = get_object_or_404(Order, id=id)

    if order.status != "SERVED":
        order.status = "CANCELLED"
        order.save()
        messages.success(request, "Order cancelled successfully")
    else:
        messages.error(request, "Served order cannot be cancelled")

    return redirect("counter_orders")


# =========================
# KITCHEN - ADMIN + KITCHEN
# =========================

@kitchen_required
def kitchen_orders(request):
    accepted_orders = Order.objects.select_related("table").prefetch_related("items__menu_item").filter(
        status="ACCEPTED"
    ).order_by("-created_at")

    preparing_orders = Order.objects.select_related("table").prefetch_related("items__menu_item").filter(
        status="PREPARING"
    ).order_by("-created_at")

    context = {
        "accepted_orders": accepted_orders,
        "preparing_orders": preparing_orders,
        "accepted_count": accepted_orders.count(),
        "preparing_count": preparing_orders.count(),
        "total_kitchen_orders": accepted_orders.count() + preparing_orders.count(),
    }

    return render(request, "dashboard/kitchen_orders.html", context)

@kitchen_required
def order_preparing(request, id):
    order = get_object_or_404(Order, id=id)

    if order.status == "ACCEPTED":
        order.status = "PREPARING"
        order.save()
        messages.success(request, "Order marked as preparing")
    else:
        messages.error(request, "Only accepted orders can be marked preparing")

    return redirect("kitchen_orders")


@kitchen_required
def order_ready(request, id):
    order = get_object_or_404(Order, id=id)

    if order.status == "PREPARING":
        order.status = "READY"
        order.save()
        messages.success(request, "Order marked as ready")
    else:
        messages.error(request, "Only preparing orders can be marked ready")

    return redirect("kitchen_orders")

@kitchen_required
def kot_print(request, id):
    order = get_object_or_404(
        Order.objects.select_related("table").prefetch_related("items__menu_item"),
        id=id
    )

    return render(request, "dashboard/kot_print.html", {
        "order": order
    })
# =========================
# BILLING - ADMIN + COUNTER
# =========================

@counter_required
def billing_detail(request, id):
    order = get_object_or_404(
        Order.objects.select_related("table").prefetch_related("items__menu_item"),
        id=id,
    )

    bill = Bill.objects.filter(order=order).first()
    setting = CafeSetting.get_settings()

    return render(request, "dashboard/billing_detail.html", {
        "order": order,
        "bill": bill,
        "setting": setting,
    })


@counter_required
def bill_generate(request, id):
    order = get_object_or_404(Order, id=id)

    if request.method != "POST":
        return redirect("billing_detail", id=order.id)

    tax_percent = Decimal(request.POST.get("tax_percent") or "0")
    service_charge = Decimal(request.POST.get("service_charge") or "0")
    discount_amount = Decimal(request.POST.get("discount_amount") or "0")

    subtotal = Decimal(order.total_amount)
    tax_amount = (subtotal * tax_percent) / Decimal("100")
    grand_total = subtotal + tax_amount + service_charge - discount_amount

    bill, created = Bill.objects.get_or_create(
        order=order,
        defaults={
            "bill_number": Bill.generate_bill_number(),
            "subtotal": subtotal,
            "payment_status": order.payment_status,
        }
    )

    bill.subtotal = subtotal
    bill.tax_percent = tax_percent
    bill.tax_amount = tax_amount
    bill.service_charge = service_charge
    bill.discount_amount = discount_amount
    bill.grand_total = grand_total
    bill.payment_status = order.payment_status
    bill.save()

    if created:
        messages.success(request, "Bill generated successfully")
    else:
        messages.success(request, "Bill updated successfully")

    return redirect("billing_detail", id=order.id)


@counter_required
def bill_mark_paid(request, id):
    order = get_object_or_404(Order, id=id)

    payment_method = request.POST.get("payment_method", "CASH")

    if payment_method not in ["CASH", "UPI", "CARD"]:
        payment_method = "CASH"

    order.payment_status = "PAID"
    order.payment_method = payment_method
    order.save()

    order.table.status = "CLEANING"
    order.table.save()

    bill = Bill.objects.filter(order=order).first()

    if bill:
        bill.payment_status = "PAID"
        bill.save()

    messages.success(request, f"Payment marked as paid by {payment_method}")
    return redirect("billing_detail", id=order.id)




def customer_menu_page(request, table_id):
    table = get_object_or_404(CafeTable, id=table_id, is_active=True)
    categories = Category.objects.filter(is_active=True).prefetch_related("menu_items")

    if request.method == "POST":
        customer_name = request.POST.get("customer_name")
        customer_mobile = request.POST.get("customer_mobile")
        note = request.POST.get("note")

        item_ids = request.POST.getlist("item_id")
        quantities = request.POST.getlist("quantity")

        selected_items = []

        for item_id, qty in zip(item_ids, quantities):
            try:
                qty = int(qty)
            except ValueError:
                qty = 0

            if qty > 0:
                menu_item = get_object_or_404(MenuItem, id=item_id, is_available=True)

                selected_items.append({
                    "menu_item": menu_item,
                    "quantity": qty,
                    "subtotal": menu_item.price * qty,
                })

        if not selected_items:
            messages.error(request, "Please select at least one item")
            return redirect("customer_menu", table_id=table.id)

        with transaction.atomic():
            order = Order.objects.create(
                table=table,
                customer_name=customer_name,
                customer_mobile=customer_mobile,
                note=note,
                status="PENDING",
                payment_status="UNPAID",
                payment_method="NONE",
                total_amount=Decimal("0.00"),
            )

            total = Decimal("0.00")

            for selected in selected_items:
                OrderItem.objects.create(
                    order=order,
                    menu_item=selected["menu_item"],
                    quantity=selected["quantity"],
                    price=selected["menu_item"].price,
                    subtotal=selected["subtotal"],
                )

                total += selected["subtotal"]

            order.total_amount = total
            order.save()

            table.status = "OCCUPIED"
            table.save()
        return redirect("customer_order_success", order_id=order.id)

    return render(request, "customer_menu.html", {
        "table": table,
        "categories": categories,
    })


def customer_order_success(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related("table").prefetch_related("items__menu_item"),
        id=order_id,
    )

    return render(request, "customer_order_success.html", {"order": order})


# =========================
# API DASHBOARD
# =========================

class DashboardStatsAPIView(APIView):
    permission_classes = [IsAdminUserProfile]

    def get(self, request):
        today = timezone.localdate()

        today_revenue = Bill.objects.filter(
            created_at__date=today,
            payment_status="PAID"
        ).aggregate(total=Sum("grand_total"))["total"] or 0

        return Response({
            "total_tables": CafeTable.objects.count(),
            "total_menu_items": MenuItem.objects.count(),
            "today_orders": Order.objects.filter(created_at__date=today).count(),
            "pending_orders": Order.objects.filter(status="PENDING").count(),
            "today_revenue": today_revenue,
            "total_staff": UserProfile.objects.count(),
        })


class TodayOrdersAPIView(APIView):
    permission_classes = [IsAdminUserProfile]

    def get(self, request):
        today = timezone.localdate()

        orders = Order.objects.select_related("table").prefetch_related(
            "items__menu_item"
        ).filter(created_at__date=today)

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)


class TodaySalesAPIView(APIView):
    permission_classes = [IsAdminUserProfile]

    def get(self, request):
        today = timezone.localdate()

        bills = Bill.objects.filter(created_at__date=today)

        return Response({
            "date": today,
            "total_sales": bills.aggregate(total=Sum("grand_total"))["total"] or 0,
            "paid_sales": bills.filter(payment_status="PAID").aggregate(total=Sum("grand_total"))["total"] or 0,
            "unpaid_sales": bills.filter(payment_status="UNPAID").aggregate(total=Sum("grand_total"))["total"] or 0,
            "total_bills": bills.count(),
        })