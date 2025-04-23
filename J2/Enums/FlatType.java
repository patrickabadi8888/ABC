package Enums;

public enum FlatType {
    TWO_ROOM("2-Room"),
    THREE_ROOM("3-Room");

    private final String displayName;

    FlatType(String displayName) {
        this.displayName = displayName;
    }

    public String getDisplayName() {
        return displayName;
    }

    /**
     * Parses a string to find the corresponding FlatType enum constant.
     * Case-insensitive matching against enum name and display name.
     * @param text The string to parse.
     * @return The matching FlatType, or null if no match is found.
     */
    public static FlatType fromString(String text) {
        if (text != null) {
            String trimmedText = text.trim();
            for (FlatType b : FlatType.values()) {
                // Check against enum constant name (e.g., "TWO_ROOM")
                if (trimmedText.equalsIgnoreCase(b.name())) {
                    return b;
                }
                // Check against display name (e.g., "2-Room")
                if (trimmedText.equalsIgnoreCase(b.displayName)) {
                    return b;
                }
            }
            // Add specific common variations if needed, though covered by displayName check now
            // if ("2-Room".equalsIgnoreCase(trimmedText)) return TWO_ROOM;
            // if ("3-Room".equalsIgnoreCase(trimmedText)) return THREE_ROOM;
        }
        // Return null if no match found or input is null
        return null;
    }
}
