/**
 * Main class for testing Java relationship extraction.
 */

// Standard imports
import java.util.Date;
import java.util.List;
import java.util.ArrayList;

// Custom imports from same package
import Module1;
import DefaultClass;

// Import from utils package
import utils.Module2;

// Static imports
import static utils.Module2.staticMethod;
import static java.lang.Math.PI;

// Wildcard imports
import java.util.*;

/**
 * Main class demonstrating various import patterns
 */
public class Main {
    
    /**
     * Main method
     */
    public static void main(String[] args) {
        System.out.println("Main class");
        
        // Use imported classes and methods
        Module1 module1 = new Module1();
        String result = module1.function1();
        System.out.println(result);
        
        Module2 module2 = new Module2();
        module2.function2();
        
        DefaultClass defaultInstance = new DefaultClass();
        defaultInstance.method();
        
        // Use static import
        staticMethod();
        System.out.println("PI value: " + PI);
        
        // Use wildcard imports
        Date currentDate = new Date();
        List<String> list = new ArrayList<>();
        list.add("Test item");
        
        System.out.println("Current time: " + currentDate);
        System.out.println("List size: " + list.size());
    }
}
