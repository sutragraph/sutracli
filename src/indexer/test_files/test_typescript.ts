/**
 * Comprehensive TypeScript test file for AST parser testing.
 * Contains examples of all extractable code constructs.
 */

import { readFileSync } from 'fs';
import { join } from 'path';
import * as util from 'util';
import axios, { AxiosResponse } from 'axios';
import { EventEmitter } from 'events';
import type { IncomingMessage } from 'http';

// ============================================================================
// ENUMS - Should be extracted as BlockType.ENUM
// ============================================================================

enum Status {
    PENDING = "pending",
    ACTIVE = "active",
    INACTIVE = "inactive"
}

enum Priority {
    LOW = 1,
    MEDIUM = 2,
    HIGH = 3
}

enum Color {
    RED,
    GREEN,
    BLUE
}

const enum ConstEnum {
    VALUE1 = "value1",
    VALUE2 = "value2"
}

enum ComputedEnum {
    FIRST = 1,
    SECOND = FIRST * 2,
    THIRD = SECOND + 1
}

// ============================================================================
// VARIABLES - Should be extracted as BlockType.VARIABLE
// ============================================================================

// Simple variable declarations
const DATABASE_URL: string = "postgresql://localhost/mydb";
const API_VERSION = "v1.0";
let MAX_RETRIES: number = 3;
var IS_DEBUG = true;

// Destructuring assignments
const { name, age, city } = { name: "John", age: 30, city: "NYC" };
const [first, second, ...rest] = [1, 2, 3, 4, 5];

// Object destructuring with renaming
const { name: userName, age: userAge } = { name: "Alice", age: 25 };

// Nested destructuring
const {
    user: { profile: { email } },
    settings: { theme }
} = {
    user: { profile: { email: "test@example.com" } },
    settings: { theme: "dark" }
};

// Array destructuring with defaults
const [x = 0, y = 0, z = 0] = [1, 2];

// Complex object
const CONFIG = {
    host: "localhost",
    port: 5432,
    debug: true,
    features: {
        auth: true,
        logging: false
    }
};

// Type assertions
const someValue: any = "hello";
const strLength = (someValue as string).length;

// Generic variables
const items: Array<string> = ["item1", "item2"];
const map: Map<string, number> = new Map();

// ============================================================================
// FUNCTIONS - Should be extracted as BlockType.FUNCTION
// ============================================================================

// Regular function declaration
function simpleFunction(): string {
    return "Hello, World!";
}

// Function with parameters and return type
function functionWithParams(name: string, age: number = 25): string {
    return `Name: ${name}, Age: ${age}`;
}

// Function with rest parameters
function functionWithRestParams(first: string, ...rest: string[]): string[] {
    return [first, ...rest];
}

// Async function
async function asyncFunction(): Promise<string> {
    await new Promise(resolve => setTimeout(resolve, 1000));
    return "Async result";
}

// Async function with parameters
async function asyncFunctionWithParams(url: string, timeout: number = 30): Promise<any> {
    const response = await fetch(url);
    return response.json();
}

// Generator function
function* generatorFunction(): Generator<number, void, unknown> {
    for (let i = 0; i < 5; i++) {
        yield i;
    }
}

// Async generator function
async function* asyncGeneratorFunction(): AsyncGenerator<number, void, unknown> {
    for (let i = 0; i < 3; i++) {
        await new Promise(resolve => setTimeout(resolve, 100));
        yield i;
    }
}

// Function with generic parameters
function genericFunction<T>(item: T): T {
    return item;
}

// Function with multiple generics
function multipleGenerics<T, U>(first: T, second: U): [T, U] {
    return [first, second];
}

// Function with conditional types
function conditionalFunction<T extends string | number>(
    value: T
): T extends string ? string : number {
    return value as any;
}

// Arrow function assignments
const arrowFunction = () => "Arrow function";
const arrowWithParams = (x: number, y: number) => x + y;
const asyncArrowFunction = async () => await Promise.resolve("Async arrow");
const genericArrowFunction = <T>(item: T): T => item;

// Arrow function with complex return type
const complexArrowFunction = (data: any[]): { processed: any[], count: number } => ({
    processed: data.map(item => ({ ...item, processed: true })),
    count: data.length
});

// Function expressions
const functionExpression = function(name: string): string {
    return `Hello, ${name}`;
};

const namedFunctionExpression = function namedFunc(x: number): number {
    return x * 2;
};

// Higher-order functions
function higherOrderFunction(callback: (x: number) => number): (x: number) => number {
    return (x: number) => callback(x * 2);
}

