import re
import os

def apply_fixes_to_java_file(filename="BTOApp_fixed.java"):
    """
    Reads a Java file, applies specific fixes based on error analysis,
    and writes the modified content back to the SAME file (overwrite).
    """
    print(f"Attempting to read input file: {filename}")
    if not os.path.exists(filename):
        print(f"Error: Input file '{filename}' not found.")
        return

    try:
        with open(filename, 'r', encoding='utf-8') as f_in:
            content = f_in.read()
        print("Successfully read input file.")
    except Exception as e:
        print(f"Error reading input file: {e}")
        return

    original_content = content # Keep a copy for comparison if needed
    modified_content = content # Work on a copy

    print("Applying fixes...")

    # --- Fix 1 (Revisited): writeCsv header calls ---
    # Ensure we are adding List.of() only if it's missing.
    # Target the specific pattern: writeCsv(filename, new String[]{...})
    patterns_replacements_fix1 = [
        (r'writeCsv\(filename,\s*new String\[]\{"ApplicationID",\s*"ApplicantNRIC",\s*"ProjectName",\s*"FlatTypeApplied",\s*"Status",\s*"ApplicationDate"\}\)',
         'writeCsv(filename, List.of(new String[]{"ApplicationID", "ApplicantNRIC", "ProjectName", "FlatTypeApplied", "Status", "ApplicationDate"}))'),
        (r'writeCsv\(filename,\s*new String\[]\{"EnquiryID",\s*"ApplicantNRIC",\s*"ProjectName",\s*"EnquiryText",\s*"ReplyText",\s*"RepliedByNRIC",\s*"EnquiryDate",\s*"ReplyDate"\}\)',
         'writeCsv(filename, List.of(new String[]{"EnquiryID", "ApplicantNRIC", "ProjectName", "EnquiryText", "ReplyText", "RepliedByNRIC", "EnquiryDate", "ReplyDate"}))'),
        (r'writeCsv\(filename,\s*new String\[]\{"RegistrationID",\s*"OfficerNRIC",\s*"ProjectName",\s*"Status",\s*"RegistrationDate"\}\)',
         'writeCsv(filename, List.of(new String[]{"RegistrationID", "OfficerNRIC", "ProjectName", "Status", "RegistrationDate"}))')
    ]

    applied_fix1 = False
    for pattern, replacement in patterns_replacements_fix1:
        new_content = re.sub(pattern, replacement, modified_content)
        if new_content != modified_content:
            applied_fix1 = True
            modified_content = new_content
    if applied_fix1:
        print("Applied Fix 1 (writeCsv headers - added List.of)")
    else:
        print("Skipped Fix 1 (patterns not found or already fixed)")


    # --- Fix 4 (Revisited): ManagerController variable name ---
    # Find the method scope first, then replace within that scope.
    method_start_pattern = r"public void viewAndReplyToManagedEnquiries\(\)\s*\{"
    method_end_pattern = r"^\s*\}\s*$" # Matches a closing brace on its own line (adjust if needed)

    method_match = re.search(method_start_pattern, modified_content, re.MULTILINE)
    applied_fix4 = False

    if method_match:
        start_index = method_match.end()
        # Find the end of the method (this is approximate, relies on brace matching)
        brace_level = 1
        end_index = -1
        current_index = start_index
        while current_index < len(modified_content):
            char = modified_content[current_index]
            if char == '{':
                brace_level += 1
            elif char == '}':
                brace_level -= 1
                if brace_level == 0:
                    end_index = current_index
                    break
            current_index += 1

        if end_index != -1:
            method_body = modified_content[start_index:end_index]
            # Perform replacements *only* within the method body
            original_body = method_body
            method_body = method_body.replace('myProjects.isEmpty()', 'myManagedProjectNames.isEmpty()')
            method_body = method_body.replace('myProjects.contains(e.getProjectName())', 'myManagedProjectNames.contains(e.getProjectName())')

            # Replace the original method body with the modified one
            if method_body != original_body:
                 modified_content = modified_content[:start_index] + method_body + modified_content[end_index:]
                 applied_fix4 = True
                 print("Applied Fix 4 (ManagerController variable name within method scope)")
            else:
                 print("Skipped Fix 4 (variable name patterns not found within method or already fixed)")
        else:
            print("Warning: Could not reliably find the end of the 'viewAndReplyToManagedEnquiries' method for Fix 4.")
    else:
        print("Warning: Could not find the start of the 'viewAndReplyToManagedEnquiries' method for Fix 4.")

    # --- Ignore Fix 9 (Public Type Error) ---
    # This is a file naming convention issue, not fixable by content modification.

    # --- Write Output (Overwrite) ---
    if modified_content != original_content:
        print(f"\nWriting modified content back to: {filename}")
        try:
            with open(filename, 'w', encoding='utf-8') as f_out:
                f_out.write(modified_content)
            print("Successfully overwrote file.")
        except Exception as e:
            print(f"Error writing output file: {e}")
    else:
        print("\nNo changes were made to the file content.")

# --- Run the script ---
if __name__ == "__main__":
    # Make sure to run this on BTOApp_fixed.java
    apply_fixes_to_java_file(filename="BTOApp_fixed.java")