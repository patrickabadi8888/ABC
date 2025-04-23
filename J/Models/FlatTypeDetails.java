package Models;

public class FlatTypeDetails {
    private final int totalUnits;
    private int availableUnits;
    private double sellingPrice;

    public FlatTypeDetails(int totalUnits, int availableUnits, double sellingPrice) {
        if (totalUnits < 0 || availableUnits < 0 || availableUnits > totalUnits || sellingPrice < 0) {
            throw new IllegalArgumentException("Invalid FlatTypeDetails parameters: total=" + totalUnits + ", available=" + availableUnits + ", price=" + sellingPrice);
        }
        this.totalUnits = totalUnits;
        this.availableUnits = availableUnits;
        this.sellingPrice = sellingPrice;
    }

    public int getTotalUnits() { return totalUnits; }
    public int getAvailableUnits() { return availableUnits; }
    public double getSellingPrice() { return sellingPrice; }

    public void setSellingPrice(double sellingPrice) {
        if (sellingPrice >= 0) {
            this.sellingPrice = sellingPrice;
        } else {
             System.err.println("Warning: Attempted to set negative selling price.");
        }
    }

    public boolean decrementAvailableUnits() {
        if (this.availableUnits > 0) {
            this.availableUnits--;
            return true;
        } else {
             System.err.println("Warning: Attempted to decrement zero available units.");
             return false;
        }
    }

    public boolean incrementAvailableUnits() {
        if (this.availableUnits < this.totalUnits) {
            this.availableUnits++;
            return true;
        } else {
             System.err.println("Warning: Attempted to increment available units beyond total units.");
             return false;
        }
    }

    public void setAvailableUnits(int availableUnits) {
        if (availableUnits >= 0 && availableUnits <= this.totalUnits) {
            this.availableUnits = availableUnits;
        } else {
            System.err.println("Error: Invalid available units (" + availableUnits + ") set for flat type with total " + this.totalUnits + ". Clamping to valid range [0, " + this.totalUnits + "].");
            this.availableUnits = Math.max(0, Math.min(availableUnits, this.totalUnits));
        }
    }
}