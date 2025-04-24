import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from project.core.app import ReactiveApp
except ImportError as e:
    print(f"Error importing ReactiveApp: {e}")
    print(f"Project Root: {project_root}")
    print(f"Sys Path: {sys.path}")
    sys.exit(1)

if __name__ == "__main__":
    print("Starting application from main.py...")
    app = ReactiveApp()
    try:
        app.run()
    except SystemExit:
        print("Application exited.")
    except Exception as e:
        print(f"An error occurred during execution: {e}")
    finally:
        if 'app' in locals() and hasattr(app, 'cleanup'):
             print("Running final cleanup...")
             app.cleanup()
             print("Cleanup finished.")
        print("Application finished.")