from app import app as application

# Hostinger Passenger loads 'application' from this file
if __name__ == "__main__":
    application.run()
