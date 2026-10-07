package miniso;

import java.awt.*;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.List;
import javax.swing.*;
import javax.swing.table.DefaultTableModel;

public class MainFrame extends JFrame {
    private final StorageManager storageManager;
    private final List<Staff> staffList;
    private final List<Product> productList;
    private final List<SalesRecord> salesList;
    private IncentiveRule currentRule;

    private final DefaultTableModel staffTableModel;
    private final DefaultTableModel productTableModel;
    private final DefaultTableModel salesTableModel;
    private final DefaultTableModel performanceTableModel;

    private final JTextField staffIdField;
    private final JTextField staffNameField;
    private final JTextField departmentField;
    private final JTextField designationField;
    private final JTextField storeIdField;
    private final JTextField targetField;

    private final JTextField productIdField;
    private final JTextField productNameField;
    private final JTextField categoryField;
    private final JTextField priceField;
    private final JTextField stockField;

    private final JComboBox<String> staffComboBox;
    private final JComboBox<String> productComboBox;
    private final JTextField quantityField;
    private final JTextField unitPriceField;
    private final JTextField discountField;
    private final JTextField salesDateField;

    private final JTextField excellentThresholdField;
    private final JTextField goodThresholdField;
    private final JTextField averageThresholdField;
    private final JTextField excellentRateField;
    private final JTextField goodRateField;
    private final JTextField averageRateField;

    private final JTextArea reportArea;
    private JTable staffTable;
    private JTable productTable;
    private JTable salesTable;
    private JTable performanceTable;

    public MainFrame() {
        super("MINISO Staff Performance & Incentive Management");
        this.storageManager = new StorageManager("data");
        this.staffList = storageManager.loadStaffs();
        this.productList = storageManager.loadProducts();
        this.salesList = storageManager.loadSales();
        this.currentRule = storageManager.loadRule();

        if (staffList.isEmpty()) {
            seedSampleStaffData();
        }
        if (productList.isEmpty()) {
            seedSampleProductData();
        }
        if (salesList.isEmpty()) {
            seedSampleSalesData();
        }

        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setSize(1300, 820);
        setLocationRelativeTo(null);

        staffTableModel = new DefaultTableModel(new Object[]{"Staff ID", "Name", "Department", "Designation", "Store", "Status", "Target"}, 0) {
            @Override
            public boolean isCellEditable(int row, int column) {
                return false;
            }
        };

        productTableModel = new DefaultTableModel(new Object[]{"Product ID", "Name", "Category", "Price", "Stock", "Status"}, 0) {
            @Override
            public boolean isCellEditable(int row, int column) {
                return false;
            }
        };

        salesTableModel = new DefaultTableModel(new Object[]{"Transaction ID", "Staff ID", "Staff Name", "Product", "Qty", "Total", "Date"}, 0) {
            @Override
            public boolean isCellEditable(int row, int column) {
                return false;
            }
        };

        performanceTableModel = new DefaultTableModel(new Object[]{"Staff ID", "Name", "Target", "Total Sales", "Achievement %", "Performance", "Incentive"}, 0) {
            @Override
            public boolean isCellEditable(int row, int column) {
                return false;
            }
        };

        staffIdField = new JTextField();
        staffNameField = new JTextField();
        departmentField = new JTextField();
        designationField = new JTextField();
        storeIdField = new JTextField();
        targetField = new JTextField();

        productIdField = new JTextField();
        productNameField = new JTextField();
        categoryField = new JTextField();
        priceField = new JTextField();
        stockField = new JTextField();

        staffComboBox = new JComboBox<>();
        productComboBox = new JComboBox<>();
        quantityField = new JTextField("1");
        unitPriceField = new JTextField();
        discountField = new JTextField("0");
        salesDateField = new JTextField(LocalDate.now().toString());

        excellentThresholdField = new JTextField(String.valueOf(currentRule.getExcellentThreshold()));
        goodThresholdField = new JTextField(String.valueOf(currentRule.getGoodThreshold()));
        averageThresholdField = new JTextField(String.valueOf(currentRule.getAverageThreshold()));
        excellentRateField = new JTextField(String.valueOf(currentRule.getExcellentIncentive()));
        goodRateField = new JTextField(String.valueOf(currentRule.getGoodIncentive()));
        averageRateField = new JTextField(String.valueOf(currentRule.getAverageIncentive()));
        reportArea = new JTextArea();
        reportArea.setEditable(false);

        JTabbedPane tabbedPane = new JTabbedPane();
        tabbedPane.addTab("Staff Management", createStaffPanel());
        tabbedPane.addTab("Product Management", createProductPanel());
        tabbedPane.addTab("Sales Management", createSalesPanel());
        tabbedPane.addTab("Performance & Incentive", createPerformancePanel());
        tabbedPane.addTab("Reports", createReportPanel());

        add(tabbedPane, BorderLayout.CENTER);
        refreshStaffTable();
        refreshProductTable();
        refreshSalesTable();
        refreshPerformanceTable();
        refreshReport();
        refreshStaffCombo();
        refreshProductCombo();
    }

