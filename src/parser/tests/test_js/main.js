// Main file with imports
import { add, fetchData } from './example.js';
import Calculator from './example.js';
const utils = require('./utils.js');

// Use imported functions
console.log(add(5, 3));

// Use imported class
const calc = new Calculator();
calc.increment();

// Use required module
utils.logger.log('Application started');