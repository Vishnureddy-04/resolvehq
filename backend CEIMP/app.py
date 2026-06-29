from flask import Flask

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return {'message': 'ResolveHQ API is live!', 'status': 'success'}, 200

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)