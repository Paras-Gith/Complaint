from complaint_app.application import create_app
from config import Config
from models import db as db

app = create_app()


if __name__ == "__main__":
    app.run(debug=Config.DEBUG)
