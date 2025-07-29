#!/usr/bin/env python3
"""Test script for class method nested function extraction."""

import tempfile
import os
from pathlib import Path
from ast_parser import ASTParser


def create_test_class_files():
    """Create test files with classes containing large methods."""

    # Create a temporary directory for test files
    test_dir = tempfile.mkdtemp(prefix="class_method_test_")

    # Large TypeScript class with a large method
    large_ts_class = (
        """
export class DataProcessor {
    private config: any;
    
    constructor(config: any) {
        this.config = config;
    }
    
    // Small method - should not trigger nested extraction
    validateConfig(): boolean {
        return this.config && typeof this.config === 'object';
    }
    
    // Large method - should trigger nested extraction
    processComplexData(data: any[]): ProcessedResult {
        const result: ProcessedResult = {
            processed: [],
            errors: [],
            metadata: {}
        };
        
        function validateItem(item: any): boolean {
            if (!item || typeof item !== 'object') {
                return false;
            }
            return item.id && item.value !== undefined;
        }
        
        function transformItem(item: any): TransformedItem {
            return {
                id: item.id,
                value: parseFloat(item.value) || 0,
                timestamp: new Date().toISOString(),
                processed: true
            };
        }
        
        function calculateMetrics(items: TransformedItem[]): Metrics {
            const metrics: Metrics = {
                total: items.length,
                sum: 0,
                average: 0,
                min: Number.MAX_VALUE,
                max: Number.MIN_VALUE
            };
            
            for (const item of items) {
                metrics.sum += item.value;
                if (item.value < metrics.min) metrics.min = item.value;
                if (item.value > metrics.max) metrics.max = item.value;
            }
            
            metrics.average = items.length > 0 ? metrics.sum / items.length : 0;
            return metrics;
        }
        
"""
        + "\n".join([f"        // Processing step {i}" for i in range(1, 250)])
        + """
        
        // Main processing logic
        try {
            const validItems = data.filter(validateItem);
            const transformedItems = validItems.map(transformItem);
            const metrics = calculateMetrics(transformedItems);
            
            result.processed = transformedItems;
            result.metadata = { metrics, processedAt: new Date().toISOString() };
            
            return result;
        } catch (error) {
            result.errors.push(error.message);
            return result;
        }
    }
    
    // Another small method
    getProcessedCount(): number {
        return this.config.processedCount || 0;
    }
}

interface ProcessedResult {
    processed: any[];
    errors: string[];
    metadata: any;
}

interface TransformedItem {
    id: string;
    value: number;
    timestamp: string;
    processed: boolean;
}

interface Metrics {
    total: number;
    sum: number;
    average: number;
    min: number;
    max: number;
}
"""
    )

    # Large Python class with a large method
    large_py_class = (
        """
from typing import List, Dict, Any, Optional
from datetime import datetime

class DataAnalyzer:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.results = {}
    
    # Small method - should not trigger nested extraction
    def validate_config(self) -> bool:
        \"\"\"Validate configuration.\"\"\"
        return self.config and isinstance(self.config, dict)
    
    # Large method - should trigger nested extraction
    def analyze_large_dataset(self, dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
        \"\"\"Analyze a large dataset with complex processing.\"\"\"
        analysis_result = {
            'processed_data': [],
            'statistics': {},
            'anomalies': [],
            'summary': {}
        }
        
        def preprocess_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            \"\"\"Preprocess a single data item.\"\"\"
            if not item or not isinstance(item, dict):
                return None
            
            processed = {
                'id': item.get('id', self._generate_id()),
                'value': float(item.get('value', 0)),
                'category': str(item.get('category', 'unknown')).lower(),
                'timestamp': item.get('timestamp', datetime.now().isoformat()),
                'metadata': item.get('metadata', {})
            }
            
            # Validation and cleaning
            if processed['value'] < 0:
                processed['value'] = abs(processed['value'])
                processed['metadata']['was_negative'] = True
            
            return processed
        
        def detect_anomalies(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            \"\"\"Detect statistical anomalies in the data.\"\"\"
            if not data:
                return []
            
            values = [item['value'] for item in data]
            mean_val = sum(values) / len(values)
            variance = sum((x - mean_val) ** 2 for x in values) / len(values)
            std_dev = variance ** 0.5
            
            threshold = mean_val + (2 * std_dev)
            anomalies = []
            
            for item in data:
                if item['value'] > threshold:
                    anomalies.append({
                        'item_id': item['id'],
                        'value': item['value'],
                        'threshold': threshold,
                        'deviation': item['value'] - mean_val,
                        'severity': 'high' if item['value'] > mean_val + (3 * std_dev) else 'medium'
                    })
            
            return anomalies
        
        def calculate_statistics(data: List[Dict[str, Any]]) -> Dict[str, Any]:
            \"\"\"Calculate comprehensive statistics.\"\"\"
            if not data:
                return {}
            
            values = [item['value'] for item in data]
            categories = {}
            
            # Group by category
            for item in data:
                cat = item['category']
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(item['value'])
            
            # Calculate overall statistics
            stats = {
                'total_items': len(data),
                'total_value': sum(values),
                'mean': sum(values) / len(values),
                'median': sorted(values)[len(values) // 2],
                'min': min(values),
                'max': max(values),
                'range': max(values) - min(values),
                'categories': {}
            }
            
            # Calculate category-specific statistics
            for cat, cat_values in categories.items():
                stats['categories'][cat] = {
                    'count': len(cat_values),
                    'mean': sum(cat_values) / len(cat_values),
                    'total': sum(cat_values),
                    'percentage': (len(cat_values) / len(data)) * 100,
                    'min': min(cat_values),
                    'max': max(cat_values)
                }
            
            return stats
        
"""
        + "\n".join([f"        # Analysis step {i}" for i in range(1, 200)])
        + """
        
        # Main analysis workflow
        try:
            # Step 1: Preprocess all items
            processed_items = []
            for item in dataset:
                processed = preprocess_item(item)
                if processed:
                    processed_items.append(processed)
            
            # Step 2: Detect anomalies
            anomalies = detect_anomalies(processed_items)
            
            # Step 3: Calculate statistics
            statistics = calculate_statistics(processed_items)
            
            # Step 4: Generate summary
            summary = {
                'total_processed': len(processed_items),
                'anomaly_count': len(anomalies),
                'anomaly_rate': (len(anomalies) / len(processed_items)) * 100 if processed_items else 0,
                'quality_score': max(0, 100 - (len(anomalies) / len(processed_items) * 100)) if processed_items else 0,
                'processing_timestamp': datetime.now().isoformat()
            }
            
            # Compile final result
            analysis_result.update({
                'processed_data': processed_items,
                'statistics': statistics,
                'anomalies': anomalies,
                'summary': summary
            })
            
            return analysis_result
            
        except Exception as e:
            return {
                'error': str(e),
                'processed_data': [],
                'statistics': {},
                'anomalies': [],
                'summary': {'error': True, 'message': str(e)}
            }
    
    def _generate_id(self) -> str:
        \"\"\"Generate a unique ID.\"\"\"
        import hashlib
        return hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
    
    # Another small method
    def get_config_value(self, key: str) -> Any:
        \"\"\"Get configuration value.\"\"\"
        return self.config.get(key)
"""
    )

    # Write test files
    test_files = {"large_class.ts": large_ts_class, "large_class.py": large_py_class}

    for filename, content in test_files.items():
        file_path = Path(test_dir) / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    return test_dir


