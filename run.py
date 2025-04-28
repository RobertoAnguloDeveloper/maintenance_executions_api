# run.py
# This is the entry point for running the Flask development server.

from app import create_app # Import the application factory function
import os

# Create the application instance using the factory.
# The factory (`create_app` in app/__init__.py) handles configuration loading,
# extension initialization, blueprint registration, logging setup, etc.
app = create_app()

# The __name__ == '__main__' block ensures this code only runs
# when the script is executed directly (e.g., `python run.py`).
if __name__ == '__main__':
    # --- Configuration for Development Server ---
    # It's generally better to configure host, port, and debug mode
    # via environment variables (FLASK_RUN_HOST, FLASK_RUN_PORT, FLASK_DEBUG)
    # or command-line arguments (`flask run --host=0.0.0.0 --port=8000`)
    # rather than hardcoding them here.

    # Get host, port, and debug settings from environment variables with defaults.
    host = os.environ.get('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_RUN_PORT', 5000))
    # FLASK_DEBUG=1 enables debug mode (and the reloader)
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'

    # --- Run the Development Server ---
    # The `app.run()` method starts Flask's built-in development server.
    # WARNING: This server is NOT suitable for production deployments.
    # Use a production-ready WSGI server like Gunicorn or uWSGI instead.
    app.run(
        host=host,
        port=port,
        debug=debug_mode
        # use_reloader=debug_mode # The reloader is automatically enabled when debug=True
                                # Setting this explicitly can sometimes help clarify intent or override default behavior.
    )

# Note: If you were using Flask-Script or Click commands defined within your app
# (like `flask database init`), you typically run them via the `flask` command
# in your terminal (e.g., `flask database init`), not by executing `run.py`.
# The `register_commands` function called within `create_app` makes those
# commands available to the `flask` CLI tool.
