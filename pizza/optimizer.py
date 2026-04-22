import math
import heapq
from django.db import models

class DeliveryOptimizer:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def haversine_distance(self, lat1, lng1, lat2, lng2):
        R = 6371
        lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.asin(min(1, math.sqrt(a)))
        return R * c
    
    def calculate_distance_matrix(self, points):
        n = len(points)
        matrix = [[0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i != j:
                    matrix[i][j] = self.haversine_distance(
                        points[i][0], points[i][1],
                        points[j][0], points[j][1]
                    )
        return matrix
    
    def a_star_search(self, start, goals, distance_matrix):
        open_set = [(0, start, [start])]
        closed_set = set()
        
        while open_set:
            cost, current, path = heapq.heappop(open_set)
            
            if current in closed_set:
                continue
            
            if all(goal in path for goal in goals):
                return path, cost
            
            closed_set.add(current)
            
            for neighbor in range(len(distance_matrix)):
                if neighbor not in path:
                    new_cost = cost + distance_matrix[current][neighbor]
                    remaining_goals = [g for g in goals if g not in path]
                    if remaining_goals:
                        heuristic = min(distance_matrix[neighbor][g] for g in remaining_goals)
                    else:
                        heuristic = 0
                    heapq.heappush(open_set, (new_cost + heuristic, neighbor, path + [neighbor]))
        
        return None, float('inf')
    
    def optimize_route(self, restaurant_coords, deliveries):
        if not deliveries:
            return [], 0
        
        points = [restaurant_coords]
        for d in deliveries:
            points.append((d['lat'], d['lng']))
        
        distance_matrix = self.calculate_distance_matrix(points)
        delivery_indices = list(range(1, len(points)))
        route, total_distance = self.a_star_search(0, delivery_indices, distance_matrix)
        
        optimized_route = []
        for idx in route:
            if idx == 0:
                optimized_route.append({'type': 'restaurant', 'coords': points[idx]})
            else:
                optimized_route.append({
                    'type': 'delivery',
                    'coords': points[idx],
                    'order_id': deliveries[idx-1].get('order_id'),
                    'address': deliveries[idx-1].get('address')
                })
        
        return optimized_route, total_distance
    
    def find_nearest_courier(self, restaurant_coords, couriers):
        if not couriers:
            return None, float('inf')
        
        nearest = None
        min_distance = float('inf')
        
        for courier in couriers:
            if courier.status == 'Свободен':
                dist = self.haversine_distance(
                    restaurant_coords[0], restaurant_coords[1],
                    courier.current_lat, courier.current_lng
                )
                if dist < min_distance:
                    min_distance = dist
                    nearest = courier
        
        return nearest, min_distance


class PriceCalculator:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def calculate_pizza_price(self, base_price, toppings_price, quantity=1, discount_percent=0):
        total = (base_price + toppings_price) * quantity
        if discount_percent > 0:
            total = total * (1 - discount_percent / 100)
        return round(total, 2)
    
    def calculate_delivery_fee(self, total_amount, distance_km):
        if total_amount >= 500:
            return 0
        base_fee = 100
        distance_fee = int(distance_km * 20)
        return min(base_fee + distance_fee, 300)