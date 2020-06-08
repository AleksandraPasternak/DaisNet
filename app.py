from __future__ import division, print_function
import os
import numpy as np


# Keras
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image

# Flask utils
from flask import Flask, redirect, url_for, request, render_template
from werkzeug.utils import secure_filename
from gevent.pywsgi import WSGIServer

app = Flask(__name__)

trained_model = load_model('model2')


def model_predict(img_path):
    img = image.load_img(img_path, target_size=(240, 320), color_mode="grayscale")
    #img.show()
    input_arr = image.img_to_array(img)
    input_arr = input_arr / 255.
    input_arr = np.array([input_arr])  #convert single image to a batch.

    preds = np.squeeze(trained_model.predict(input_arr))
    return preds


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/predict', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        # Get the file from post request
        f = request.files['file']

        # Save the file to ./uploads
        base_path = os.path.dirname(__file__)  # path of the current directory under which a .py file is executed
        file_path = os.path.join(base_path, 'uploads', secure_filename(f.filename))
        f.save(file_path)

        # Make prediction
        predictions = model_predict(file_path)
        print(predictions)
        #os.remove(file_path)

        pred_class = predictions.argmax()
        result = "corrosion" if pred_class == 1 else "no corrosion"
        return result
    return None


if __name__ == '__main__':
    app.run(debug=True)




