/**
 * Helper utility class for testing Java relationship extraction.
 */
package utils;

// Standard library imports
import java.util.concurrent.ThreadLocalRandom;
import java.util.stream.Collectors;
import java.util.Arrays;

/**
 * Helper utility class
 */
public class Helper {
    
    /**
     * Help with a task
     */
    public void helpWithTask() {
        System.out.println("Helper is helping with task");
        
        // Generate some random data
        int randomValue = ThreadLocalRandom.current().nextInt(1, 101);
        System.out.println("Generated random value: " + randomValue);
    }
    
    /**
     * Process a string input
     */
    public String processString(String input) {
        if (input == null) {
            return "null";
        }
        
        // Use streams to process the string
        return Arrays.stream(input.split(""))
                .map(String::toUpperCase)
                .collect(Collectors.joining("-"));
    }
    
    /**
     * Calculate something
     */
    public double calculate(double... values) {
        return Arrays.stream(values)
                .average()
                .orElse(0.0);
    }
}
