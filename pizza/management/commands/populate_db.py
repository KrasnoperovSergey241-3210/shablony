import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.hashers import make_password

from faker import Faker

from pizza.models import (
    Client, Admin, Ingredient, CustomPizza,
    CustomPizzaIngredient, Order, Courier, OrderStatusHistory
)


class Command(BaseCommand):
    help = 'Автоматическое заполнение БД тестовыми данными через Faker'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Очистить ВСЮ БД перед заполнением',
        )

    def handle(self, *args, **options):
        clear = options['clear']
        fake = Faker('ru_RU')

        if clear:
            self.stdout.write(self.style.WARNING('Очистка базы данных...'))
            OrderStatusHistory.objects.all().delete()
            Order.objects.all().delete()
            CustomPizzaIngredient.objects.all().delete()
            CustomPizza.objects.all().delete()
            Client.objects.all().delete()
            Courier.objects.all().delete()
            Ingredient.objects.all().delete()
            Admin.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('База данных полностью очищена.'))

        if not Admin.objects.filter(username='admin').exists():
            Admin.objects.create(
                username='admin',
                password=make_password('admin'),
                permissions='full'
            )
            self.stdout.write(self.style.SUCCESS(
                'Создан суперпользователь: admin / admin'
            ))

        test_password = make_password('test123')

        if Ingredient.objects.count() == 0:
            self.stdout.write('Создаём 60 ингредиентов...')
            categories = ['base', 'sauce', 'cheese', 'topping']
            for cat in categories:
                for _ in range(15):
                    name = f"{fake.word().capitalize()} {fake.word().capitalize()}"
                    price = round(random.uniform(40 if cat in ['sauce', 'cheese'] else 80, 220), 2)
                    Ingredient.objects.create(
                        ingredient_name=name,
                        price=price,
                        is_available=random.random() > 0.15,
                        unit=random.choice(['шт', 'г', 'мл']),
                        category=cat,
                    )
            self.stdout.write(self.style.SUCCESS(f'Создано {Ingredient.objects.count()} ингредиентов'))

        bases = list(Ingredient.objects.filter(category='base'))
        sauces = list(Ingredient.objects.filter(category='sauce'))
        cheeses = list(Ingredient.objects.filter(category='cheese'))
        toppings = list(Ingredient.objects.filter(category='topping'))

        if Courier.objects.count() == 0:
            self.stdout.write('Создаём 20 курьеров...')
            for _ in range(20):
                Courier.objects.create(
                    name=fake.name(),
                    phone=fake.phone_number(),
                    status=random.choice(['Свободен', 'Занят']),
                )
            self.stdout.write(self.style.SUCCESS(f'Создано {Courier.objects.count()} курьеров'))

        couriers = list(Courier.objects.all())

        if Client.objects.count() == 0:
            self.stdout.write('Создаём 60 клиентов (пароль для всех: test123)...')
            for i in range(60):
                Client.objects.create(
                    name=fake.name(),
                    email=fake.unique.email(),
                    phone=fake.phone_number() if random.random() > 0.4 else '',
                    password=test_password,
                    registration_date=timezone.make_aware(fake.date_time_this_decade()),
                    is_active=random.random() > 0.1,
                )
                if (i + 1) % 20 == 0:
                    self.stdout.write(f'   ... {i+1}/60 клиентов')
            self.stdout.write(self.style.SUCCESS(f'Создано {Client.objects.count()} клиентов'))

        clients = list(Client.objects.all())

        if CustomPizza.objects.count() == 0:
            self.stdout.write('Создаём кастомные пиццы (5 на клиента)...')
            for client in clients:
                for _ in range(5):
                    base = random.choice(bases)
                    sauce = random.choice(sauces)
                    cheese = random.choice(cheeses)
                    selected_toppings = random.sample(toppings, k=random.randint(3, 5))

                    price = base.price + sauce.price + cheese.price + sum(t.price for t in selected_toppings)

                    custom = CustomPizza.objects.create(
                        client=client,
                        base=base,
                        sauce=sauce,
                        cheese=cheese,
                        custom_price=round(price, 2),
                        is_favorite=random.choice([True, False]),
                    )

                    for topping in selected_toppings:
                        CustomPizzaIngredient.objects.create(
                            custom_pizza=custom,
                            ingredient=topping,
                        )
            self.stdout.write(self.style.SUCCESS(f'Создано {CustomPizza.objects.count()} кастомных пицц'))

        if Order.objects.count() == 0:
            self.stdout.write('Создаём заказы (5 на клиента)...')
            status_list = ['Принят', 'Готовится', 'В печи', 'Передан курьеру', 'Доставлен']

            for client in clients:
                for _ in range(5):
                    delivery_type = random.choice(['delivery', 'pickup'])
                    address = fake.address() if delivery_type == 'delivery' else 'Самовывоз'
                    amount = round(random.uniform(499, 2999), 2)
                    courier = random.choice(couriers) if random.random() < 0.6 and couriers else None

                    status_idx = random.randint(0, len(status_list) - 1)
                    status = status_list[status_idx]

                    order = Order.objects.create(
                        client=client,
                        courier=courier,
                        status=status,
                        delivery_type=delivery_type,
                        amount=amount,
                        address=address,
                    )

                    for i in range(status_idx + 1):
                        OrderStatusHistory.objects.create(
                            order=order,
                            status=status_list[i],
                            changed_at=timezone.now() - timedelta(minutes=random.randint(10, 180 * (i + 1))),
                        )
            self.stdout.write(self.style.SUCCESS(f'Создано {Order.objects.count()} заказов'))

        self.stdout.write(self.style.SUCCESS(
            '\nЗаполнение БД завершено!\n'
            '   Клиенты: 60 (пароль для всех — test123)\n'
            '   Кастомные пиццы: ~300\n'
            '   Заказы: 300\n'
            '   Ингредиенты: 60\n'
            '   Курьеры: 20\n'
            '   Админ: admin / admin\n\n'
            'Теперь можно логиниться как клиент с email из БД и паролем test123'
        ))