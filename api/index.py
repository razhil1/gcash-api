import traceback
import sys
from app import create_app

try:
    app = create_app()
except Exception as e:
    # This will print the error directly into your Vercel logs!
    print("❌ ERROR DURING APP CREATION:")
    print(traceback.format_exc())
    # Still define 'app' so Vercel doesn't crash on the initial import
    app = None

if __name__ == '__main__':
    if app:
        app.run()
