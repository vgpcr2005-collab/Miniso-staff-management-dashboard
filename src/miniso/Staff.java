package miniso;

public class Staff {
    private String id;
    private String name;
    private String department;
    private String designation;
    private String storeId;
    private String status;
    private double target;

    public Staff(String id, String name, String department, double target) {
        this(id, name, department, "Sales Executive", "STORE01", "Active", target);
    }

    public Staff(String id, String name, String department, String designation, String storeId, String status, double target) {
        this.id = id;
        this.name = name;
        this.department = department;
        this.designation = designation == null || designation.trim().isEmpty() ? "Sales Executive" : designation.trim();
        this.storeId = storeId == null || storeId.trim().isEmpty() ? "STORE01" : storeId.trim();
        this.status = status == null || status.trim().isEmpty() ? "Active" : status.trim();
        this.target = target;
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

    public String getDepartment() {
        return department;
    }

    public void setDepartment(String department) {
        this.department = department;
    }

    public String getDesignation() {
        return designation;
    }

    public void setDesignation(String designation) {
        this.designation = designation == null || designation.trim().isEmpty() ? "Sales Executive" : designation.trim();
    }

    public String getStoreId() {
        return storeId;
    }

    public void setStoreId(String storeId) {
        this.storeId = storeId == null || storeId.trim().isEmpty() ? "STORE01" : storeId.trim();
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status == null || status.trim().isEmpty() ? "Active" : status.trim();
    }

    public double getTarget() {
        return target;
    }

    public void setTarget(double target) {
        this.target = target;
    }

    public String toFileString() {
        return id + "," + name + "," + department + "," + designation + "," + storeId + "," + status + "," + target;
    }

    public static Staff fromFileString(String line) {
        if (line == null || line.trim().isEmpty()) {
            return null;
        }

        String[] parts = line.split(",", -1);
        if (parts.length == 4) {
            String id = parts[0].trim();
            String name = parts[1].trim();
            String department = parts[2].trim();
            double target = Double.parseDouble(parts[3].trim());
            return new Staff(id, name, department, target);
        }

        if (parts.length >= 7) {
            String id = parts[0].trim();
            String name = parts[1].trim();
            String department = parts[2].trim();
            String designation = parts[3].trim();
            String storeId = parts[4].trim();
            String status = parts[5].trim();
            double target = Double.parseDouble(parts[6].trim());
            return new Staff(id, name, department, designation, storeId, status, target);
        }

        return null;
    }
}