def main():
    """Test class method nested extraction."""
    print("Creating test files with large class methods...")
    test_dir = create_test_class_files()

    try:
        print(f"Test directory created: {test_dir}")
        print("Files created:")
        for file_path in Path(test_dir).iterdir():
            if file_path.is_file():
                print(f"  - {file_path.name}")

        print("\nRunning AST parser on class files...")
        parser = ASTParser()
        results = parser.extract_from_directory(test_dir)

        print(f"Processed {len(results)} files")

        # Analyze results
        print("\n" + "=" * 60)
        print("CLASS METHOD EXTRACTION SUMMARY")
        print("=" * 60)

        for file_path, result in results.items():
            filename = Path(file_path).name
            blocks = result.get("blocks", [])

            print(f"\n📁 {filename}")
            print(f"   Language: {result.get('language', 'unknown')}")
            print(f"   Total blocks: {len(blocks)}")

            class_blocks = [b for b in blocks if b.type.value == "class"]
            if class_blocks:
                print(f"   Class blocks: {len(class_blocks)}")

                for class_block in class_blocks:
                    print(f"\n   🏛️  Class: {class_block.name}")
                    print(f"      Content length: {len(class_block.content)} chars")
                    print(f"      Children: {len(class_block.children)}")

                    if class_block.children:
                        method_children = [
                            c
                            for c in class_block.children
                            if c.type.value == "function"
                        ]
                        var_children = [
                            c
                            for c in class_block.children
                            if c.type.value == "variable"
                        ]

                        print(f"      Methods: {len(method_children)}")
                        print(f"      Variables: {len(var_children)}")

                        for method in method_children:
                            line_count = method.end_line - method.start_line + 1
                            nested_count = len(method.children)

                            status = (
                                "🔍 NESTED EXTRACTED"
                                if nested_count > 0
                                else "✅ NORMAL"
                            )
                            print(
                                f"        - {method.name}: {line_count} lines, {nested_count} nested functions {status}"
                            )

                            if nested_count > 0:
                                for child in method.children:
                                    print(f"          └─ {child.name} (ID: {child.id})")

        print(f"\n📄 Analysis complete!")

    finally:
        # Clean up test directory
        import shutil

        shutil.rmtree(test_dir)
        print(f"\nCleaned up test directory: {test_dir}")


if __name__ == "__main__":
    main()
