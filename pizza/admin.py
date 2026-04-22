from django.contrib import admin
from .models import Ingredient, Order, CustomPizza, Courier, Pizza, Client, Admin, OrderStatusHistory, CartItem

@admin.register(Pizza)
class PizzaAdmin(admin.ModelAdmin):
    list_display = ('pizza_id', 'name', 'base_price', 'category', 'is_available')
    list_editable = ('base_price', 'is_available')
    list_filter = ('category', 'is_available')
    search_fields = ('name', 'description')
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'base_price', 'category')
        }),
        ('Доступность', {
            'fields': ('is_available',)
        }),
    )

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('ingredient_id', 'ingredient_name', 'price', 'is_available', 'category')
    list_display_links = ('ingredient_id', 'ingredient_name')
    list_editable = ('price', 'is_available')
    list_filter = ('category', 'is_available')
    search_fields = ('ingredient_name',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'client', 'status', 'delivery_type', 'amount', 'created_at')
    list_filter = ('status', 'delivery_type', 'created_at')
    search_fields = ('order_id', 'client__name', 'address')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(CustomPizza)
class CustomPizzaAdmin(admin.ModelAdmin):
    list_display = ('custom_pizza_id', 'client', 'custom_price', 'is_favorite', 'created_at')
    list_filter = ('is_favorite', 'created_at')
    search_fields = ('custom_pizza_id', 'client__name')

@admin.register(Courier)
class CourierAdmin(admin.ModelAdmin):
    list_display = ('courier_id', 'name', 'phone', 'status')
    list_editable = ('status',)
    list_filter = ('status',)
    search_fields = ('name', 'phone')

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('client_id', 'name', 'email', 'phone', 'registration_date', 'is_active')
    list_editable = ('is_active',)
    list_filter = ('is_active', 'registration_date')
    search_fields = ('name', 'email', 'phone')
    readonly_fields = ('registration_date',)

@admin.register(Admin)
class AdminAdmin(admin.ModelAdmin):
    list_display = ('admin_id', 'username', 'permissions')
    search_fields = ('username',)

@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('status_history_id', 'order', 'status', 'changed_at')
    list_filter = ('status', 'changed_at')
    readonly_fields = ('changed_at',)

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart_item_id', 'client', 'session_key', 'quantity', 'added_at')
    list_filter = ('added_at',)
    search_fields = ('session_key', 'client__name')

admin.site.site_header = 'PizzaFlow Административная панель'
admin.site.site_title = 'PizzaFlow Admin'
admin.site.index_title = 'Управление пиццерией'