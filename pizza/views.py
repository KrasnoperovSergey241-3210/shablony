from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from .models import *
from django.contrib.auth.hashers import make_password, check_password
from datetime import datetime
import json
from .optimizer import DeliveryOptimizer, PriceCalculator
from .strategies import OrderContext, StandardPricing, LoyaltyPricing, StandardDelivery, PickupStrategy
from .singletons import ConfigManager, EventBus, CacheManager

def index(request):
    ingredients = Ingredient.objects.all()
    pizzas = Pizza.objects.filter(is_available=True)
    total_clients = Client.objects.count()
    couriers_count = Courier.objects.count()
    pizzas_count = Pizza.objects.filter(is_available=True).count()
    
    context = {
        'ingredients': ingredients,
        'pizzas': pizzas,
        'total_clients': total_clients,
        'couriers_count': couriers_count,
        'pizzas_count': pizzas_count,
    }
    return render(request, 'index.html', context)

def register(request):
    if request.method == 'POST':
        name = request.POST['name']
        email = request.POST['email']
        password = make_password(request.POST['password'])
        if Client.objects.filter(email=email).exists():
            messages.error(request, 'Email уже занят')
        else:
            Client.objects.create(name=name, email=email, password=password)
            messages.success(request, 'Регистрация успешна')
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
                request.session['user_name'] = user.name
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
                request.session['user_name'] = admin.username
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
        
        cart = request.session.get('cart', {})
        cart_key = f"custom_{custom.custom_pizza_id}"
        cart[cart_key] = {
            'type': 'custom',
            'id': custom.custom_pizza_id,
            'name': f'Кастомная пицца #{custom.custom_pizza_id}',
            'price': price,
            'quantity': 1
        }
        request.session['cart'] = cart
        
        messages.success(request, 'Пицца добавлена в корзину')
        return redirect('cart')

    return render(request, 'constructor.html', {'ingredients': ingredients})

def favorites(request):
    if 'user_id' not in request.session:
        return redirect('login')
    favs = CustomPizza.objects.filter(client_id=request.session['user_id'], is_favorite=True)
    return render(request, 'favorites.html', {'favorites': favs})

