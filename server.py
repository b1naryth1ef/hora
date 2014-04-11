# from klein import run, route
from flask import Flask
from util import *

# Register Blueprints
from api import *

__version__ = 0.1

app = Flask(__name__)
app.register_blueprint(api, url_prefix="/api")

@app.route('/', methods=['GET', 'HEAD', 'POST'])
def home():
    return JsonResponse({
        "version": __version__,
        "status": 0
    })

if __name__ == '__main__':
    app.run(debug=True)
