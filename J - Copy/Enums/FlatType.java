package Enums;

public enum FlatType {
    TWO_ROOM("2-Room"), THREE_ROOM("3-Room");

    private final String displayName;

    FlatType(String displayName) {
        this.displayName = displayName;
    }

    public String getDisplayName() {
        return displayName;
    }

    public static FlatType fromString(String text) {
        if (text != null) {
            for (FlatType b : FlatType.values()) {
                if (text.trim().equalsIgnoreCase(b.name()) || text.trim().equalsIgnoreCase(b.displayName)) {
                    return b;
                }
            }
            if ("2-Room".equalsIgnoreCase(text.trim())) return TWO_ROOM;
            if ("3-Room".equalsIgnoreCase(text.trim())) return THREE_ROOM;
        }
        return null;
    }
}