// ============================================================================
// CLASSES - Should be extracted as BlockType.CLASS
// ============================================================================

class SimpleClass {
    private value: number;

    constructor() {
        this.value = 42;
    }

    getValue(): number {
        return this.value;
    }
}

class ClassWithMethods {
    private _name: string;
    private _privateValue: number = 100;

    constructor(name: string) {
        this._name = name;
    }

    public getName(): string {
        return this._name;
    }

    private getPrivateValue(): number {
        return this._privateValue;
    }

    protected getProtectedValue(): number {
        return this._privateValue;
    }

    static staticMethod(): string {
        return "Static result";
    }

    async asyncMethod(): Promise<string> {
        await new Promise(resolve => setTimeout(resolve, 100));
        return "Async method result";
    }

    get nameProperty(): string {
        return this._name;
    }

    set nameProperty(value: string) {
        this._name = value;
    }

    // Method with generic
    genericMethod<T>(item: T): T {
        return item;
    }
}

// Class with inheritance
class InheritedClass extends ClassWithMethods {
    private value: number;

    constructor(name: string, value: number) {
        super(name);
        this.value = value;
    }

    getInfo(): string {
        return `${this.getName()}: ${this.value}`;
    }

    // Override method
    getName(): string {
        return `Override: ${super.getName()}`;
    }
}

// Abstract class
abstract class AbstractClass {
    protected name: string;

    constructor(name: string) {
        this.name = name;
    }

    abstract abstractMethod(): string;

    abstract asyncAbstractMethod(): Promise<string>;

    concreteMethod(): string {
        return "Concrete implementation";
    }
}

// Generic class
class GenericClass<T> {
    private items: T[];

    constructor(items: T[]) {
        this.items = items;
    }

    addItem(item: T): void {
        this.items.push(item);
    }

    getItems(): T[] {
        return this.items;
    }
}

// Class with multiple generic parameters
class MultipleGenericsClass<T, U> {
    constructor(private first: T, private second: U) {}

    getFirst(): T {
        return this.first;
    }

    getSecond(): U {
        return this.second;
    }
}

// Class implementing interface
class ImplementationClass implements ShapeInterface {
    constructor(private width: number, private height: number) {}

    area(): number {
        return this.width * this.height;
    }

    perimeter(): number {
        return 2 * (this.width + this.height);
    }
}

// Class with decorators (if decorators are enabled)
class DecoratedClass {
    @readonly
    name: string = "decorated";

    @methodDecorator
    decoratedMethod(): string {
        return "Decorated method";
    }
}

// ============================================================================
// INTERFACES - Should be extracted as BlockType.INTERFACE
// ============================================================================

interface SimpleInterface {
    name: string;
    age: number;
}

interface ShapeInterface {
    area(): number;
    perimeter(): number;
}

interface GenericInterface<T> {
    value: T;
    process(item: T): T;
}

interface ExtendedInterface extends SimpleInterface {
    email: string;
    getFullInfo(): string;
}

interface MultipleExtendedInterface extends SimpleInterface, ShapeInterface {
    id: number;
    description: string;
}

// Interface with optional properties
interface OptionalInterface {
    required: string;
    optional?: number;
    readonly readOnly: boolean;
}

// Interface with method signatures
interface MethodInterface {
    regularMethod(param: string): string;
    asyncMethod(param: number): Promise<number>;
    genericMethod<T>(item: T): T;
}

// Interface with index signatures
interface IndexInterface {
    [key: string]: any;
    [index: number]: string;
}

// Interface with call signatures
interface CallableInterface {
    (param: string): string;
    property: number;
}

// Interface with construct signatures
interface ConstructableInterface {
    new (param: string): any;
    staticMethod(): string;
}

// Conditional interface
interface ConditionalInterface<T> {
    value: T extends string ? string : number;
}

// ============================================================================
// IMPORTS - Should be extracted as BlockType.IMPORT
// ============================================================================

// Note: Imports are already at the top of the file
// import { readFileSync } from 'fs';
// import { join } from 'path';
// import * as util from 'util';
// import axios, { AxiosResponse } from 'axios';
// import { EventEmitter } from 'events';
// import type { IncomingMessage } from 'http';

// Additional import examples would go here in a real file:
// import defaultExport from 'module';
// import { namedExport } from 'module';
// import { originalName as alias } from 'module';
// import * as namespace from 'module';
// import 'module'; // side-effect import
// import type { TypeOnly } from 'module';

