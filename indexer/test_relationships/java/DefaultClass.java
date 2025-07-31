/**
 * Default class for testing Java relationship extraction.
 */

// Import from utils package
import utils.Helper;

// Standard library imports
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * Default class demonstrating various relationships
 */
public class DefaultClass {
    
    private Helper helper;
    private DateTimeFormatter formatter;
    
    /**
     * Constructor
     */
    public DefaultClass() {
        this.helper = new Helper();
        this.formatter = DateTimeFormatter.ISO_LOCAL_DATE_TIME;
    }
    
    /**
     * Example method
     */
    public void method() {
        System.out.println("Method from DefaultClass");
        
        LocalDateTime now = LocalDateTime.now();
        String formattedTime = now.format(formatter);
        
        System.out.println("Current time: " + formattedTime);
        helper.helpWithTask();
    }
    
    /**
     * Another method that uses helper
     */
    public String processWithHelper(String input) {
        return helper.processString(input);
    }
}
