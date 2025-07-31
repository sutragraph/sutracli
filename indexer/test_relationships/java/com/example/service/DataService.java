/**
 * Data service for testing complex package structures.
 */
package com.example.service;

// Import from different package levels
import com.example.model.User;
import com.example.model.Product;

// Import from utils (different root)
import utils.Helper;

// Standard library imports
import java.util.List;
import java.util.ArrayList;
import java.util.Optional;
import java.util.stream.Collectors;

/**
 * Service class demonstrating complex package relationships
 */
public class DataService {
    
    private Helper helper;
    private List<User> users;
    private List<Product> products;
    
    /**
     * Constructor
     */
    public DataService() {
        this.helper = new Helper();
        this.users = new ArrayList<>();
        this.products = new ArrayList<>();
    }
    
    /**
     * Add a user
     */
    public void addUser(User user) {
        if (user != null) {
            users.add(user);
            System.out.println("Added user: " + user.getName());
        }
    }
    
    /**
     * Find user by name
     */
    public Optional<User> findUserByName(String name) {
        return users.stream()
                .filter(user -> user.getName().equals(name))
                .findFirst();
    }
    
    /**
     * Get all products
     */
    public List<Product> getAllProducts() {
        return new ArrayList<>(products);
    }
    
    /**
     * Process data using helper
     */
    public void processData() {
        helper.helpWithTask();
        
        List<String> userNames = users.stream()
                .map(User::getName)
                .collect(Collectors.toList());
        
        System.out.println("Processing " + userNames.size() + " users");
    }
}