    private void seedSampleStaffData() {
        staffList.add(new Staff("S101", "Harsha", "Sales", "Sales Executive", "STORE01", "Active", 100000));
        staffList.add(new Staff("S102", "Rahul", "Sales", "Senior Sales", "STORE01", "Active", 90000));
        staffList.add(new Staff("S103", "Priya", "Sales", "Sales Executive", "STORE01", "Active", 110000));
        staffList.add(new Staff("S104", "Ankit", "Store", "Store Associate", "STORE01", "Active", 75000));
        saveStaffs();
    }

    private void seedSampleProductData() {
        productList.add(new Product("P001", "Water Bottle", "Lifestyle", 299, 120, "Active"));
        productList.add(new Product("P002", "Toy Set", "Kids", 499, 80, "Active"));
        productList.add(new Product("P003", "Travel Bag", "Accessories", 850, 40, "Active"));
        productList.add(new Product("P004", "Beauty Kit", "Beauty", 1200, 35, "Active"));
        saveProducts();
    }

    private void seedSampleSalesData() {
        salesList.add(new SalesRecord("TX-001", "S101", "P001", "Water Bottle", 2, 299, 0, 598, LocalDate.now().minusDays(3)));
        salesList.add(new SalesRecord("TX-002", "S101", "P003", "Travel Bag", 1, 850, 50, 800, LocalDate.now().minusDays(2)));
        salesList.add(new SalesRecord("TX-003", "S102", "P002", "Toy Set", 3, 499, 0, 1497, LocalDate.now().minusDays(1)));
        salesList.add(new SalesRecord("TX-004", "S103", "P004", "Beauty Kit", 1, 1200, 100, 1100, LocalDate.now().minusDays(4)));
        saveSales();
    }

    private JPanel createStaffPanel() {
        JPanel panel = new JPanel(new BorderLayout(10, 10));
        panel.setBorder(BorderFactory.createEmptyBorder(12, 12, 12, 12));

        JPanel formPanel = new JPanel(new GridBagLayout());
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.insets = new Insets(5, 5, 5, 5);
        gbc.fill = GridBagConstraints.HORIZONTAL;

        addField(formPanel, gbc, 0, 0, "Staff ID:", staffIdField);
        addField(formPanel, gbc, 0, 1, "Name:", staffNameField);
        addField(formPanel, gbc, 0, 2, "Department:", departmentField);
        addField(formPanel, gbc, 0, 3, "Designation:", designationField);
        addField(formPanel, gbc, 0, 4, "Store ID:", storeIdField);
        addField(formPanel, gbc, 0, 5, "Target:", targetField);

        JPanel buttonPanel = new JPanel(new FlowLayout(FlowLayout.LEFT));
        JButton addButton = new JButton("Add Staff");
        JButton deleteButton = new JButton("Delete Selected");
        JButton clearButton = new JButton("Clear");

        addButton.addActionListener(e -> addStaff());
        deleteButton.addActionListener(e -> deleteSelectedStaff());
        clearButton.addActionListener(e -> clearStaffForm());

        buttonPanel.add(addButton);
        buttonPanel.add(deleteButton);
        buttonPanel.add(clearButton);
        formPanel.add(buttonPanel, new GridBagConstraints(0, 6, 2, 1, 1, 0,
                GridBagConstraints.LINE_START, GridBagConstraints.HORIZONTAL, new Insets(10, 5, 5, 5), 0, 0));

        staffTable = new JTable(staffTableModel);
        JScrollPane scrollPane = new JScrollPane(staffTable);

        panel.add(formPanel, BorderLayout.NORTH);
        panel.add(scrollPane, BorderLayout.CENTER);
        return panel;
    }