def cart_view(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total = 0
    
    for key, item in cart.items():
        item_total = item['price'] * item['quantity']
        total += item_total
        cart_items.append({
            'key': key,
            'type': item['type'],
            'name': item['name'],
            'price': item['price'],
            'quantity': item['quantity'],
            'total': item_total
        })
    
    delivery_fee = 0  
    grand_total = total + delivery_fee
    
    context = {
        'cart_items': cart_items,
        'total': total,
        'delivery_fee': delivery_fee,
        'grand_total': grand_total,
        'free_delivery_threshold': 500,
        'cart_count': sum(item['quantity'] for item in cart.values())
    }
    return render(request, 'cart.html', context)

def add_to_cart(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        item_type = data.get('type')
        item_id = data.get('id')
        name = data.get('name')
        price = data.get('price')
        quantity = data.get('quantity', 1)
        
        cart = request.session.get('cart', {})
        key = f"{item_type}_{item_id}"
        
        if key in cart:
            cart[key]['quantity'] += quantity
        else:
            cart[key] = {
                'type': item_type,
                'id': item_id,
                'name': name,
                'price': price,
                'quantity': quantity
            }
        
        request.session['cart'] = cart
        cart_count = sum(item['quantity'] for item in cart.values())
        
        return JsonResponse({
            'success': True,
            'cart_count': cart_count,
            'message': f'{name} добавлен в корзину'
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def remove_from_cart(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        key = data.get('key')
        
        cart = request.session.get('cart', {})
        if key in cart:
            del cart[key]
            request.session['cart'] = cart
        
        cart_count = sum(item['quantity'] for item in cart.values())
        
        return JsonResponse({
            'success': True,
            'cart_count': cart_count
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def update_cart_quantity(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        key = data.get('key')
        quantity = data.get('quantity', 1)
        
        cart = request.session.get('cart', {})
        if key in cart and quantity > 0:
            cart[key]['quantity'] = quantity
            request.session['cart'] = cart
            item_total = cart[key]['price'] * quantity
            
            return JsonResponse({
                'success': True,
                'item_total': item_total
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def create_order(request):
    if 'user_id' not in request.session:
        return redirect('login')
    
    cart = request.session.get('cart', {})
    total = sum(item['price'] * item['quantity'] for item in cart.values())
    
    if total == 0:
        messages.warning(request, 'Корзина пуста')
        return redirect('constructor')
    
    if request.method == 'POST':
        delivery_type = request.POST.get('delivery_type')
        address = request.POST.get('address', '')
        
        if delivery_type == 'pickup':
            address = 'Самовывоз'
        
        config = ConfigManager()
        
        client = Client.objects.get(client_id=request.session['user_id'])
        
        if delivery_type == 'delivery':
            delivery_strategy = StandardDelivery()
        else:
            delivery_strategy = PickupStrategy()
        
        pricing_strategy = StandardPricing()
        
        order_context = OrderContext(pricing_strategy, delivery_strategy)
        
        if address and address != 'Самовывоз':
            distance_km = 5
        else:
            distance_km = 0
        
        final_total = order_context.calculate_total(
            total, 0, 1, distance_km, total
        )
        
        order = Order.objects.create(
            client_id=request.session['user_id'],
            delivery_type=delivery_type,
            amount=final_total,
            address=address
        )
        
        if delivery_type == 'delivery':
            free_courier = Courier.objects.filter(status='Свободен').first()
            if free_courier:
                order.courier = free_courier
                free_courier.status = 'Занят'
                free_courier.save()
                order.save()
        
        request.session['cart'] = {}
        
        event_bus = EventBus()
        event_bus.publish('order_created', {'order_id': order.order_id, 'client_id': client.client_id})
        
        messages.success(request, f'Заказ #{order.order_id} успешно создан')
        return redirect('my_orders')
    
    delivery_fee = 200 if total < 500 else 0
    grand_total = total + delivery_fee
    cart_items = []
    
    for key, item in cart.items():
        cart_items.append({
            'key': key,
            'name': item['name'],
            'price': item['price'],
            'quantity': item['quantity'],
            'total': item['price'] * item['quantity']
        })
    
    context = {
        'cart_items': cart_items,
        'total': total,
        'delivery_fee': delivery_fee,
        'grand_total': grand_total,
        'free_delivery_threshold': 500
    }
    return render(request, 'checkout.html', context)

def my_orders(request):
    if 'user_id' not in request.session:
        return redirect('login')
    orders = Order.objects.filter(client_id=request.session['user_id']).order_by('-created_at')
    return render(request, 'my_orders.html', {'orders': orders})

def admin_dashboard(request):
    if request.session.get('role') != 'admin':
        return redirect('admin_login')
    orders = Order.objects.all().order_by('-created_at')
    ingredients = Ingredient.objects.all()
    clients = Client.objects.all()
    couriers = Courier.objects.all()
    
    context = {
        'orders': orders,
        'ingredients': ingredients,
        'clients': clients,
        'couriers': couriers,
        'total_orders': orders.count(),
        'total_clients': clients.count(),
        'total_revenue': sum(o.amount for o in orders if o.status == 'Доставлен')
    }
    return render(request, 'admin_dashboard.html', context)

def kitchen(request):
    orders = Order.objects.all().order_by('created_at')
    return render(request, 'kitchen.html', {'orders': orders})

def update_status(request, order_id):
    """API для умного конвейера - обновление статуса заказа"""
    order = get_object_or_404(Order, order_id=order_id)
    
    if order.delivery_type == 'delivery':
        statuses = ['Принят', 'Готовится', 'В печи', 'Передан курьеру', 'Доставлен']
    else:
        statuses = ['Принят', 'Готовится', 'В печи', 'Доставлен']
    
    try:
        idx = statuses.index(order.status)
        if idx < len(statuses) - 1:
            new_status = statuses[idx + 1]
            order.status = new_status
            order.save()
            OrderStatusHistory.objects.create(order=order, status=order.status)
            
            if order.delivery_type == 'delivery':
                if order.status == 'Передан курьеру' and order.courier:
                    courier = order.courier
                    courier.status = 'В пути'
                    courier.save()
                elif order.status == 'Доставлен' and order.courier:
                    courier = order.courier
                    courier.status = 'Свободен'
                    courier.save()
            
            return JsonResponse({
                'status': order.status, 
                'order_id': order.order_id,
                'is_finished': False
            })
        else:
            return JsonResponse({
                'status': order.status, 
                'order_id': order.order_id,
                'is_finished': True
            })
    except ValueError:
        pass
    
    return JsonResponse({'status': order.status, 'order_id': order.order_id, 'is_finished': True})

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

        Courier.objects.create(name="Иван Иванов", phone="89161234567", status="Свободен")
        Courier.objects.create(name="Петр Сидоров", phone="89167654321", status="Свободен")
        Courier.objects.create(name="Сергей Смирнов", phone="89163456789", status="Свободен")

        if not Admin.objects.exists():
            admin = Admin.objects.create(username="admin", password=make_password("admin"))

        if not Pizza.objects.exists():
            Pizza.objects.create(
                name="Маргарита",
                description="Томатный соус, моцарелла, свежие помидоры, базилик",
                base_price=499,
                category="Классическая"
            )
            Pizza.objects.create(
                name="Пепперони",
                description="Пикантная пепперони, томатный соус, моцарелла",
                base_price=599,
                category="Мясная"
            )
            Pizza.objects.create(
                name="Четыре сыра",
                description="Моцарелла, пармезан, горгонзола, рикотта",
                base_price=649,
                category="Сырная"
            )
            Pizza.objects.create(
                name="Гавайская",
                description="Курица, ананас, моцарелла, томатный соус",
                base_price=579,
                category="Фруктовая"
            )
            Pizza.objects.create(
                name="Мясная",
                description="Бекон, пепперони, ветчина, курица, моцарелла",
                base_price=699,
                category="Мясная"
            )

        messages.success(request, 'Начальные данные загружены')
    return redirect('index')

def pizza_menu(request):
    pizzas = Pizza.objects.filter(is_available=True)
    return render(request, 'menu.html', {'pizzas': pizzas})

def optimize_route_api(request):
    if request.method == 'GET':
        pending_orders = Order.objects.filter(
            status='Передан курьеру',
            delivery_type='delivery'
        )[:5]
        
        if not pending_orders:
            return JsonResponse({'route': [], 'distance': 0, 'orders_count': 0})
        
        restaurant_coords = (55.751244, 37.618423)
        deliveries = []
        
        for order in pending_orders:
            deliveries.append({
                'order_id': order.order_id,
                'lat': 55.752244,
                'lng': 37.619423,
                'address': order.address
            })
        
        optimizer = DeliveryOptimizer()
        route, distance = optimizer.optimize_route(restaurant_coords, deliveries)
        
        return JsonResponse({
            'route': route,
            'distance': round(distance, 2),
            'orders_count': len(pending_orders)
        })
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

def get_config_api(request):
    if request.method == 'GET':
        config = ConfigManager()
        return JsonResponse(config.get_all())
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

def get_cart_count(request):
    cart = request.session.get('cart', {})
    count = sum(item.get('quantity', 1) for item in cart.values())
    return JsonResponse({'count': count})

def get_order_status(request, order_id):
    try:
        order = Order.objects.get(order_id=order_id)
        status_history = OrderStatusHistory.objects.filter(order=order).values('status', 'changed_at')
        
        return JsonResponse({
            'order_id': order.order_id,
            'status': order.status,
            'status_display': order.get_status_display(),
            'amount': order.amount,
            'delivery_type': order.delivery_type,
            'address': order.address,
            'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': order.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            'history': list(status_history)
        })
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)

def order_tracking(request, order_id):
    try:
        order = Order.objects.get(order_id=order_id)
        status_history = OrderStatusHistory.objects.filter(order=order).order_by('changed_at')
        
        if order.delivery_type == 'delivery':
            status_steps = [
                {'status': 'Принят', 'icon': '📋', 'description': 'Заказ принят'},
                {'status': 'Готовится', 'icon': '👨‍🍳', 'description': 'Пицца готовится'},
                {'status': 'В печи', 'icon': '🔥', 'description': 'Пицца в печи'},
                {'status': 'Передан курьеру', 'icon': '🛵', 'description': 'Курьер в пути'},
                {'status': 'Доставлен', 'icon': '✅', 'description': 'Заказ доставлен'},
            ]
        else:
            status_steps = [
                {'status': 'Принят', 'icon': '📋', 'description': 'Заказ принят'},
                {'status': 'Готовится', 'icon': '👨‍🍳', 'description': 'Пицца готовится'},
                {'status': 'В печи', 'icon': '🔥', 'description': 'Пицца в печи'},
                {'status': 'Доставлен', 'icon': '✅', 'description': 'Заказ готов к выдаче'},
            ]
        
        current_step = 0
        for i, step in enumerate(status_steps):
            if step['status'] == order.status:
                current_step = i
                break
        
        context = {
            'order': order,
            'status_history': status_history,
            'status_steps': status_steps,
            'current_step': current_step,
        }
        return render(request, 'order_tracking.html', context)
    except Order.DoesNotExist:
        messages.error(request, 'Заказ не найден')
        return redirect('index')

def cancel_order(request, order_id):
    if 'user_id' not in request.session:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        order = Order.objects.get(order_id=order_id, client_id=request.session['user_id'])
        
        cancel_allowed_statuses = ['Принят', 'Готовится', 'В печи']
        
        if order.status in cancel_allowed_statuses:
            order.status = 'Отменен'
            order.save()
            OrderStatusHistory.objects.create(order=order, status='Отменен', note='Отменен клиентом')
            
            if order.courier:
                courier = order.courier
                courier.status = 'Свободен'
                courier.save()
            
            messages.success(request, f'Заказ #{order_id} отменен')
            return JsonResponse({'success': True, 'message': 'Заказ отменен'})
        else:
            return JsonResponse({'error': 'Cannot cancel order in current status'}, status=400)
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)

def assign_courier_to_order(request, courier_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        order_id = data.get('order_id')
        
        try:
            courier = Courier.objects.get(courier_id=courier_id)
            order = Order.objects.get(order_id=order_id)
            
            if courier.status == 'Свободен' and order.status == 'В печи' and order.delivery_type == 'delivery':
                order.courier = courier
                order.status = 'Передан курьеру'
                order.save()
                
                courier.status = 'В пути'
                courier.save()
                
                OrderStatusHistory.objects.create(order=order, status='Передан курьеру', note=f'Курьер: {courier.name}')
                
                return JsonResponse({'success': True, 'message': f'Курьер {courier.name} назначен на заказ #{order_id}'})
            else:
                return JsonResponse({'error': 'Courier not available or order not ready'}, status=400)
        except (Courier.DoesNotExist, Order.DoesNotExist):
            return JsonResponse({'error': 'Courier or order not found'}, status=404)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

def sales_report(request):
    if request.session.get('role') != 'admin':
        return redirect('admin_login')
    
    from datetime import datetime, timedelta
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    orders = Order.objects.filter(created_at__gte=start_date, status='Доставлен')
    
    total_revenue = sum(o.amount for o in orders)
    total_orders = orders.count()
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
    
    daily_stats = []
    for i in range(30):
        day = end_date - timedelta(days=i)
        day_orders = orders.filter(created_at__date=day.date())
        daily_stats.append({
            'date': day.strftime('%Y-%m-%d'),
            'orders': day_orders.count(),
            'revenue': sum(o.amount for o in day_orders)
        })
    
    context = {
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'avg_order_value': avg_order_value,
        'daily_stats': daily_stats,
    }
    return render(request, 'reports/sales.html', context)

def popular_pizzas_report(request):
    if request.session.get('role') != 'admin':
        return redirect('admin_login')
    
    from django.db.models import Count, Sum
    
    popular_pizzas = Pizza.objects.annotate(
        order_count=Count('orderitem'),
        total_revenue=Sum('orderitem__price')
    ).filter(order_count__gt=0).order_by('-order_count')[:10]
    
    context = {
        'popular_pizzas': popular_pizzas,
    }
    return render(request, 'reports/popular_pizzas.html', context)