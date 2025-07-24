/**
 * Main module for testing TypeScript relationship extraction.
 */

// Standard imports
import { function1 } from './module1';
import * as module2 from './utils/module2';

// Default import
import DefaultClass from './module1';

// Side-effect import
import './utils/module2';

// Dynamic import
const loadModule = async () => {
  const dynamicModule = await import('./module1');
  return dynamicModule.function1();
};

// CommonJS require (TypeScript allows this syntax)
const requiredModule = require('./utils/module2');

/**
 * Main function
 */
function main() {
  console.log('Main module');
  function1();
  module2.function2();
  
  const instance = new DefaultClass();
  instance.method();
  
  loadModule().then(result => console.log(result));
  
  requiredModule.function2();
}

main();