    private JPanel createProductPanel() {
        JPanel panel = new JPanel(new BorderLayout(10, 10));
        panel.setBorder(BorderFactory.createEmptyBorder(12, 12, 12, 12));

        JPanel formPanel = new JPanel(new GridBagLayout());
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.insets = new Insets(5, 5, 5, 5);
        gbc.fill = GridBagConstraints.HORIZONTAL;

        addField(formPanel, gbc, 0, 0, "Product ID:", productIdField);
        addField(formPanel, gbc, 0, 1, "Product Name:", productNameField);
        addField(formPanel, gbc, 0, 2, "Category:", categoryField);
        addField(formPanel, gbc, 0, 3, "Price:", priceField);
        addField(formPanel, gbc, 0, 4, "Stock:", stockField);

        JPanel buttonPanel = new JPanel(new FlowLayout(FlowLayout.LEFT));
        JButton addButton = new JButton("Add Product");
        JButton deleteButton = new JButton("Delete Selected");
        JButton clearButton = new JButton("Clear");

        addButton.addActionListener(e -> addProduct());
        deleteButton.addActionListener(e -> deleteSelectedProduct());
        clearButton.addActionListener(e -> clearProductForm());

        buttonPanel.add(addButton);
        buttonPanel.add(deleteButton);
        buttonPanel.add(clearButton);
        formPanel.add(buttonPanel, new GridBagConstraints(0, 5, 2, 1, 1, 0,
                GridBagConstraints.LINE_START, GridBagConstraints.HORIZONTAL, new Insets(10, 5, 5, 5), 0, 0));

        productTable = new JTable(productTableModel);
        JScrollPane scrollPane = new JScrollPane(productTable);

        panel.add(formPanel, BorderLayout.NORTH);
        panel.add(scrollPane, BorderLayout.CENTER);
        return panel;
    }

    private JPanel createSalesPanel() {
        JPanel panel = new JPanel(new BorderLayout(10, 10));
        panel.setBorder(BorderFactory.createEmptyBorder(12, 12, 12, 12));

        JPanel formPanel = new JPanel(new GridBagLayout());
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.insets = new Insets(5, 5, 5, 5);
        gbc.fill = GridBagConstraints.HORIZONTAL;

        addField(formPanel, gbc, 0, 0, "Staff:", staffComboBox);
        addField(formPanel, gbc, 0, 1, "Product:", productComboBox);
        addField(formPanel, gbc, 0, 2, "Quantity:", quantityField);
        addField(formPanel, gbc, 0, 3, "Unit Price:", unitPriceField);
        addField(formPanel, gbc, 0, 4, "Discount:", discountField);
        addField(formPanel, gbc, 0, 5, "Sale Date (yyyy-MM-dd):", salesDateField);

        JPanel buttonPanel = new JPanel(new FlowLayout(FlowLayout.LEFT));
        JButton addSaleButton = new JButton("Add Sale");
        JButton refreshButton = new JButton("Refresh");

        addSaleButton.addActionListener(e -> addSalesRecord());
        refreshButton.addActionListener(e -> refreshSalesTable());

        buttonPanel.add(addSaleButton);
        buttonPanel.add(refreshButton);
        formPanel.add(buttonPanel, new GridBagConstraints(0, 6, 2, 1, 1, 0,
                GridBagConstraints.LINE_START, GridBagConstraints.HORIZONTAL, new Insets(10, 5, 5, 5), 0, 0));

        salesTable = new JTable(salesTableModel);
        JScrollPane scrollPane = new JScrollPane(salesTable);

        panel.add(formPanel, BorderLayout.NORTH);
        panel.add(scrollPane, BorderLayout.CENTER);
        return panel;
    }

