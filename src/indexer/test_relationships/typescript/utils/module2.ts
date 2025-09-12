/**
 * Module 2 for testing TypeScript relationship extraction.
 */

// Import from parent directory
import { function1 } from '../module1';

/**
 * Example function
 */
export function function2(): void {
  console.log('Function 2 from module2');
  console.log(`Current time: ${new Date().toISOString()}`);
}

/**
 * Side effect when imported
 */
console.log('Module 2 loaded');
