"""Class inheritance examples"""

from abc import ABC, abstractmethod
from typing import Optional

# Base classes
class Animal(ABC):
    """Abstract base class for animals"""
    
    def __init__(self, name: str, age: int):
        """Initialize animal"""
        self.name = name
        self.age = age
    
    @abstractmethod
    def speak(self) -> str:
        """Abstract method for animal sound"""
        pass
    
    def get_info(self) -> str:
        """Get animal information"""
        return f"{self.name} is {self.age} years old"

class Vehicle:
    """Base class for vehicles"""
    
    def __init__(self, brand: str, year: int):
        """Initialize vehicle"""
        self.brand = brand
        self.year = year
        self.is_running = False
    
    def start(self) -> str:
        """Start the vehicle"""
        self.is_running = True
        return f"{self.brand} vehicle started"
    
    def stop(self) -> str:
        """Stop the vehicle"""
        self.is_running = False
        return f"{self.brand} vehicle stopped"

# Derived classes
class Dog(Animal):
    """Dog class inheriting from Animal"""
    
    def __init__(self, name: str, age: int, breed: str):
        """Initialize dog"""
        super().__init__(name, age)
        self.breed = breed
    
    def speak(self) -> str:
        """Dog's speak implementation"""
        return f"{self.name} barks: Woof!"
    
    def wag_tail(self) -> str:
        """Dog-specific method"""
        return f"{self.name} wags tail happily"
    
    def fetch(self, item: str) -> str:
        """Dog fetches an item"""
        return f"{self.name} fetches the {item}"

class Cat(Animal):
    """Cat class inheriting from Animal"""
    
    def __init__(self, name: str, age: int, color: str):
        """Initialize cat"""
        super().__init__(name, age)
        self.color = color
    
    def speak(self) -> str:
        """Cat's speak implementation"""
        return f"{self.name} meows: Meow!"
    
    def purr(self) -> str:
        """Cat-specific method"""
        return f"{self.name} purrs contentedly"

class Car(Vehicle):
    """Car class inheriting from Vehicle"""
    
    def __init__(self, brand: str, year: int, model: str):
        """Initialize car"""
        super().__init__(brand, year)
        self.model = model
        self.fuel_level = 100
    
    def honk(self) -> str:
        """Car honks"""
        return f"{self.brand} {self.model} honks: Beep beep!"
    
    def drive(self, distance: float) -> str:
        """Drive the car"""
        if not self.is_running:
            # Call parent method
            self.start()
        
        fuel_used = distance * 0.1
        self.fuel_level -= fuel_used
        return f"Drove {distance} miles, fuel level: {self.fuel_level}%"

# Multi-level inheritance
class SportsCar(Car):
    """Sports car inheriting from Car"""
    
    def __init__(self, brand: str, year: int, model: str, top_speed: int):
        """Initialize sports car"""
        super().__init__(brand, year, model)
        self.top_speed = top_speed
    
    def accelerate(self) -> str:
        """Accelerate the sports car"""
        return f"{self.brand} {self.model} accelerates to {self.top_speed} mph!"
    
    def race_mode(self) -> str:
        """Enable race mode"""
        # Call parent method
        self.start()
        return f"{self.brand} {self.model} enters race mode!"

class ElectricCar(Car):
    """Electric car inheriting from Car"""
    
    def __init__(self, brand: str, year: int, model: str, battery_capacity: int):
        """Initialize electric car"""
        super().__init__(brand, year, model)
        self.battery_capacity = battery_capacity
        self.charge_level = 100
    
    def charge(self) -> str:
        """Charge the electric car"""
        self.charge_level = 100
        return f"Charging {self.brand} {self.model} to 100%"
    
    def drive(self, distance: float) -> str:
        """Override drive method for electric car"""
        if not self.is_running:
            self.start()
        
        charge_used = distance * 0.05
        self.charge_level -= charge_used
        return f"Drove {distance} miles, charge level: {self.charge_level}%"

# Multiple inheritance example
class FlyingCar(Car, ABC):
    """Flying car with multiple inheritance"""
    
    def __init__(self, brand: str, year: int, model: str, max_altitude: int):
        """Initialize flying car"""
        super().__init__(brand, year, model)
        self.max_altitude = max_altitude
        self.is_flying = False
    
    def take_off(self) -> str:
        """Take off"""
        # Call parent start method
        self.start()
        self.is_flying = True
        return f"{self.brand} {self.model} takes off!"
    
    def land(self) -> str:
        """Land the flying car"""
        self.is_flying = False
        return f"{self.brand} {self.model} lands safely"

# Factory function using inheritance
def create_animal(animal_type: str, name: str, age: int, **kwargs) -> Optional[Animal]:
    """Factory function to create animals"""
    if animal_type.lower() == "dog":
        breed = kwargs.get("breed", "Unknown")
        return Dog(name, age, breed)
    elif animal_type.lower() == "cat":
        color = kwargs.get("color", "Unknown")
        return Cat(name, age, color)
    return None

# Module-level usage
dog = create_animal("dog", "Buddy", 3, breed="Golden Retriever")
cat = create_animal("cat", "Whiskers", 2, color="Orange")

if dog:
    dog_sound = dog.speak()
    dog_info = dog.get_info()

if cat:
    cat_sound = cat.speak()
    cat_purr = cat.purr()

# Vehicle examples
sports_car = SportsCar("Ferrari", 2023, "F8", 340)
electric_car = ElectricCar("Tesla", 2023, "Model S", 100)

# Method calls
sports_car_start = sports_car.start()
sports_car_race = sports_car.race_mode()
electric_charge = electric_car.charge()
electric_drive = electric_car.drive(50)