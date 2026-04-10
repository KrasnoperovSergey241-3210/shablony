from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from .models import *
from django.contrib.auth.hashers import make_password, check_password
from datetime import datetime

def index(request):
    ingredients = Ingredient.objects.all()
    return render(request, 'index.html', {'ingredients': ingredients})

def register(request):
    if request.method == 'POST':
        name = request.POST['name']
        email = request.POST['email']
        password = make_password(request.POST['password'])
        if Client.objects.filter(email=email).exists():
            messages.error(request, 'Email уже занят')
        else:
            Client.objects.create(name=name, email=email, password=password)
            messages.success(request, 'Регистрация успешна!')
            return redirect('login')
    return render(request, 'register.html')

def login_view(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        try:
            user = Client.objects.get(email=email)
            if check_password(password, user.password):
                request.session['user_id'] = user.client_id
                request.session['role'] = 'client'
                return redirect('index')
        except Client.DoesNotExist:
            pass
        messages.error(request, 'Неверный email или пароль')
    return render(request, 'login.html')

def admin_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        try:
            admin = Admin.objects.get(username=username)
            if check_password(password, admin.password):
                request.session['user_id'] = admin.admin_id
                request.session['role'] = 'admin'
                return redirect('admin_dashboard')
        except Admin.DoesNotExist:
            pass
        messages.error(request, 'Неверные данные администратора')
    return render(request, 'admin_login.html')

def logout_view(request):
    request.session.flush()
    return redirect('index')

def constructor(request):
    ingredients = Ingredient.objects.all()
    if request.method == 'POST':
        base_id = int(request.POST['base'])
        sauce_id = int(request.POST['sauce'])
        cheese_id = int(request.POST['cheese'])
        topping_ids = list(map(int, request.POST.getlist('toppings')))[:8]

        base = Ingredient.objects.get(ingredient_id=base_id)
        sauce = Ingredient.objects.get(ingredient_id=sauce_id)
        cheese = Ingredient.objects.get(ingredient_id=cheese_id)

        price = base.price + sauce.price + cheese.price
        for tid in topping_ids:
            price += Ingredient.objects.get(ingredient_id=tid).price

        custom = CustomPizza.objects.create(
            client_id=request.session.get('user_id'),
            base=base,
            sauce=sauce,
            cheese=cheese,
            custom_price=price,
            is_favorite=request.POST.get('save_favorite') == 'on'
        )
        for tid in topping_ids:
            CustomPizzaIngredient.objects.create(
                custom_pizza=custom,
                ingredient_id=tid
            )
        messages.success(request, 'Кастомная пицца сохранена!')
        return redirect('favorites')

    return render(request, 'constructor.html', {'ingredients': ingredients})

def favorites(request):
    if 'user_id' not in request.session:
        return redirect('login')
    favs = CustomPizza.objects.filter(client_id=request.session['user_id'], is_favorite=True)
    return render(request, 'favorites.html', {'favorites': favs})

def create_order(request):
    if 'user_id' not in request.session:
        return redirect('login')
    if request.method == 'POST':
        delivery_type = request.POST['delivery_type']
        address = request.POST.get('address', 'Самовывоз')
        amount = 599.0

        order = Order.objects.create(
            client_id=request.session['user_id'],
            delivery_type=delivery_type,
            amount=amount,
            address=address
        )

        if delivery_type == 'delivery':
            free_courier = Courier.objects.filter(status='Свободен').first()
            if free_courier:
                order.courier = free_courier
                free_courier.status = 'Занят'
                free_courier.save()
                order.save()

        messages.success(request, f'Заказ #{order.order_id} создан!')
        return redirect('my_orders')
    return redirect('index')

def my_orders(request):
    if 'user_id' not in request.session:
        return redirect('login')
    orders = Order.objects.filter(client_id=request.session['user_id']).order_by('-created_at')
    return render(request, 'my_orders.html', {'orders': orders})

def admin_dashboard(request):
    if request.session.get('role') != 'admin':
        return redirect('admin_login')
    orders = Order.objects.all()
    ingredients = Ingredient.objects.all()
    return render(request, 'admin_dashboard.html', {'orders': orders, 'ingredients': ingredients})

def kitchen(request):
    orders = Order.objects.all().order_by('created_at')
    return render(request, 'kitchen.html', {'orders': orders})

def update_status(request, order_id):
    """API для умного конвейера"""
    order = get_object_or_404(Order, order_id=order_id)
    statuses = ['Принят', 'Готовится', 'В печи', 'Передан курьеру', 'Доставлен']
    try:
        idx = statuses.index(order.status)
        if idx < len(statuses) - 1:
            order.status = statuses[idx + 1]
            order.save()
            OrderStatusHistory.objects.create(order=order, status=order.status)
    except:
        pass
    return JsonResponse({'status': order.status, 'order_id': order.order_id})

def courier_view(request):
    couriers = Courier.objects.all()
    return render(request, 'courier.html', {'couriers': couriers})

def init_data(request):
    if not Ingredient.objects.exists():
        ingredients_data = [
            ("Тонкое тесто", 100, "base"),
            ("Толстое тесто", 150, "base"),
            ("Томатный соус", 50, "sauce"),
            ("Сливочный соус", 70, "sauce"),
            ("Моцарелла", 80, "cheese"),
            ("Чеддер", 90, "cheese"),
            ("Пепперони", 120, "topping"),
            ("Грибы", 90, "topping"),
            ("Ананас", 80, "topping"),
            ("Бекон", 110, "topping"),
        ]
        for name, price, cat in ingredients_data:
            Ingredient.objects.create(ingredient_name=name, price=price, category=cat)

        Courier.objects.create(name="Иван Иванов", phone="89161234567")
        Courier.objects.create(name="Пётр Сидоров", phone="89167654321")

        if not Admin.objects.exists():
            Admin.objects.create(username="admin", password=make_password("admin"))

        messages.success(request, 'Начальные данные загружены!')
    return redirect('index')