    private JPanel createPerformancePanel() {
        JPanel panel = new JPanel(new BorderLayout(10, 10));
        panel.setBorder(BorderFactory.createEmptyBorder(12, 12, 12, 12));

        JPanel rulePanel = new JPanel(new GridBagLayout());
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.insets = new Insets(5, 5, 5, 5);
        gbc.fill = GridBagConstraints.HORIZONTAL;

        addField(rulePanel, gbc, 0, 0, "Excellent >=:", excellentThresholdField);
        addField(rulePanel, gbc, 1, 0, "Excellent Bonus:", excellentRateField);
        addField(rulePanel, gbc, 0, 1, "Good >=:", goodThresholdField);
        addField(rulePanel, gbc, 1, 1, "Good Bonus:", goodRateField);
        addField(rulePanel, gbc, 0, 2, "Average >=:", averageThresholdField);
        addField(rulePanel, gbc, 1, 2, "Average Bonus:", averageRateField);

        JPanel buttons = new JPanel(new FlowLayout(FlowLayout.LEFT));
        JButton applyButton = new JButton("Apply Rule");
        JButton calculateButton = new JButton("Calculate Performance");

        applyButton.addActionListener(e -> applyRule());
        calculateButton.addActionListener(e -> refreshPerformanceTable());

        buttons.add(applyButton);
        buttons.add(calculateButton);
        rulePanel.add(buttons, new GridBagConstraints(0, 3, 2, 1, 1, 0,
                GridBagConstraints.LINE_START, GridBagConstraints.HORIZONTAL, new Insets(10, 5, 5, 5), 0, 0));

        performanceTable = new JTable(performanceTableModel);
        JScrollPane scrollPane = new JScrollPane(performanceTable);

        panel.add(rulePanel, BorderLayout.NORTH);
        panel.add(scrollPane, BorderLayout.CENTER);
        return panel;
    }

    private JPanel createReportPanel() {
        JPanel panel = new JPanel(new BorderLayout(10, 10));
        panel.setBorder(BorderFactory.createEmptyBorder(12, 12, 12, 12));

        JButton refreshButton = new JButton("Generate Report");
        refreshButton.addActionListener(e -> refreshReport());

        panel.add(refreshButton, BorderLayout.NORTH);
        JScrollPane scrollPane = new JScrollPane(reportArea);
        panel.add(scrollPane, BorderLayout.CENTER);
        return panel;
    }

    private void addField(Container container, GridBagConstraints gbc, int x, int y, String labelText, JComponent field) {
        JLabel label = new JLabel(labelText);
        gbc.gridx = x * 2;
        gbc.gridy = y;
        gbc.weightx = 0.15;
        container.add(label, gbc);

        gbc.gridx = x * 2 + 1;
        gbc.weightx = 0.85;
        container.add(field, gbc);
    }

    private void addStaff() {
        String id = staffIdField.getText().trim();
        String name = staffNameField.getText().trim();
        String department = departmentField.getText().trim();
        String designation = designationField.getText().trim();
        String storeId = storeIdField.getText().trim();
        String targetText = targetField.getText().trim();

        if (id.isEmpty() || name.isEmpty() || department.isEmpty() || targetText.isEmpty()) {
            JOptionPane.showMessageDialog(this, "Please fill all required staff details.", "Validation Error", JOptionPane.WARNING_MESSAGE);
            return;
        }

        try {
            double target = Double.parseDouble(targetText);
            if (target <= 0) {
                throw new NumberFormatException();
            }

            Staff existing = findStaffById(id);
            if (existing != null) {
                existing.setName(name);
                existing.setDepartment(department);
                existing.setDesignation(designation);
                existing.setStoreId(storeId);
                existing.setTarget(target);
            } else {
                staffList.add(new Staff(id, name, department, designation, storeId, "Active", target));
            }

            saveStaffs();
            refreshStaffTable();
            refreshStaffCombo();
            clearStaffForm();
            refreshReport();
        } catch (NumberFormatException ex) {
            JOptionPane.showMessageDialog(this, "Target must be a valid positive number.", "Invalid Input", JOptionPane.ERROR_MESSAGE);
        }
    }

