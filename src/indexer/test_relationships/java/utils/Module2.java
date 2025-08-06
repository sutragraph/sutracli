/**
 * Module 2 for testing Java relationship extraction.
 */
package utils;

// Import from parent package (going up one level)
import Module1;

// Standard library imports
import java.util.Date;
import java.text.SimpleDateFormat;

/**
 * Utility class in utils package
 */
public class Module2 {
    
    private SimpleDateFormat dateFormat;
    
    /**
     * Constructor
     */
    public Module2() {
        this.dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
    }
    
    /**
     * Example function
     */
    public void function2() {
        System.out.println("Function 2 from Module2");
        Date currentDate = new Date();
        String formattedDate = dateFormat.format(currentDate);
        System.out.println("Current time: " + formattedDate);
    }
    
    /**
     * Static method for static imports
     */
    public static void staticMethod() {
        System.out.println("Static method from Module2");
    }
    
    /**
     * Utility data processing method
     */
    public void processUtilityData() {
        System.out.println("Processing utility data in Module2");
    }
    
    /**
     * Method that creates dependency back to parent package
     */
    public void useModule1() {
        Module1 module1 = new Module1();
        String result = module1.function1();
        System.out.println("Using Module1 from Module2: " + result);
    }
}
