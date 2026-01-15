from waitress import serve
from app import app
import os

if __name__ == "__main__":
    from app import app
    print("----- RUN_PRODUCTION: REGISTERED ROUTES -----")
    print(app.url_map)
    print("---------------------------------------------")
    
    # Kill any existing process on port 5000 (Windows specific helper)
    # Using 'waitress' which is pure python
    
    print("STARTING PRODUCTION SERVER (WAITRESS)")
    print("Serving on http://0.0.0.0:5000")
    print("----------------------------------------------------------------")
    serve(app, host='0.0.0.0', port=5000)
