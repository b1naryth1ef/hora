from klein import run, route
from util import *

# Register Blueprints
from api import *

__version__ = 0.1

@route('/', methods=['GET', 'HEAD', 'POST'])
def home(request):
    return JsonResponse({
        "version": __version__,
        "status": 0
    })

if __name__ == '__main__':
    run("localhost", 5000)
