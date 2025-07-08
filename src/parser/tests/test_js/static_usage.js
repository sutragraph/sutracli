// Static usage examples
import { Calculator, MathUtils } from './calculator.js';

function useStaticMethods() {
    // Use static method from Calculator
    const result = Calculator.multiply(5, 3);
    
    // Use static method from MathUtils
    const instance = MathUtils.createInstance();
    
    return result;
}

class Helper {
    static formatNumber(num) {
        return num.toFixed(2);
    }
    
    static PI = 3.14159;
    
    processData(data) {
        // Use static method from same class
        const formatted = Helper.formatNumber(data);
        
        // Use static property from same class
        const pi = Helper.PI;
        
        // Use static method from other class
        const calculated = Calculator.multiply(data, pi);
        
        return { formatted, calculated };
    }
}

// Module-level static usage
const pi = Helper.PI;
const formatted = Helper.formatNumber(42);
const multiplied = Calculator.multiply(10, 20);

export { useStaticMethods, Helper };