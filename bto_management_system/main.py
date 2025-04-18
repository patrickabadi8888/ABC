# Ensure the project root is in the Python path if running from elsewhere
# import sys
# import os
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from controller.application_controller import ApplicationController

if __name__ == "__main__":
    # Create data directory if it doesn't exist
    # This should ideally be handled more robustly (e.g., config)
    import os
    data_dir = "data"
    if not os.path.exists(data_dir):
        try:
            os.makedirs(data_dir)
            print(f"Created data directory: {data_dir}")
        except OSError as e:
            print(f"Error creating data directory {data_dir}: {e}")
            # Decide if this is fatal or not

    # Start the application
    app = ApplicationController()
    app.run()