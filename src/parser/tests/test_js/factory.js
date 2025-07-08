// Factory function that instantiates classes
import { Calculator } from './example.js';
import { MathUtils } from './calculator.js';

function createCalculator() {
    // Function instantiates Calculator class
    return new Calculator();
}

function createMathUtils(initialValue) {
    // Function instantiates MathUtils class with arguments
    const utils = new MathUtils();
    return utils;
}

class Factory {
    static createInstance(type) {
        // Static method instantiates different classes
        if (type === 'calc') {
            return new Calculator();
        } else if (type === 'utils') {
            return new MathUtils();
        }
        return null;
    }
}

export { createCalculator, createMathUtils, Factory };