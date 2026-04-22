from django.core.cache import cache
import json

class ConfigManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        self._config = {
            'delivery_free_threshold': 500,
            'delivery_base_fee': 100,
            'delivery_per_km_fee': 20,
            'max_delivery_fee': 300,
            'loyalty_points_rate': 0.01,
            'max_loyalty_discount_percent': 20,
            'min_order_amount': 200,
            'working_hours_start': 10,
            'working_hours_end': 23,
            'max_toppings': 8,
            'courier_assignment_timeout': 300
        }
    
    def get(self, key, default=None):
        return self._config.get(key, default)
    
    def set(self, key, value):
        self._config[key] = value
    
    def get_all(self):
        return self._config.copy()


class DatabaseConnectionPool:
    _instance = None
    _connections = []
    _max_connections = 10
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_connection(self):
        if len(self._connections) < self._max_connections:
            conn = self._create_connection()
            self._connections.append(conn)
            return conn
        return self._connections[0]
    
    def _create_connection(self):
        return {"id": len(self._connections) + 1, "active": True}
    
    def release_connection(self, conn):
        if conn in self._connections:
            conn["active"] = False


class EventBus:
    _instance = None
    _listeners = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def subscribe(self, event, callback):
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(callback)
    
    def publish(self, event, data):
        if event in self._listeners:
            for callback in self._listeners[event]:
                callback(data)


class CacheManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get(self, key):
        return cache.get(key)
    
    def set(self, key, value, timeout=300):
        cache.set(key, value, timeout)
    
    def delete(self, key):
        cache.delete(key)
    
    def clear(self):
        cache.clear()