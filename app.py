from flask import Flask, request, jsonify, render_template
import joblib

app = Flask(__name__)
model = joblib.load('models/model.joblib')

@app.route('/predict', methods=['GET'])
def predict():
    text = request.args.get('text')
    return model.predict([text])[0]

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')