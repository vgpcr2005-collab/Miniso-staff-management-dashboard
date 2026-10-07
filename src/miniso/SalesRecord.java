package miniso;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;

public class SalesRecord {
    private String transactionId;
    private String staffId;
    private String productId;
    private String productName;
    private int quantity;
    private double unitPrice;
    private double discount;
    private double totalAmount;
    private LocalDate saleDate;

    public SalesRecord(String staffId, LocalDate saleDate, double amount) {
        this("TX-" + System.currentTimeMillis(), staffId, "", "", 1, amount, 0.0, amount, saleDate);
    }

    public SalesRecord(String transactionId, String staffId, String productId, String productName,
                      int quantity, double unitPrice, double discount, double totalAmount, LocalDate saleDate) {
        this.transactionId = transactionId == null || transactionId.trim().isEmpty() ? "TX-" + System.currentTimeMillis() : transactionId.trim();
        this.staffId = staffId;
        this.productId = productId == null ? "" : productId.trim();
        this.productName = productName == null ? "" : productName.trim();
        this.quantity = Math.max(1, quantity);
        this.unitPrice = unitPrice;
        this.discount = discount;
        this.totalAmount = totalAmount;
        this.saleDate = saleDate;
    }

    public String getTransactionId() {
        return transactionId;
    }

    public void setTransactionId(String transactionId) {
        this.transactionId = transactionId;
    }

    public String getStaffId() {
        return staffId;
    }

    public void setStaffId(String staffId) {
        this.staffId = staffId;
    }

    public String getProductId() {
        return productId;
    }

    public void setProductId(String productId) {
        this.productId = productId;
    }

    public String getProductName() {
        return productName;
    }

    public void setProductName(String productName) {
        this.productName = productName;
    }

    public int getQuantity() {
        return quantity;
    }

    public void setQuantity(int quantity) {
        this.quantity = Math.max(1, quantity);
    }

    public double getUnitPrice() {
        return unitPrice;
    }

    public void setUnitPrice(double unitPrice) {
        this.unitPrice = unitPrice;
    }

    public double getDiscount() {
        return discount;
    }

    public void setDiscount(double discount) {
        this.discount = discount;
    }

    public double getTotalAmount() {
        return totalAmount;
    }

    public void setTotalAmount(double totalAmount) {
        this.totalAmount = totalAmount;
    }

    public LocalDate getSaleDate() {
        return saleDate;
    }

    public void setSaleDate(LocalDate saleDate) {
        this.saleDate = saleDate;
    }

    public double getAmount() {
        return totalAmount;
    }

    public void setAmount(double amount) {
        this.totalAmount = amount;
    }

    public String toFileString() {
        return transactionId + "," + staffId + "," + productId + "," + productName + "," + quantity + ","
                + unitPrice + "," + discount + "," + totalAmount + "," + saleDate.format(DateTimeFormatter.ISO_LOCAL_DATE);
    }

    public static SalesRecord fromFileString(String line) {
        if (line == null || line.trim().isEmpty()) {
            return null;
        }

        String[] parts = line.split(",", -1);
        if (parts.length == 3) {
            String staffId = parts[0].trim();
            LocalDate date = LocalDate.parse(parts[1].trim());
            double amount = Double.parseDouble(parts[2].trim());
            return new SalesRecord(staffId, date, amount);
        }

        if (parts.length >= 9) {
            String transactionId = parts[0].trim();
            String staffId = parts[1].trim();
            String productId = parts[2].trim();
            String productName = parts[3].trim();
            int quantity = Integer.parseInt(parts[4].trim());
            double unitPrice = Double.parseDouble(parts[5].trim());
            double discount = Double.parseDouble(parts[6].trim());
            double totalAmount = Double.parseDouble(parts[7].trim());
            LocalDate date = LocalDate.parse(parts[8].trim());
            return new SalesRecord(transactionId, staffId, productId, productName, quantity, unitPrice, discount, totalAmount, date);
        }

        return null;
    }
}
