def cart_count(request):
    cart = request.session.get('cart', {})
    count = sum(item.get('quantity', 1) for item in cart.values())
    return {'cart_count': count}