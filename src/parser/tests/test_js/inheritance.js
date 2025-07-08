// Class inheritance examples

// Base classes
class Animal {
    constructor(name) {
        this.name = name;
    }
    
    speak() {
        console.log(`${this.name} makes a sound`);
    }
}

class Vehicle {
    constructor(brand) {
        this.brand = brand;
    }
    
    start() {
        console.log(`${this.brand} vehicle started`);
    }
}

// Derived classes
class Dog extends Animal {
    constructor(name, breed) {
        super(name);
        this.breed = breed;
    }
    
    speak() {
        console.log(`${this.name} barks`);
    }
    
    wagTail() {
        console.log(`${this.name} wags tail`);
    }
}

class Cat extends Animal {
    constructor(name, color) {
        super(name);
        this.color = color;
    }
    
    speak() {
        console.log(`${this.name} meows`);
    }
}

class Car extends Vehicle {
    constructor(brand, model) {
        super(brand);
        this.model = model;
    }
    
    honk() {
        console.log(`${this.brand} ${this.model} honks`);
    }
}

// Multi-level inheritance
class SportsCar extends Car {
    constructor(brand, model, topSpeed) {
        super(brand, model);
        this.topSpeed = topSpeed;
    }
    
    accelerate() {
        console.log(`${this.brand} ${this.model} accelerates to ${this.topSpeed} mph`);
    }
}

// Exported class with inheritance
export class ElectricCar extends Car {
    constructor(brand, model, batteryCapacity) {
        super(brand, model);
        this.batteryCapacity = batteryCapacity;
    }
    
    charge() {
        console.log(`Charging ${this.brand} ${this.model}`);
    }
}

export { Animal, Dog, Cat, Vehicle, Car, SportsCar };