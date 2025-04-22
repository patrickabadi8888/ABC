import os

# Define the desired package structure and the classes in each package
structure = {
    "services": ["DataService"],
    "controllers": ["AuthController", "BaseController", "ApplicantController", "OfficerController", "ManagerController"],
    "views": ["BaseView", "ApplicantView", "OfficerView", "ManagerView"],
}

base_dir = ""

for pkg, classes in structure.items():
    pkg_dir = os.path.join(base_dir, pkg.title())
    os.makedirs(pkg_dir, exist_ok=True)
    for cls in classes:
        file_path = os.path.join(pkg_dir, f"{cls}.java")
        with open(file_path, "w") as f:
            f.write(f"package {pkg.title()};\n")

print("Folders and Java files created successfully.")
