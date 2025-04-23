package Models;

import java.util.Objects;

public class FlatTypeDetails {
    private final int totalUnits; // Total units planned for this type
    private int availableUnits; // Units currently available for booking
    private double sellingPrice;

    public FlatTypeDetails(int totalUnits, int availableUnits, double sellingPrice) {
        // Validation during construction
        if (totalUnits < 0) {
            throw new IllegalArgumentException("Total units cannot be negative: " + totalUnits);
        }
        if (availableUnits < 0 || availableUnits > totalUnits) {
            throw new IllegalArgumentException("Invalid available units: " + availableUnits + " (Total: " + totalUnits + ")");
        }
        if (sellingPrice < 0) {
            throw new IllegalArgumentException("Selling price cannot be negative: " + sellingPrice);
        }

        this.totalUnits = totalUnits;
        this.availableUnits = availableUnits;
        this.sellingPrice = sellingPrice;
    }

    // Getters
    public int getTotalUnits() { return totalUnits; }
    public int getAvailableUnits() { return availableUnits; }
    public double getSellingPrice() { return sellingPrice; }

    // Setters with validation

    /**
     * Sets the selling price. Must be non-negative.
     * @param sellingPrice The new selling price.
     */
    public void setSellingPrice(double sellingPrice) {
        if (sellingPrice >= 0) {
            this.sellingPrice = sellingPrice;
        } else {
             System.err.println("Warning: Attempted to set negative selling price (" + sellingPrice + "). Price not changed.");
             // Or throw IllegalArgumentException("Selling price cannot be negative: " + sellingPrice);
        }
    }

    /**
     * Decrements the number of available units by one.
     * Fails if no units are currently available.
     * @return true if a unit was successfully decremented, false otherwise.
     */
    public boolean decrementAvailableUnits() {
        if (this.availableUnits > 0) {
            this.availableUnits--;
            return true;
        } else {
             // Log or handle the case where decrement is attempted on zero units
             System.err.println("Warning: Attempted to decrement available units when already zero.");
             return false;
        }
    }

    /**
     * Increments the number of available units by one (e.g., due to withdrawal).
     * Fails if available units are already equal to total units.
     * @return true if a unit was successfully incremented, false otherwise.
     */
    public boolean incrementAvailableUnits() {
        if (this.availableUnits < this.totalUnits) {
            this.availableUnits++;
            return true;
        } else {
             // Log or handle the case where increment goes beyond total
             System.err.println("Warning: Attempted to increment available units beyond total units (" + this.totalUnits + ").");
             return false;
        }
    }

    /**
     * Directly sets the number of available units. Used during data synchronization.
     * Clamps the value within the valid range [0, totalUnits].
     * @param availableUnits The desired number of available units.
     */
    public void setAvailableUnits(int availableUnits) {
        if (availableUnits >= 0 && availableUnits <= this.totalUnits) {
            this.availableUnits = availableUnits;
        } else {
            // Log the error and clamp the value to the nearest valid boundary
            System.err.println("Error: Invalid available units (" + availableUnits + ") set for flat type with total " + this.totalUnits + ". Clamping to valid range [0, " + this.totalUnits + "].");
            this.availableUnits = Math.max(0, Math.min(availableUnits, this.totalUnits));
        }
    }

    // --- Standard overrides ---
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        FlatTypeDetails that = (FlatTypeDetails) o;
        // Two details are equal if total units, available units, and price are the same
        return totalUnits == that.totalUnits &&
               availableUnits == that.availableUnits &&
               Double.compare(that.sellingPrice, sellingPrice) == 0;
    }

    @Override
    public int hashCode() {
        return Objects.hash(totalUnits, availableUnits, sellingPrice);
    }

    @Override
    public String toString() {
        return "FlatTypeDetails{" +
                "totalUnits=" + totalUnits +
                ", availableUnits=" + availableUnits +
                ", sellingPrice=" + sellingPrice +
                '}';
    }
}
