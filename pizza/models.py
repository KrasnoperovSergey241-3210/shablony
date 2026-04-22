from django.db import models
from django.utils import timezone
from transitions import Machine

class Client(models.Model):
    client_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    password = models.CharField(max_length=255)
    registration_date = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    loyalty_points = models.IntegerField(default=0)

    def __str__(self):
        return self.name

class Admin(models.Model):
    admin_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=255)
    permissions = models.CharField(max_length=255, default="full")

    def __str__(self):
        return self.username

class Ingredient(models.Model):
    ingredient_id = models.AutoField(primary_key=True)
    ingredient_name = models.CharField(max_length=100)
    price = models.FloatField()
    is_available = models.BooleanField(default=True)
    unit = models.CharField(max_length=20, default="шт")
    category = models.CharField(max_length=30, choices=[
        ('base', 'Основа'), ('sauce', 'Соус'), ('cheese', 'Сыр'), ('topping', 'Топпинг')
    ])

    def __str__(self):
        return f"{self.ingredient_name} ({self.price} ₽)"

class Pizza(models.Model):
    pizza_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    base_price = models.FloatField()
    is_available = models.BooleanField(default=True)
    category = models.CharField(max_length=50, default="Классическая")
    ingredients = models.ManyToManyField(Ingredient, through='PizzaIngredient')

    def __str__(self):
        return self.name

class PizzaIngredient(models.Model):
    pizza = models.ForeignKey(Pizza, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

class CustomPizza(models.Model):
    custom_pizza_id = models.AutoField(primary_key=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True)
    base = models.ForeignKey(Ingredient, on_delete=models.SET_NULL, null=True, related_name='base_pizzas')
    sauce = models.ForeignKey(Ingredient, on_delete=models.SET_NULL, null=True, related_name='sauce_pizzas')
    cheese = models.ForeignKey(Ingredient, on_delete=models.SET_NULL, null=True, related_name='cheese_pizzas')
    custom_price = models.FloatField()
    is_favorite = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Кастомная пицца #{self.custom_pizza_id}"

class CustomPizzaIngredient(models.Model):
    custom_pizza = models.ForeignKey(CustomPizza, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)

class Order(models.Model):
    STATUS_CHOICES = [
        ('Принят', 'Принят'),
        ('Готовится', 'Готовится'),
        ('В печи', 'В печи'),
        ('Передан курьеру', 'Передан курьеру'),
        ('Доставлен', 'Доставлен'),
        ('Отменен', 'Отменен'),
    ]
    
    order_id = models.AutoField(primary_key=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    courier = models.ForeignKey('Courier', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Принят')
    delivery_type = models.CharField(max_length=20, choices=[('delivery', 'Доставка'), ('pickup', 'Самовывоз')])
    amount = models.FloatField()
    address = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._setup_state_machine()
    
    def _setup_state_machine(self):
        states = ['Принят', 'Готовится', 'В печи', 'Передан курьеру', 'Доставлен', 'Отменен']
        self.machine = Machine(model=self, states=states, initial=self.status or 'Принят')
        
        self.machine.add_transition('start_cook', 'Принят', 'Готовится')
        self.machine.add_transition('put_in_oven', 'Готовится', 'В печи')
        self.machine.add_transition('give_to_courier', 'В печи', 'Передан курьеру')
        self.machine.add_transition('deliver', 'Передан курьеру', 'Доставлен')
        self.machine.add_transition('cancel', ['Принят', 'Готовится', 'В печи'], 'Отменен')
    
    def can_cancel(self):
        return self.state in ['Принят', 'Готовится', 'В печи']
    
    def get_status_display_custom(self):
        status_display = {
            'Принят': 'Заказ принят',
            'Готовится': 'Пицца готовится',
            'В печи': 'Пицца в печи',
            'Передан курьеру': 'Курьер в пути',
            'Доставлен': 'Заказ доставлен',
            'Отменен': 'Заказ отменен'
        }
        return status_display.get(self.state, self.state)
    
    def __str__(self):
        return f"Заказ #{self.order_id} — {self.get_status_display_custom()}"

class Courier(models.Model):
    courier_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    status = models.CharField(max_length=30, default="Свободен")

    def __str__(self):
        return self.name

class OrderStatusHistory(models.Model):
    status_history_id = models.AutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    changed_at = models.DateTimeField(default=timezone.now)

class CartItem(models.Model):
    cart_item_id = models.AutoField(primary_key=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=100, blank=True)
    pizza = models.ForeignKey(Pizza, on_delete=models.CASCADE, null=True, blank=True)
    custom_pizza = models.ForeignKey(CustomPizza, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.IntegerField(default=1)
    added_at = models.DateTimeField(default=timezone.now)
    
    def get_price(self):
        if self.pizza:
            return self.pizza.base_price * self.quantity
        elif self.custom_pizza:
            return self.custom_pizza.custom_price * self.quantity
        return 0