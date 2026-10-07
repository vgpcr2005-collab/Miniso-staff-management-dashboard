package miniso;

public class Product {
    private String id;
    private String name;
    private String category;
    private double price;
    private int stock;
    private String status;

    public Product(String id, String name, String category, double price, int stock, String status) {
        this.id = id;
        this.name = name;
        this.category = category;
        this.price = price;
        this.stock = stock;
        this.status = status == null || status.trim().isEmpty() ? "Active" : status.trim();
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getCategory() {
        return category;
    }

    public void setCategory(String category) {
        this.category = category;
    }

    public double getPrice() {
        return price;
    }

    public void setPrice(double price) {
        this.price = price;
    }

    public int getStock() {
        return stock;
    }

    public void setStock(int stock) {
        this.stock = stock;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status == null || status.trim().isEmpty() ? "Active" : status.trim();
    }

    public String toFileString() {
        return id + "," + name + "," + category + "," + price + "," + stock + "," + status;
    }

    public static Product fromFileString(String line) {
        if (line == null || line.trim().isEmpty()) {
            return null;
        }

        String[] parts = line.split(",", -1);
        if (parts.length < 6) {
            return null;
        }

        return new Product(
                parts[0].trim(),
                parts[1].trim(),
                parts[2].trim(),
                Double.parseDouble(parts[3].trim()),
                Integer.parseInt(parts[4].trim()),
                parts[5].trim()
        );
    }
}
