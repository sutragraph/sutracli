/**
 * User model class for testing package relationships.
 */
package com.example.model;

// Standard library imports
import java.time.LocalDateTime;
import java.util.Objects;

/**
 * User model class
 */
public class User {
    
    private String name;
    private String email;
    private LocalDateTime createdAt;
    
    /**
     * Default constructor
     */
    public User() {
        this.createdAt = LocalDateTime.now();
    }
    
    /**
     * Constructor with parameters
     */
    public User(String name, String email) {
        this();
        this.name = name;
        this.email = email;
    }
    
    /**
     * Get name
     */
    public String getName() {
        return name;
    }
    
    /**
     * Set name
     */
    public void setName(String name) {
        this.name = name;
    }
    
    /**
     * Get email
     */
    public String getEmail() {
        return email;
    }
    
    /**
     * Set email
     */
    public void setEmail(String email) {
        this.email = email;
    }
    
    /**
     * Get created at timestamp
     */
    public LocalDateTime getCreatedAt() {
        return createdAt;
    }
    
    @Override
    public boolean equals(Object obj) {
        if (this == obj) return true;
        if (obj == null || getClass() != obj.getClass()) return false;
        User user = (User) obj;
        return Objects.equals(name, user.name) && Objects.equals(email, user.email);
    }
    
    @Override
    public int hashCode() {
        return Objects.hash(name, email);
    }
    
    @Override
    public String toString() {
        return "User{name='" + name + "', email='" + email + "', createdAt=" + createdAt + "}";
    }
}
