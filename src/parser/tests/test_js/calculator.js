// Calculator with function calls
import { add } from './example.js';

function multiply(a, b) {
    return a * b;
}

function calculate(x, y) {
    // Call imported function
    const sum = add(x, y);
    
    // Call local function
    const product = multiply(x, y);
    
    // Call method
    console.log(`Sum: ${sum}, Product: ${product}`);
    
    return { sum, product };
}

function processArray(numbers) {
    // Call function with callback
    return numbers.map(num => multiply(num, 2));
}

class MathUtils {
    constructor() {
        this.history = [];
    }
    
    performCalculation(a, b) {
        // Call external function
        const result = calculate(a, b);
        
        // Call method on this
        this.saveToHistory(result);
        
        return result;
    }
    
    saveToHistory(result) {
        this.history.push(result);
    }
    
    static createInstance() {
        // Constructor call
        return new MathUtils();
    }
}

// Function calls at module level
const utils = MathUtils.createInstance();
const result = utils.performCalculation(10, 5);

// Chained method calls
const formatted = JSON.stringify(result).toUpperCase();

export { multiply, calculate, MathUtils };