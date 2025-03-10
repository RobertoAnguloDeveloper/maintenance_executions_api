# run.py
from app import create_app
#from flask_talisman import Talisman

app = create_app()
#Talisman(app, force_https=True)  # Force HTTPS

if __name__ == '__main__':
    #app.run(debug=True, ssl_context='adhoc')
    app.run(debug=True)