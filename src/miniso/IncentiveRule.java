package miniso;

public class IncentiveRule {
    private double excellentThreshold = 110.0;
    private double goodThreshold = 100.0;
    private double averageThreshold = 90.0;
    private double excellentIncentive = 6000.0;
    private double goodIncentive = 4000.0;
    private double averageIncentive = 2000.0;
    private double belowTargetIncentive = 1000.0;

    public IncentiveRule() {
    }

    public IncentiveRule(double excellentThreshold, double goodThreshold, double averageThreshold,
                         double excellentIncentive, double goodIncentive, double averageIncentive) {
        this.excellentThreshold = excellentThreshold;
        this.goodThreshold = goodThreshold;
        this.averageThreshold = averageThreshold;
        this.excellentIncentive = excellentIncentive;
        this.goodIncentive = goodIncentive;
        this.averageIncentive = averageIncentive;
    }

    public double getExcellentThreshold() {
        return excellentThreshold;
    }

    public void setExcellentThreshold(double excellentThreshold) {
        this.excellentThreshold = excellentThreshold;
    }

    public double getGoodThreshold() {
        return goodThreshold;
    }

    public void setGoodThreshold(double goodThreshold) {
        this.goodThreshold = goodThreshold;
    }

    public double getAverageThreshold() {
        return averageThreshold;
    }

    public void setAverageThreshold(double averageThreshold) {
        this.averageThreshold = averageThreshold;
    }

    public double getExcellentIncentive() {
        return excellentIncentive;
    }

    public void setExcellentIncentive(double excellentIncentive) {
        this.excellentIncentive = excellentIncentive;
    }

    public double getGoodIncentive() {
        return goodIncentive;
    }

    public void setGoodIncentive(double goodIncentive) {
        this.goodIncentive = goodIncentive;
    }

    public double getAverageIncentive() {
        return averageIncentive;
    }

    public void setAverageIncentive(double averageIncentive) {
        this.averageIncentive = averageIncentive;
    }

    public double getBelowTargetIncentive() {
        return belowTargetIncentive;
    }

    public void setBelowTargetIncentive(double belowTargetIncentive) {
        this.belowTargetIncentive = belowTargetIncentive;
    }

    public String toFileString() {
        return excellentThreshold + "," + goodThreshold + "," + averageThreshold + ","
                + excellentIncentive + "," + goodIncentive + "," + averageIncentive + "," + belowTargetIncentive;
    }

    public static IncentiveRule fromFileString(String line) {
        if (line == null || line.trim().isEmpty()) {
            return new IncentiveRule();
        }

        String[] values = line.split(",", -1);
        if (values.length < 6) {
            return new IncentiveRule();
        }

        try {
            double excellentThreshold = Double.parseDouble(values[0].trim());
            double goodThreshold = Double.parseDouble(values[1].trim());
            double averageThreshold = Double.parseDouble(values[2].trim());
            double excellentIncentive = Double.parseDouble(values[3].trim());
            double goodIncentive = Double.parseDouble(values[4].trim());
            double averageIncentive = Double.parseDouble(values[5].trim());
            double belowTargetIncentive = values.length > 6 ? Double.parseDouble(values[6].trim()) : 1000.0;

            IncentiveRule rule = new IncentiveRule(excellentThreshold, goodThreshold, averageThreshold,
                    excellentIncentive, goodIncentive, averageIncentive);
            rule.setBelowTargetIncentive(belowTargetIncentive);
            return rule;
        } catch (NumberFormatException e) {
            return new IncentiveRule();
        }
    }
}
