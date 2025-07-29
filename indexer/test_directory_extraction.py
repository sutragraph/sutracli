#!/usr/bin/env python3
"""Test script for directory extraction with nested function feature."""

import json
import os
import tempfile
from pathlib import Path
from ast_parser import ASTParser


def create_test_files():
    """Create test files with both large and small functions."""

    # Create a temporary directory for test files
    test_dir = tempfile.mkdtemp(prefix="nested_function_test_")

    # Large TypeScript function (300+ lines)
    large_ts_content = (
        """
// Large TypeScript file with nested functions
export class DataProcessor {
    private data: any[] = [];
    
    // Small function - should not trigger nested extraction
    validateInput(input: string): boolean {
        if (!input) return false;
        return input.length > 0;
    }
    
    // Large function - should trigger nested extraction
    processLargeDataset(dataset: any[]): ProcessedData {
        const results: ProcessedData = {
            processed: [],
            errors: [],
            statistics: {}
        };
        
        function cleanData(rawData: any[]): any[] {
            const cleaned = [];
            for (const item of rawData) {
                if (item && typeof item === 'object') {
                    cleaned.push({
                        id: item.id || generateId(),
                        value: item.value || 0,
                        timestamp: item.timestamp || Date.now()
                    });
                }
            }
            return cleaned;
        }
        
        function validateData(data: any[]): ValidationResult {
            const result: ValidationResult = {
                valid: [],
                invalid: [],
                warnings: []
            };
            
            for (const item of data) {
                if (!item.id) {
                    result.invalid.push(item);
                    continue;
                }
                
                if (item.value < 0) {
                    result.warnings.push(`Negative value for item ${item.id}`);
                }
                
                result.valid.push(item);
            }
            
            return result;
        }
        
        function transformData(validData: any[]): any[] {
            return validData.map(item => ({
                ...item,
                processed: true,
                processedAt: new Date().toISOString(),
                hash: generateHash(item)
            }));
        }
        
        function generateStatistics(data: any[]): Statistics {
            const stats: Statistics = {
                total: data.length,
                average: 0,
                min: Number.MAX_VALUE,
                max: Number.MIN_VALUE,
                distribution: {}
            };
            
            let sum = 0;
            for (const item of data) {
                const value = item.value || 0;
                sum += value;
                
                if (value < stats.min) stats.min = value;
                if (value > stats.max) stats.max = value;
                
                const bucket = Math.floor(value / 10) * 10;
                stats.distribution[bucket] = (stats.distribution[bucket] || 0) + 1;
            }
            
            stats.average = data.length > 0 ? sum / data.length : 0;
            return stats;
        }
        
"""
        + "\n".join([f"        // Processing step {i}" for i in range(1, 250)])
        + """
        
        // Main processing logic
        try {
            const cleaned = cleanData(dataset);
            const validated = validateData(cleaned);
            const transformed = transformData(validated.valid);
            const statistics = generateStatistics(transformed);
            
            results.processed = transformed;
            results.errors = validated.invalid;
            results.statistics = statistics;
            
            return results;
        } catch (error) {
            console.error('Processing failed:', error);
            throw error;
        }
    }
}

interface ProcessedData {
    processed: any[];
    errors: any[];
    statistics: Statistics;
}

interface ValidationResult {
    valid: any[];
    invalid: any[];
    warnings: string[];
}

interface Statistics {
    total: number;
    average: number;
    min: number;
    max: number;
    distribution: Record<string, number>;
}

function generateId(): string {
    return Math.random().toString(36).substr(2, 9);
}

function generateHash(item: any): string {
    return btoa(JSON.stringify(item)).substr(0, 8);
}
"""
    )

    # Large Python function (300+ lines)
    large_py_content = (
        """
# Large Python file with nested functions
import json
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime

class DataAnalyzer:
    def __init__(self):
        self.data = []
        self.results = {}
    
    # Small function - should not trigger nested extraction
    def validate_input(self, data: Any) -> bool:
        \"\"\"Validate input data.\"\"\"
        return data is not None and len(str(data)) > 0
    
    # Large function - should trigger nested extraction
    def analyze_complex_dataset(self, dataset: List[Dict]) -> Dict[str, Any]:
        \"\"\"Analyze a complex dataset with multiple processing steps.\"\"\"
        analysis_results = {
            'processed_data': [],
            'statistics': {},
            'anomalies': [],
            'recommendations': []
        }
        
        def preprocess_data(raw_data: List[Dict]) -> List[Dict]:
            \"\"\"Clean and preprocess the raw data.\"\"\"
            processed = []
            for item in raw_data:
                if not item or not isinstance(item, dict):
                    continue
                
                cleaned_item = {
                    'id': item.get('id', self._generate_id()),
                    'value': float(item.get('value', 0)),
                    'category': str(item.get('category', 'unknown')).lower(),
                    'timestamp': item.get('timestamp', datetime.now().isoformat()),
                    'metadata': item.get('metadata', {})
                }
                
                # Additional cleaning
                if cleaned_item['value'] < 0:
                    cleaned_item['value'] = abs(cleaned_item['value'])
                    cleaned_item['metadata']['was_negative'] = True
                
                processed.append(cleaned_item)
            
            return processed
        
        def detect_anomalies(data: List[Dict]) -> List[Dict]:
            \"\"\"Detect anomalies in the dataset.\"\"\"
            anomalies = []
            if not data:
                return anomalies
            
            values = [item['value'] for item in data]
            mean_val = sum(values) / len(values)
            std_dev = (sum((x - mean_val) ** 2 for x in values) / len(values)) ** 0.5
            
            threshold = mean_val + (2 * std_dev)
            
            for item in data:
                if item['value'] > threshold:
                    anomalies.append({
                        'item_id': item['id'],
                        'value': item['value'],
                        'threshold': threshold,
                        'deviation': item['value'] - mean_val,
                        'type': 'statistical_outlier'
                    })
            
            return anomalies
        
        def calculate_advanced_statistics(data: List[Dict]) -> Dict[str, Any]:
            \"\"\"Calculate comprehensive statistics.\"\"\"
            if not data:
                return {}
            
            values = [item['value'] for item in data]
            categories = {}
            
            for item in data:
                cat = item['category']
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(item['value'])
            
            stats = {
                'total_items': len(data),
                'total_value': sum(values),
                'mean': sum(values) / len(values),
                'median': sorted(values)[len(values) // 2],
                'min': min(values),
                'max': max(values),
                'categories': {}
            }
            
            # Category-specific statistics
            for cat, cat_values in categories.items():
                stats['categories'][cat] = {
                    'count': len(cat_values),
                    'mean': sum(cat_values) / len(cat_values),
                    'total': sum(cat_values),
                    'percentage': (len(cat_values) / len(data)) * 100
                }
            
            return stats
        
        def generate_recommendations(data: List[Dict], stats: Dict, anomalies: List[Dict]) -> List[str]:
            \"\"\"Generate recommendations based on analysis.\"\"\"
            recommendations = []
            
            if not data:
                recommendations.append("No data available for analysis")
                return recommendations
            
            # Data quality recommendations
            if len(anomalies) > len(data) * 0.1:
                recommendations.append("High number of anomalies detected - consider data quality review")
            
            # Category distribution recommendations
            if 'categories' in stats:
                category_counts = [cat_stats['count'] for cat_stats in stats['categories'].values()]
                if max(category_counts) > len(data) * 0.8:
                    recommendations.append("Data heavily skewed towards one category - consider balancing")
            
            # Value range recommendations
            if stats.get('max', 0) > stats.get('mean', 0) * 10:
                recommendations.append("Large value range detected - consider normalization")
            
            return recommendations
        
"""
        + "\n".join([f"        # Analysis step {i}" for i in range(1, 200)])
        + """
        
        # Main analysis workflow
        try:
            # Step 1: Preprocess the data
            processed_data = preprocess_data(dataset)
            
            # Step 2: Detect anomalies
            anomalies = detect_anomalies(processed_data)
            
            # Step 3: Calculate statistics
            statistics = calculate_advanced_statistics(processed_data)
            
            # Step 4: Generate recommendations
            recommendations = generate_recommendations(processed_data, statistics, anomalies)
            
            # Compile results
            analysis_results.update({
                'processed_data': processed_data,
                'statistics': statistics,
                'anomalies': anomalies,
                'recommendations': recommendations,
                'processing_timestamp': datetime.now().isoformat(),
                'data_quality_score': max(0, 100 - (len(anomalies) / len(processed_data) * 100)) if processed_data else 0
            })
            
            return analysis_results
            
        except Exception as e:
            return {
                'error': str(e),
                'processed_data': [],
                'statistics': {},
                'anomalies': [],
                'recommendations': [f"Analysis failed: {str(e)}"]
            }
    
    def _generate_id(self) -> str:
        \"\"\"Generate a unique ID.\"\"\"
        return hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]

# Small standalone function
def simple_helper(value: str) -> str:
    \"\"\"Simple helper function.\"\"\"
    return value.upper().strip()
"""
    )

    # Small TypeScript file
    small_ts_content = """
// Small TypeScript file with only small functions
export class SimpleUtils {
    static formatString(input: string): string {
        return input.trim().toLowerCase();
    }
    
    static calculateSum(numbers: number[]): number {
        return numbers.reduce((sum, num) => sum + num, 0);
    }
    
    static isValidEmail(email: string): boolean {
        const emailRegex = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;
        return emailRegex.test(email);
    }
}

function quickSort(arr: number[]): number[] {
    if (arr.length <= 1) return arr;
    
    const pivot = arr[Math.floor(arr.length / 2)];
    const left = arr.filter(x => x < pivot);
    const right = arr.filter(x => x > pivot);
    
    return [...quickSort(left), pivot, ...quickSort(right)];
}
"""

    # Small Python file
    small_py_content = """
# Small Python file with only small functions
from typing import List, Optional

def fibonacci(n: int) -> int:
    \"\"\"Calculate fibonacci number.\"\"\"
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def is_prime(num: int) -> bool:
    \"\"\"Check if a number is prime.\"\"\"
    if num < 2:
        return False
    for i in range(2, int(num ** 0.5) + 1):
        if num % i == 0:
            return False
    return True

class MathUtils:
    @staticmethod
    def gcd(a: int, b: int) -> int:
        \"\"\"Calculate greatest common divisor.\"\"\"
        while b:
            a, b = b, a % b
        return a
    
    @staticmethod
    def lcm(a: int, b: int) -> int:
        \"\"\"Calculate least common multiple.\"\"\"
        return abs(a * b) // MathUtils.gcd(a, b)
"""

    # Write test files
    test_files = {
        "large_processor.ts": large_ts_content,
        "large_analyzer.py": large_py_content,
        "small_utils.ts": small_ts_content,
        "small_math.py": small_py_content,
    }

    for filename, content in test_files.items():
        file_path = Path(test_dir) / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    return test_dir


