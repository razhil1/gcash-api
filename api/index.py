from app import create_app

app = create_app()

# For Vercel, the variable must be 'app'
if __name__ == '__main__':
    app.run()
