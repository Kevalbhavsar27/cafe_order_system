from django.urls import path
from . import views

urlpatterns = [


    # API
    path("stats/", views.DashboardStatsAPIView.as_view(), name="dashboard_stats"),
    path("today-orders/", views.TodayOrdersAPIView.as_view(), name="today_orders"),
    path("today-sales/", views.TodaySalesAPIView.as_view(), name="today_sales"),
    path("export/orders/", views.export_orders_csv, name="export_orders_csv"),
    path("export/bills/", views.export_bills_csv, name="export_bills_csv"),
    path("export/reports/", views.export_reports_csv, name="export_reports_csv"),
    # Django template admin pages
    path("", views.admin_dashboard, name="admin_dashboard"),
    path("staff-panel/", views.staff_panel, name="staff_panel"),
    path("kitchen-panel/", views.kitchen_panel, name="kitchen_panel"),
    
    path("reports/", views.reports_dashboard, name="reports_dashboard"),
    path("order-history/", views.order_history, name="order_history"),
    path("tables/<int:id>/available/", views.table_mark_available, name="table_mark_available"),
    path("tables/<int:id>/cleaning/", views.table_mark_cleaning, name="table_mark_cleaning"),
    path("kot/<int:id>/", views.kot_print, name="kot_print"),

    path("settings/", views.cafe_settings, name="cafe_settings"),
    
    path("staff/", views.staff_list, name="staff_list"),
    path("staff/add/", views.staff_add, name="staff_add"),
    path("staff/<int:id>/delete/", views.staff_delete, name="staff_delete"),
    path("staff/<int:id>/edit/", views.staff_edit, name="staff_edit"),

    path("tables/", views.tables_list, name="tables_list"),
    path("tables/add/", views.table_add, name="table_add"),
    path("tables/<int:id>/delete/", views.table_delete, name="table_delete"),
    path("tables/<int:id>/edit/", views.table_edit, name="table_edit"),
    path("tables/<int:id>/qr-print/", views.table_qr_print, name="table_qr_print"),

    path("menu/", views.menu_list, name="menu_list"),
    path("menu/add/", views.menu_add, name="menu_add"),
    path("menu/<int:id>/delete/", views.menu_delete, name="menu_delete"),
    path("menu/<int:id>/edit/", views.menu_edit, name="menu_edit"),
    path("menu/<int:id>/toggle/", views.menu_toggle, name="menu_toggle"),

    path("counter-orders/", views.counter_orders, name="counter_orders"),
    path("counter-orders/<int:id>/accept/", views.order_accept, name="order_accept"),
    path("counter-orders/<int:id>/served/", views.order_served, name="order_served"),
    path("counter-orders/<int:id>/paid/", views.order_paid, name="order_paid"),
    path("counter-orders/<int:id>/cancel/", views.order_cancel, name="order_cancel"),

    path("kitchen-orders/", views.kitchen_orders, name="kitchen_orders"),
    path("kitchen-orders/<int:id>/preparing/", views.order_preparing, name="order_preparing"),
    path("kitchen-orders/<int:id>/ready/", views.order_ready, name="order_ready"),

    path("billing/<int:id>/", views.billing_detail, name="billing_detail"),
    path("billing/<int:id>/generate/", views.bill_generate, name="bill_generate"),
    path("billing/<int:id>/paid/", views.bill_mark_paid, name="bill_mark_paid"),

    path("billing/<int:id>/razorpay/", views.razorpay_payment_page, name="razorpay_payment_page"),
    path("billing/<int:id>/razorpay/verify/", views.razorpay_verify_payment, name="razorpay_verify_payment"),

    path("categories/", views.category_list, name="category_list"),
    path("categories/add/", views.category_add, name="category_add"),
    path("categories/<int:id>/delete/", views.category_delete, name="category_delete"),
    path("categories/<int:id>/toggle/", views.category_toggle, name="category_toggle"),
    path("categories/<int:id>/edit/", views.category_edit, name="category_edit"),

    path("backup/", views.backup_restore, name="backup_restore"),
    path("backup/download/", views.download_backup, name="download_backup"),

]