package miniso;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;

public class StorageManager {
    private final Path dataDirectory;

    public StorageManager(String folderPath) {
        this.dataDirectory = Paths.get(folderPath);
        try {
            Files.createDirectories(this.dataDirectory);
        } catch (IOException e) {
            throw new RuntimeException("Unable to create data directory", e);
        }
    }

    public void saveStaffs(List<Staff> staffList) throws IOException {
        Path file = dataDirectory.resolve("staffs.txt");
        List<String> lines = new ArrayList<>();
        for (Staff staff : staffList) {
            lines.add(staff.toFileString());
        }
        Files.write(file, lines);
    }

    public List<Staff> loadStaffs() {
        Path file = dataDirectory.resolve("staffs.txt");
        List<Staff> staffList = new ArrayList<>();

        if (!Files.exists(file)) {
            return staffList;
        }

        try {
            List<String> lines = Files.readAllLines(file);
            for (String line : lines) {
                if (line == null || line.trim().isEmpty()) {
                    continue;
                }
                Staff staff = Staff.fromFileString(line);
                if (staff != null) {
                    staffList.add(staff);
                }
            }
        } catch (IOException e) {
            System.err.println("Failed to load staff data: " + e.getMessage());
        }

        return staffList;
    }

    public void saveSales(List<SalesRecord> salesList) throws IOException {
        Path file = dataDirectory.resolve("sales.txt");
        List<String> lines = new ArrayList<>();
        for (SalesRecord sale : salesList) {
            lines.add(sale.toFileString());
        }
        Files.write(file, lines);
    }

    public List<SalesRecord> loadSales() {
        Path file = dataDirectory.resolve("sales.txt");
        List<SalesRecord> salesList = new ArrayList<>();

        if (!Files.exists(file)) {
            return salesList;
        }

        try {
            List<String> lines = Files.readAllLines(file);
            for (String line : lines) {
                if (line == null || line.trim().isEmpty()) {
                    continue;
                }
                SalesRecord sale = SalesRecord.fromFileString(line);
                if (sale != null) {
                    salesList.add(sale);
                }
            }
        } catch (IOException e) {
            System.err.println("Failed to load sales data: " + e.getMessage());
        }

        return salesList;
    }

    public void saveProducts(List<Product> productList) throws IOException {
        Path file = dataDirectory.resolve("products.txt");
        List<String> lines = new ArrayList<>();
        for (Product product : productList) {
            lines.add(product.toFileString());
        }
        Files.write(file, lines);
    }

    public List<Product> loadProducts() {
        Path file = dataDirectory.resolve("products.txt");
        List<Product> productList = new ArrayList<>();

        if (!Files.exists(file)) {
            return productList;
        }

        try {
            List<String> lines = Files.readAllLines(file);
            for (String line : lines) {
                if (line == null || line.trim().isEmpty()) {
                    continue;
                }
                Product product = Product.fromFileString(line);
                if (product != null) {
                    productList.add(product);
                }
            }
        } catch (IOException e) {
            System.err.println("Failed to load product data: " + e.getMessage());
        }

        return productList;
    }

    public void saveRule(IncentiveRule rule) throws IOException {
        Path file = dataDirectory.resolve("rules.txt");
        Files.write(file, List.of(rule.toFileString()));
    }

    public IncentiveRule loadRule() {
        Path file = dataDirectory.resolve("rules.txt");
        if (!Files.exists(file)) {
            return new IncentiveRule();
        }

        try {
            List<String> lines = Files.readAllLines(file);
            if (lines.isEmpty()) {
                return new IncentiveRule();
            }
            return IncentiveRule.fromFileString(lines.get(0));
        } catch (IOException e) {
            System.err.println("Failed to load incentive rules: " + e.getMessage());
            return new IncentiveRule();
        }
    }
}
