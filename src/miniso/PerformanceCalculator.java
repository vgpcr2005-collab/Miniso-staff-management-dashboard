package miniso;

public class PerformanceCalculator {

    public static double calculateAchievement(double totalSales, double target) {
        if (target <= 0) {
            return 0;
        }
        return (totalSales / target) * 100;
    }

    public static double calculateTarget(double previousSales, double growthPercent) {
        if (previousSales < 0) {
            return 0;
        }
        return previousSales * (1 + (growthPercent / 100.0));
    }

    public static String getPerformanceLevel(double achievement) {
        if (achievement >= 110) {
            return "Outstanding";
        }
        if (achievement >= 100) {
            return "Excellent";
        }
        if (achievement >= 90) {
            return "Good";
        }
        if (achievement >= 80) {
            return "Below Target";
        }
        return "Needs Improvement";
    }

    public static double calculateIncentive(double achievement, IncentiveRule rule) {
        if (rule == null) {
            rule = new IncentiveRule();
        }

        if (achievement >= rule.getExcellentThreshold()) {
            return rule.getExcellentIncentive();
        }
        if (achievement >= rule.getGoodThreshold()) {
            return rule.getGoodIncentive();
        }
        if (achievement >= rule.getAverageThreshold()) {
            return rule.getAverageIncentive();
        }
        if (achievement >= 80) {
            return rule.getBelowTargetIncentive();
        }
        return 0;
    }
}