// ============================================================================
// EXPORTS - Should be extracted as BlockType.EXPORT
// ============================================================================

// Default export
export default class DefaultExportClass {
    name: string = "default";
}

// Named exports
export const EXPORTED_CONSTANT = "exported value";
export let exportedVariable = 42;

export function exportedFunction(): string {
    return "Exported function";
}

export async function exportedAsyncFunction(): Promise<string> {
    return "Exported async function";
}

export class ExportedClass {
    constructor(public name: string) {}
}

export interface ExportedInterface {
    name: string;
    value: number;
}

export enum ExportedEnum {
    VALUE1 = "value1",
    VALUE2 = "value2"
}

// Re-exports
export { Status } from './other-module';
export { Priority as TaskPriority } from './other-module';
export * from './other-module';
export * as OtherModule from './other-module';

// Export with type
export type ExportedType = string | number;
export type GenericExportedType<T> = T | null;

// ============================================================================
// COMPLEX EXAMPLES AND EDGE CASES
// ============================================================================

// Namespace
namespace MyNamespace {
    export interface NestedInterface {
        value: string;
    }

    export class NestedClass {
        constructor(public data: NestedInterface) {}
    }

    export function nestedFunction(): string {
        return "Nested function";
    }
}

// Module augmentation
declare module "existing-module" {
    interface ExistingInterface {
        newProperty: string;
    }
}

// Ambient declarations
declare const globalVariable: string;
declare function globalFunction(): void;
declare class GlobalClass {
    constructor(param: string);
}

// Conditional types
type ConditionalType<T> = T extends string ? string[] : number[];

// Mapped types
type MappedType<T> = {
    [K in keyof T]: T[K] | null;
};

// Template literal types
type TemplateType<T extends string> = `prefix-${T}-suffix`;

// Utility types usage
type PartialExample = Partial<SimpleInterface>;
type RequiredExample = Required<OptionalInterface>;
type PickExample = Pick<SimpleInterface, 'name'>;
type OmitExample = Omit<SimpleInterface, 'age'>;

// Function overloads
function overloadedFunction(param: string): string;
function overloadedFunction(param: number): number;
function overloadedFunction(param: string | number): string | number {
    if (typeof param === 'string') {
        return param.toUpperCase();
    }
    return param * 2;
}

// Class with private fields (ES2022)
class ModernClass {
    #privateField: string = "private";

    constructor(public publicField: string) {}

    #privateMethod(): string {
        return this.#privateField;
    }

    getPrivate(): string {
        return this.#privateMethod();
    }
}

// Decorator functions (for when decorators are enabled)
function readonly(target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    descriptor.writable = false;
    return descriptor;
}

function methodDecorator(target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    const originalMethod = descriptor.value;
    descriptor.value = function(...args: any[]) {
        console.log(`Calling ${propertyKey} with args:`, args);
        return originalMethod.apply(this, args);
    };
    return descriptor;
}

// Complex generic constraints
interface Lengthwise {
    length: number;
}

function constrainedGeneric<T extends Lengthwise>(arg: T): T {
    console.log(arg.length);
    return arg;
}

// Conditional type with inference
type InferType<T> = T extends (infer U)[] ? U : T;

// Complex class with all features
class ComplexClass<T extends string | number> {
    private static instances: number = 0;
    readonly id: number;

    constructor(
        public name: string,
        private value: T,
        protected settings: { [key: string]: any } = {}
    ) {
        this.id = ++ComplexClass.instances;
    }

    static getInstanceCount(): number {
        return ComplexClass.instances;
    }

    async processValue(): Promise<T> {
        await new Promise(resolve => setTimeout(resolve, 100));
        return this.value;
    }

    get displayName(): string {
        return `${this.name} (${this.id})`;
    }

    set displayName(name: string) {
        this.name = name;
    }

    *generateSequence(): Generator<number, void, unknown> {
        for (let i = 0; i < 3; i++) {
            yield i;
        }
    }

    protected updateSettings(key: string, value: any): void {
        this.settings[key] = value;
    }
}

// Union and intersection types
type UnionType = string | number | boolean;
type IntersectionType = SimpleInterface & ShapeInterface;

// Recursive type
type RecursiveType<T> = T | RecursiveType<T>[];

// Final exports
export {
    Status,
    Priority,
    SimpleClass,
    ClassWithMethods,
    AbstractClass,
    ShapeInterface,
    GenericInterface,
    simpleFunction,
    asyncFunction,
    DATABASE_URL,
    API_VERSION
};
