"""AI Model Testing, Evaluation and Investigation Agent — Launcher."""
import os
import sys

# Ensure backend directory is in python path
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"================================================================")
    print(f"  AI Model Testing, Evaluation and Investigation Agent")
    print(f"  Access web application at: http://127.0.0.1:{port}")
    print(f"================================================================")
   app.run(host='0.0.0.0', port=port, debug=False)
