from .models import Pizza, CustomPizza

class Cart:
    def __init__(self, request):
        self.request = request
        self.session = request.session
        cart = self.session.get('cart')
        if not cart:
            cart = {}
        self.cart = cart
    
    def add(self, item_type, item_id, quantity=1, price=0, name=''):
        key = f"{item_type}_{item_id}"
        
        if key in self.cart:
            self.cart[key]['quantity'] += quantity
        else:
            self.cart[key] = {
                'type': item_type,
                'id': item_id,
                'name': name,
                'price': price,
                'quantity': quantity
            }
        self.save()
    
    def remove(self, key):
        """Удаление товара из корзины"""
        if key in self.cart:
            del self.cart[key]
            self.save()
    
    def update_quantity(self, key, quantity):
        if key in self.cart and quantity > 0:
            self.cart[key]['quantity'] = quantity
            self.save()
    
    def get_items(self):
        items = []
        for key, item in self.cart.items():
            items.append({
                'key': key,
                'type': item['type'],
                'id': item['id'],
                'name': item['name'],
                'price': item['price'],
                'quantity': item['quantity'],
                'total': item['price'] * item['quantity']
            })
        return items
    
    def get_total(self):
        total = sum(item['price'] * item['quantity'] for item in self.cart.values())
        return total
    
    def get_count(self):
        count = sum(item['quantity'] for item in self.cart.values())
        return count
    
    def clear(self):
        self.cart = {}
        self.save()
    
    def save(self):
        self.session['cart'] = self.cart
        self.session.modified = True