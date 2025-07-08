// Example JavaScript file for testing

// Regular function
export function add(a, b) {
    return a + b;
}

// Async function
export async function fetchData(url) {
    const response = await fetch(url);
    return await response.json();
}

// Class with methods
class Calculator {
    constructor() {
        this.value = 0;
    }

    increment() {
        this.value++;
        return this.value;
    }

    // Static method
    static multiply(a, b) {
        return a * b;
    }
}

// Module exports
module.exports = {
    Calculator,
    utils: {
        formatDate: (date) => date.toISOString(),
        logger: {
            log: (message) => console.log(`[LOG] ${message}`),
            error: (message) => console.error(`[ERROR] ${message}`)
        }
    }
};

// Top-level await (ES modules)
const config = await Promise.resolve({ env: 'development' });
console.log(`Running in ${config.env} mode`);
