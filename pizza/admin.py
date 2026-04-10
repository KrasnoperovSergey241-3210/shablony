from django.contrib import admin
from .models import Ingredient, Order, CustomPizza, Courier

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('ingredient_name', 'price', 'is_available', 'category')
    list_editable = ('price', 'is_available')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'client', 'status', 'delivery_type')
    list_filter = ('status', 'delivery_type')

admin.site.register(CustomPizza)
admin.site.register(Courier)