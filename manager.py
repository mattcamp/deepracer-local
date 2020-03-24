from manager import app

import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

if __name__ == '__main__':
    app.debug = True
    app.run(host = '0.0.0.0',port=5000)