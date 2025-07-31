/**
 * Module 1 for testing TypeScript relationship extraction.
 */

// Import from another module
import { function2 } from './utils/module2';

/**
 * Example function
 */
export function function1(): string {
  console.log('Function 1 from module1');
  function2();
  return 'Result from function1';
}

/**
 * Default export class
 */
export default class DefaultClass {
  method(): void {
    console.log('Method from DefaultClass');
  }
}