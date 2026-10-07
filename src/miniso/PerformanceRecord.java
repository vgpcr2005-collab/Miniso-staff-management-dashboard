package miniso;

public class PerformanceRecord {
    private String staffId;
    private String staffName;
    private double target;
    private double totalSales;
    private double achievement;
    private String performanceLevel;
    private double incentive;

    public PerformanceRecord(String staffId, String staffName, double target, double totalSales,
                            double achievement, String performanceLevel, double incentive) {
        this.staffId = staffId;
        this.staffName = staffName;
        this.target = target;
        this.totalSales = totalSales;
        this.achievement = achievement;
        this.performanceLevel = performanceLevel;
        this.incentive = incentive;
    }

    public String getStaffId() {
        return staffId;
    }

    public String getStaffName() {
        return staffName;
    }

    public double getTarget() {
        return target;
    }

    public double getTotalSales() {
        return totalSales;
    }

    public double getAchievement() {
        return achievement;
    }

    public String getPerformanceLevel() {
        return performanceLevel;
    }

    public double getIncentive() {
        return incentive;
    }
}