    private void deleteSelectedStaff() {
        if (staffTable == null || staffTable.getSelectedRow() < 0) {
            JOptionPane.showMessageDialog(this, "Please select a staff row to delete.", "Delete Staff", JOptionPane.WARNING_MESSAGE);
            return;
        }

        String selectedId = String.valueOf(staffTableModel.getValueAt(staffTable.getSelectedRow(), 0));
        staffList.removeIf(staff -> staff.getId().equalsIgnoreCase(selectedId));
        salesList.removeIf(record -> record.getStaffId().equalsIgnoreCase(selectedId));

        saveStaffs();
        saveSales();
        refreshStaffTable();
        refreshSalesTable();
        refreshStaffCombo();
        refreshPerformanceTable();
        refreshReport();
    }

    private void clearStaffForm() {
        staffIdField.setText("");
        staffNameField.setText("");
        departmentField.setText("");
        designationField.setText("");
        storeIdField.setText("");
        targetField.setText("");
    }

    private void addProduct() {
        String id = productIdField.getText().trim();
        String name = productNameField.getText().trim();
        String category = categoryField.getText().trim();
        String priceText = priceField.getText().trim();
        String stockText = stockField.getText().trim();

        if (id.isEmpty() || name.isEmpty() || category.isEmpty() || priceText.isEmpty() || stockText.isEmpty()) {
            JOptionPane.showMessageDialog(this, "Please fill all product details.", "Validation Error", JOptionPane.WARNING_MESSAGE);
            return;
        }

        try {
            double price = Double.parseDouble(priceText);
            int stock = Integer.parseInt(stockText);
            if (price <= 0 || stock < 0) {
                throw new NumberFormatException();
            }

            Product existing = findProductById(id);
            if (existing != null) {
                existing.setName(name);
                existing.setCategory(category);
                existing.setPrice(price);
                existing.setStock(stock);
            } else {
                productList.add(new Product(id, name, category, price, stock, "Active"));
            }

            saveProducts();
            refreshProductTable();
            refreshProductCombo();
            clearProductForm();
        } catch (NumberFormatException ex) {
            JOptionPane.showMessageDialog(this, "Price must be positive and stock must be non-negative.", "Invalid Product", JOptionPane.ERROR_MESSAGE);
        }
    }

    private void deleteSelectedProduct() {
        if (productTable == null || productTable.getSelectedRow() < 0) {
            JOptionPane.showMessageDialog(this, "Please select a product row to delete.", "Delete Product", JOptionPane.WARNING_MESSAGE);
            return;
        }

        String selectedId = String.valueOf(productTableModel.getValueAt(productTable.getSelectedRow(), 0));
        productList.removeIf(product -> product.getId().equalsIgnoreCase(selectedId));
        salesList.removeIf(record -> record.getProductId().equalsIgnoreCase(selectedId));

        saveProducts();
        saveSales();
        refreshProductTable();
        refreshProductCombo();
        refreshSalesTable();
        refreshPerformanceTable();
        refreshReport();
    }

    private void clearProductForm() {
        productIdField.setText("");
        productNameField.setText("");
        categoryField.setText("");
        priceField.setText("");
        stockField.setText("");
    }

