#!/usr/bin/env python3
"""Test script for class-level variable extraction."""

import tempfile
import os
from pathlib import Path
from ast_parser import ASTParser


def create_test_class_with_variables():
    """Create test files with classes containing different types of variables."""

    # Create a temporary directory for test files
    test_dir = tempfile.mkdtemp(prefix="class_variables_test_")

    # Python class with class-level variables
    python_class = """
class DataProcessor:
    # Class-level variables (should be extracted as class children)
    DEFAULT_BATCH_SIZE = 1000
    MAX_RETRIES = 3
    SUPPORTED_FORMATS = ['json', 'csv', 'xml']
    
    def __init__(self, config):
        # Instance variables (should NOT be extracted as class children)
        self.config = config
        self.processed_count = 0
        self.errors = []
    
    def process_data(self, data):
        # Local variables (should NOT be extracted as class children)
        batch_size = self.DEFAULT_BATCH_SIZE
        retry_count = 0
        
        for item in data:
            # More local variables
            processed_item = self._transform(item)
            if processed_item:
                self.processed_count += 1
        
        return True
    
    def _transform(self, item):
        # Local variable in another method
        transformed = item.upper() if isinstance(item, str) else str(item)
        return transformed

class StaticUtility:
    # More class-level variables
    VERSION = "1.0.0"
    DEBUG_MODE = False
    
    @staticmethod
    def get_version():
        return StaticUtility.VERSION
"""

    # TypeScript class with class-level fields
    typescript_class = """
export class ConfigManager {
    // Class-level static fields (should be extracted as class children)
    static readonly DEFAULT_TIMEOUT = 5000;
    static readonly MAX_CONNECTIONS = 100;
    static readonly SUPPORTED_PROTOCOLS = ['http', 'https', 'ws'];
    
    // Instance fields (should be extracted as class children)
    private config: any;
    public isInitialized: boolean = false;
    
    constructor(initialConfig: any) {
        // Local variables (should NOT be extracted as class children)
        const defaultConfig = { timeout: ConfigManager.DEFAULT_TIMEOUT };
        const mergedConfig = { ...defaultConfig, ...initialConfig };
        
        this.config = mergedConfig;
        this.isInitialized = true;
    }
    
    updateConfig(newConfig: any): void {
        // Local variables (should NOT be extracted as class children)
        const oldConfig = this.config;
        const updatedConfig = { ...oldConfig, ...newConfig };
        
        this.config = updatedConfig;
    }
    
    static createDefault(): ConfigManager {
        // Local variable in static method
        const defaultSettings = { 
            timeout: ConfigManager.DEFAULT_TIMEOUT,
            maxConnections: ConfigManager.MAX_CONNECTIONS 
        };
        
        return new ConfigManager(defaultSettings);
    }
}

interface IConfig {
    timeout: number;
    maxConnections: number;
}
"""

    # Write test files
    test_files = {
        "class_variables.py": python_class,
        "class_variables.ts": typescript_class,
    }

    for filename, content in test_files.items():
        file_path = Path(test_dir) / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    return test_dir


def main():
    """Test class variable extraction."""
    print("Creating test files with class-level variables...")
    test_dir = create_test_class_with_variables()

    try:
        print(f"Test directory created: {test_dir}")
        print("Files created:")
        for file_path in Path(test_dir).iterdir():
            if file_path.is_file():
                print(f"  - {file_path.name}")

        print("\nRunning AST parser on class variable files...")
        parser = ASTParser()
        results = parser.extract_from_directory(test_dir)

        print(f"Processed {len(results)} files")

        # Analyze results
        print("\n" + "=" * 80)
        print("CLASS VARIABLE EXTRACTION ANALYSIS")
        print("=" * 80)

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

                        if var_children:
                            print(f"      📊 Class-level variables found:")
                            for var in var_children:
                                print(f"        - {var.name}: '{var.content.strip()}'")
                        else:
                            print(f"      ⚠️  No class-level variables found")

                        if method_children:
                            print(f"      📋 Methods:")
                            for method in method_children:
                                line_count = method.end_line - method.start_line + 1
                                print(f"        - {method.name}: {line_count} lines")

            # Show top-level variables (these should be local variables from methods)
            top_level_vars = [b for b in blocks if b.type.value == "variable"]
            if top_level_vars:
                print(f"\n   📄 Top-level variable blocks (should be method locals):")
                for var in top_level_vars:
                    print(
                        f"      - {var.name}: '{var.content.strip()}' (lines {var.start_line}-{var.end_line})"
                    )

        print(f"\n📄 Analysis complete!")

    finally:
        # Clean up test directory
        import shutil

        shutil.rmtree(test_dir)
        print(f"\nCleaned up test directory: {test_dir}")


if __name__ == "__main__":
    main()