def serialize_code_block(block):
    """Convert CodeBlock to JSON-serializable dictionary."""
    return {
        "id": block.id,
        "type": block.type.value,
        "name": block.name,
        "content": block.content,
        "symbols": block.symbols,
        "start_line": block.start_line,
        "end_line": block.end_line,
        "start_col": block.start_col,
        "end_col": block.end_col,
        "children": [serialize_code_block(child) for child in block.children],
    }


def main():
    """Main function to test directory extraction."""
    print("Creating test files with large and small functions...")
    test_dir = create_test_files()

    try:
        print(f"Test directory created: {test_dir}")
        print("Files created:")
        for file_path in Path(test_dir).iterdir():
            if file_path.is_file():
                print(f"  - {file_path.name}")

        print("\nRunning AST parser on directory...")
        parser = ASTParser()
        results = parser.extract_from_directory(test_dir)

        print(f"Processed {len(results)} files")

        # Convert results to JSON-serializable format
        json_results = {}
        for file_path, result in results.items():
            json_result = {
                "language": result.get("language"),
                "id": result.get("id"),
                "file_path": result.get("file_path"),
                "content_hash": result.get("content_hash"),
                "blocks": [
                    serialize_code_block(block) for block in result.get("blocks", [])
                ],
                "relationships": result.get("relationships", []),
            }

            if "error" in result:
                json_result["error"] = result["error"]

            json_results[file_path] = json_result

        # Save results to JSON file
        output_file = "nested_function_extraction_results.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(json_results, f, indent=2, ensure_ascii=False)

        print(f"\nResults saved to: {output_file}")

        # Print summary
        print("\n" + "=" * 60)
        print("EXTRACTION SUMMARY")
        print("=" * 60)

        for file_path, result in results.items():
            filename = Path(file_path).name
            blocks = result.get("blocks", [])

            print(f"\n📁 {filename}")
            print(f"   Language: {result.get('language', 'unknown')}")
            print(f"   Total blocks: {len(blocks)}")

            function_blocks = [b for b in blocks if b.type.value == "function"]
            if function_blocks:
                print(f"   Function blocks: {len(function_blocks)}")

                for func in function_blocks:
                    line_count = func.end_line - func.start_line + 1
                    nested_count = len(func.children)

                    status = "🔍 NESTED EXTRACTED" if nested_count > 0 else "✅ NORMAL"
                    print(
                        f"     - {func.name}: {line_count} lines, {nested_count} nested functions {status}"
                    )

                    if nested_count > 0:
                        for child in func.children:
                            print(f"       └─ {child.name} (ID: {child.id})")

        print(f"\n📄 Full results saved to: {output_file}")

    finally:
        # Clean up test directory
        import shutil

        shutil.rmtree(test_dir)
        print(f"\nCleaned up test directory: {test_dir}")


if __name__ == "__main__":
    main()