    private void addSalesRecord() {
        String staffId = (String) staffComboBox.getSelectedItem();
        String productId = (String) productComboBox.getSelectedItem();
        String quantityText = quantityField.getText().trim();
        String unitPriceText = unitPriceField.getText().trim();
        String discountText = discountField.getText().trim();
        String dateText = salesDateField.getText().trim();

        if (staffId == null || productId == null || quantityText.isEmpty() || unitPriceText.isEmpty() || dateText.isEmpty()) {
            JOptionPane.showMessageDialog(this, "Please fill all sales details.", "Validation Error", JOptionPane.WARNING_MESSAGE);
            return;
        }

        try {
            int quantity = Integer.parseInt(quantityText);
            double unitPrice = Double.parseDouble(unitPriceText);
            double discount = Double.parseDouble(discountText);
            if (quantity <= 0 || unitPrice <= 0 || discount < 0) {
                throw new NumberFormatException();
            }

            LocalDate saleDate = LocalDate.parse(dateText);
            Product product = findProductById(productId);
            String productName = product != null ? product.getName() : "Unknown";
            double subtotal = quantity * unitPrice;
            double totalAmount = Math.max(0, subtotal - discount);

            SalesRecord sale = new SalesRecord(
                    "TX-" + System.currentTimeMillis(),
                    staffId,
                    productId,
                    productName,
                    quantity,
                    unitPrice,
                    discount,
                    totalAmount,
                    saleDate
            );

            salesList.add(sale);
            if (product != null) {
                product.setStock(Math.max(0, product.getStock() - quantity));
            }

            saveSales();
            saveProducts();
            refreshSalesTable();
            refreshProductTable();
            refreshPerformanceTable();
            refreshReport();
            quantityField.setText("1");
            unitPriceField.setText("");
            discountField.setText("0");
            salesDateField.setText(LocalDate.now().toString());
        } catch (NumberFormatException e) {
            JOptionPane.showMessageDialog(this, "Quantity, unit price and discount must be valid numbers.", "Invalid Input", JOptionPane.ERROR_MESSAGE);
        } catch (DateTimeParseException e) {
            JOptionPane.showMessageDialog(this, "Date must be in yyyy-MM-dd format.", "Invalid Date", JOptionPane.ERROR_MESSAGE);
        }
    }

    private void applyRule() {
        try {
            double excellentThreshold = Double.parseDouble(excellentThresholdField.getText().trim());
            double goodThreshold = Double.parseDouble(goodThresholdField.getText().trim());
            double averageThreshold = Double.parseDouble(averageThresholdField.getText().trim());
            double excellentRate = Double.parseDouble(excellentRateField.getText().trim());
            double goodRate = Double.parseDouble(goodRateField.getText().trim());
            double averageRate = Double.parseDouble(averageRateField.getText().trim());

            if (excellentThreshold < goodThreshold || goodThreshold < averageThreshold) {
                JOptionPane.showMessageDialog(this, "Threshold values should be in descending order: Excellent >= Good >= Average.", "Rule Validation", JOptionPane.WARNING_MESSAGE);
                return;
            }

            currentRule = new IncentiveRule(excellentThreshold, goodThreshold, averageThreshold, excellentRate, goodRate, averageRate);
            try {
                storageManager.saveRule(currentRule);
            } catch (Exception ex) {
                JOptionPane.showMessageDialog(this, "Unable to save rules: " + ex.getMessage(), "Save Error", JOptionPane.ERROR_MESSAGE);
            }
            refreshPerformanceTable();
            refreshReport();
        } catch (NumberFormatException e) {
            JOptionPane.showMessageDialog(this, "All incentive values must be valid numbers.", "Invalid Rule", JOptionPane.ERROR_MESSAGE);
        }
    }

    private void refreshStaffTable() {
        staffTableModel.setRowCount(0);
        for (Staff staff : staffList) {
            staffTableModel.addRow(new Object[]{staff.getId(), staff.getName(), staff.getDepartment(), staff.getDesignation(), staff.getStoreId(), staff.getStatus(), staff.getTarget()});
        }
    }

    private void refreshProductTable() {
        productTableModel.setRowCount(0);
        for (Product product : productList) {
            productTableModel.addRow(new Object[]{product.getId(), product.getName(), product.getCategory(), product.getPrice(), product.getStock(), product.getStatus()});
        }
    }

    private void refreshSalesTable() {
        salesTableModel.setRowCount(0);
        for (SalesRecord sale : salesList) {
            String staffName = findStaffById(sale.getStaffId()) != null ? findStaffById(sale.getStaffId()).getName() : "Unknown";
            String productName = sale.getProductName() == null || sale.getProductName().isEmpty() ? "Manual Sale" : sale.getProductName();
            salesTableModel.addRow(new Object[]{sale.getTransactionId(), sale.getStaffId(), staffName, productName, sale.getQuantity(), sale.getTotalAmount(), sale.getSaleDate()});
        }
    }

