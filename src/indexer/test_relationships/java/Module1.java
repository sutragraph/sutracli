/**
 * Module 1 for testing Java relationship extraction.
 */

// Import from utils package
import utils.Module2;

// Standard library import
import java.util.Random;

/**
 * Example class with dependencies
 */
public class Module1 {
    
    private Module2 module2;
    private Random random;
    
    /**
     * Constructor
     */
    public Module1() {
        this.module2 = new Module2();
        this.random = new Random();
    }
    
    /**
     * Example function that uses imported classes
     */
    public String function1() {
        System.out.println("Function 1 from Module1");
        module2.function2();
        
        int randomNumber = random.nextInt(100);
        return "Result from function1: " + randomNumber;
    }
    
    /**
     * Another method
     */
    public void processData() {
        System.out.println("Processing data in Module1");
        module2.processUtilityData();
    }
}
