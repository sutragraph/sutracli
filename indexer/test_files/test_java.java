package indexer.test_files;
import java.io.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.function.*;
import java.util.stream.*;

// ============================================================================
// ENUMS
// ============================================================================

enum Status {
    PENDING("pending"),
    ACTIVE("active"),
    INACTIVE("inactive");

    private final String value;

    Status(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}

enum Priority {
    LOW(1),
    MEDIUM(2),
    HIGH(3);

    private final int value;

    Priority(int value) {
        this.value = value;
    }

    public int getValue() {
        return value;
    }
}

enum Color {
    RED,
    GREEN,
    BLUE
}

// ============================================================================
// CONSTANTS AND VARIABLES
// ============================================================================

public class Constants {
    public static final String DATABASE_URL = "postgresql://localhost/mydb";
    public static final String API_VERSION = "v1.0";
    public static final int MAX_RETRIES = 3;
    public static boolean IS_DEBUG = true;

    // Complex configuration object using builder pattern
    public static final Config CONFIG = Config.builder()
        .host("localhost")
        .port(5432)
        .debug(true)
        .feature("auth", true)
        .feature("logging", false)
        .build();
}

// ============================================================================
// CLASSES
// ============================================================================

class SimpleClass {
    private int value;

    public SimpleClass() {
        this.value = 42;
    }

    public int getValue() {
        return value;
    }
}

class ClassWithMethods {
    private String name;
    private int privateValue = 100;

    public ClassWithMethods(String name) {
        this.name = name;
    }

    public String getName() {
        return name;
    }

    private int getPrivateValue() {
        return privateValue;
    }

    protected int getProtectedValue() {
        return privateValue;
    }

    public static String staticMethod() {
        return "Static result";
    }

    public CompletableFuture<String> asyncMethod() {
        return CompletableFuture.supplyAsync(() -> {
            try {
                Thread.sleep(100);
                return "Async method result";
            } catch (InterruptedException e) {
                throw new CompletionException(e);
            }
        });
    }

    // Generic method
    public <T> T genericMethod(T item) {
        return item;
    }
}

// Class with inheritance
class InheritedClass extends ClassWithMethods {
    private int value;

    public InheritedClass(String name, int value) {
        super(name);
        this.value = value;
    }

    public String getInfo() {
        return String.format("%s: %d", getName(), value);
    }

    @Override
    public String getName() {
        return "Override: " + super.getName();
    }
}

// Abstract class
abstract class AbstractClass {
    protected String name;

    public AbstractClass(String name) {
        this.name = name;
    }

    public abstract String abstractMethod();

    public abstract CompletableFuture<String> asyncAbstractMethod();

    public String concreteMethod() {
        return "Concrete implementation";
    }
}

// Generic class
class GenericClass<T> {
    private List<T> items;

    public GenericClass(List<T> items) {
        this.items = items;
    }

    public void addItem(T item) {
        items.add(item);
    }

    public List<T> getItems() {
        return items;
    }
}

// Interface definitions
interface SimpleInterface {
    String getName();
    int getAge();
}

interface ShapeInterface {
    double area();
    double perimeter();
}

// Implementation class
class ImplementationClass implements ShapeInterface {
    private final double width;
    private final double height;

    public ImplementationClass(double width, double height) {
        this.width = width;
        this.height = height;
    }

    @Override
    public double area() {
        return width * height;
    }

    @Override
    public double perimeter() {
        return 2 * (width + height);
    }
}

// Complex class with all features
class ComplexClass<T> {
    private static int instances = 0;
    private final int id;
    private final String name;
    private final T value;
    private final Map<String, Object> settings;

    public ComplexClass(String name, T value, Map<String, Object> settings) {
        this.id = ++instances;
        this.name = name;
        this.value = value;
        this.settings = settings != null ? settings : new HashMap<>();
    }

    public static int getInstanceCount() {
        return instances;
    }

    public CompletableFuture<T> processValue() {
        return CompletableFuture.supplyAsync(() -> {
            try {
                Thread.sleep(100);
                return value;
            } catch (InterruptedException e) {
                throw new CompletionException(e);
            }
        });
    }

    public String getDisplayName() {
        return String.format("%s (%d)", name, id);
    }

    protected void updateSettings(String key, Object value) {
        settings.put(key, value);
    }

    // Iterator method
    public Iterator<Integer> generateSequence() {
        return IntStream.range(0, 3).boxed().iterator();
    }
}

// Main class
public class test_java {
    public static void main(String[] args) {
        // Example usage
        SimpleClass simple = new SimpleClass();
        System.out.println(simple.getValue());

        ClassWithMethods methods = new ClassWithMethods("Test");
        System.out.println(methods.getName());

        // Using CompletableFuture
        methods.asyncMethod()
            .thenAccept(System.out::println)
            .join();

        // Using generics
        List<String> items = Arrays.asList("item1", "item2");
        GenericClass<String> generic = new GenericClass<>(items);
        generic.addItem("item3");
        System.out.println(generic.getItems());
    }
}