    private void refreshPerformanceTable() {
        performanceTableModel.setRowCount(0);
        for (Staff staff : staffList) {
            double totalSales = 0;
            for (SalesRecord sale : salesList) {
                if (sale.getStaffId().equalsIgnoreCase(staff.getId())) {
                    totalSales += sale.getTotalAmount();
                }
            }

            double achievement = PerformanceCalculator.calculateAchievement(totalSales, staff.getTarget());
            String performance = PerformanceCalculator.getPerformanceLevel(achievement);
            double incentive = PerformanceCalculator.calculateIncentive(achievement, currentRule);

            performanceTableModel.addRow(new Object[]{
                    staff.getId(),
                    staff.getName(),
                    staff.getTarget(),
                    totalSales,
                    String.format("%.2f%%", achievement),
                    performance,
                    String.format("%.2f", incentive)
            });
        }
    }

    private void refreshReport() {
        StringBuilder report = new StringBuilder();
        report.append("MINISO Staff Performance & Incentive Report\n");
        report.append("========================================\n\n");

        if (staffList.isEmpty()) {
            report.append("No staff members registered yet.\n");
        } else {
            for (Staff staff : staffList) {
                double totalSales = 0;
                for (SalesRecord sale : salesList) {
                    if (sale.getStaffId().equalsIgnoreCase(staff.getId())) {
                        totalSales += sale.getTotalAmount();
                    }
                }

                double achievement = PerformanceCalculator.calculateAchievement(totalSales, staff.getTarget());
                String performance = PerformanceCalculator.getPerformanceLevel(achievement);
                double incentive = PerformanceCalculator.calculateIncentive(achievement, currentRule);

                report.append("Staff ID: ").append(staff.getId()).append("\n");
                report.append("Name: ").append(staff.getName()).append("\n");
                report.append("Department: ").append(staff.getDepartment()).append("\n");
                report.append("Designation: ").append(staff.getDesignation()).append("\n");
                report.append("Store: ").append(staff.getStoreId()).append("\n");
                report.append("Target: ").append(String.format("%.2f", staff.getTarget())).append("\n");
                report.append("Total Sales: ").append(String.format("%.2f", totalSales)).append("\n");
                report.append("Target Achievement: ").append(String.format("%.2f%%", achievement)).append("\n");
                report.append("Performance: ").append(performance).append("\n");
                report.append("Incentive: ").append(String.format("%.2f", incentive)).append("\n\n");
            }
        }

        reportArea.setText(report.toString());
    }

    private void refreshStaffCombo() {
        staffComboBox.removeAllItems();
        for (Staff staff : staffList) {
            staffComboBox.addItem(staff.getId());
        }
        if (staffComboBox.getItemCount() > 0) {
            staffComboBox.setSelectedIndex(0);
        }
    }

    private void refreshProductCombo() {
        productComboBox.removeAllItems();
        for (Product product : productList) {
            productComboBox.addItem(product.getId());
        }
        if (productComboBox.getItemCount() > 0) {
            productComboBox.setSelectedIndex(0);
        }
    }

    private Staff findStaffById(String staffId) {
        for (Staff staff : staffList) {
            if (staff.getId().equalsIgnoreCase(staffId)) {
                return staff;
            }
        }
        return null;
    }

    private Product findProductById(String productId) {
        for (Product product : productList) {
            if (product.getId().equalsIgnoreCase(productId)) {
                return product;
            }
        }
        return null;
    }

    private void saveStaffs() {
        try {
            storageManager.saveStaffs(staffList);
        } catch (Exception e) {
            JOptionPane.showMessageDialog(this, "Unable to save staff data. " + e.getMessage(), "Save Error", JOptionPane.ERROR_MESSAGE);
        }
    }

    private void saveProducts() {
        try {
            storageManager.saveProducts(productList);
        } catch (Exception e) {
            JOptionPane.showMessageDialog(this, "Unable to save product data. " + e.getMessage(), "Save Error", JOptionPane.ERROR_MESSAGE);
        }
    }

    private void saveSales() {
        try {
            storageManager.saveSales(salesList);
        } catch (Exception e) {
            JOptionPane.showMessageDialog(this, "Unable to save sales data. " + e.getMessage(), "Save Error", JOptionPane.ERROR_MESSAGE);
        }
    }
}
