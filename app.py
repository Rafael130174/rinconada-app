from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "¡La Rinconada Oriental está en línea!"

if __name__ == '__main__':
    app.run(debug=True)
