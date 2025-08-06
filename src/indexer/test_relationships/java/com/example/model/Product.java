/**
 * Product model class for testing package relationships.
 */
package com.example.model;

// Standard library imports
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Objects;

/**
 * Product model class
 */
public class Product {
    
    private String name;
    private String description;
    private BigDecimal price;
    private LocalDateTime createdAt;
    
    /**
     * Default constructor
     */
    public Product() {
        this.createdAt = LocalDateTime.now();
        this.price = BigDecimal.ZERO;
    }
    
    /**
     * Constructor with parameters
     */
    public Product(String name, String description, BigDecimal price) {
        this();
        this.name = name;
        this.description = description;
        this.price = price != null ? price : BigDecimal.ZERO;
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
     * Get description
     */
    public String getDescription() {
        return description;
    }
    
    /**
     * Set description
     */
    public void setDescription(String description) {
        this.description = description;
    }
    
    /**
     * Get price
     */
    public BigDecimal getPrice() {
        return price;
    }
    
    /**
     * Set price
     */
    public void setPrice(BigDecimal price) {
        this.price = price != null ? price : BigDecimal.ZERO;
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
        Product product = (Product) obj;
        return Objects.equals(name, product.name) && 
               Objects.equals(description, product.description) && 
               Objects.equals(price, product.price);
    }
    
    @Override
    public int hashCode() {
        return Objects.hash(name, description, price);
    }
    
    @Override
    public String toString() {
        return "Product{name='" + name + "', description='" + description + 
               "', price=" + price + ", createdAt=" + createdAt + "}";
    }
}
