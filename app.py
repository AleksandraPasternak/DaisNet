from __future__ import division, print_function
import os
import numpy as np
from pyimagesearch.gradcam import GradCAM
import cv2

# Keras
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image

# Flask utils
from flask import Flask, redirect, url_for, request, render_template
from werkzeug.utils import secure_filename
from gevent.pywsgi import WSGIServer

app = Flask(__name__)

MODEL_DIR = "model2"
TRAINED_MODEL = load_model(MODEL_DIR)
TARGET_SIZE = (240, 320)
FILE_PATH = None


def preprocess_img(img_path):
    img = image.load_img(img_path, target_size=TARGET_SIZE, color_mode="grayscale")
    # img.show()
    input_arr = image.img_to_array(img)
    input_arr = input_arr / 255.
    input_arr = np.array([input_arr])  # convert single image to a batch.
    return input_arr


def model_predict(img):
    preds = np.squeeze(TRAINED_MODEL.predict(img))
    return preds


def apply_gradcam(img_path):
    original_img = cv2.imread(img_path)
    original_img = cv2.resize(original_img, (320, 240))
    image = preprocess_img(img_path)
    preds = model_predict(image)
    i = np.argmax(preds[0])

    # initialize our gradient class activation map and build the heatmap
    cam = GradCAM(TRAINED_MODEL, i)
    heatmap = cam.compute_heatmap(image)

    # resize the resulting heatmap to the original input image dimensions
    # and then overlay heatmap on top of the image
    heatmap = cv2.resize(heatmap, (original_img.shape[1], original_img.shape[0]))
    (heatmap, output) = cam.overlay_heatmap(heatmap, original_img, alpha=0.5)

    output = np.vstack([original_img, heatmap, output])
    return output


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/predict', methods=['GET', 'POST'])
def upload():
    global FILE_PATH
    if request.method == 'POST':
        # Get the file from post request
        f = request.files['file']

        # Save the file to ./uploads
        base_path = os.path.dirname(__file__)  # path of the current directory under which a .py file is executed
        FILE_PATH = os.path.join('uploads', secure_filename(f.filename))
        abs_file_path = os.path.join(base_path, FILE_PATH)
        f.save(abs_file_path)

        # Make prediction
        img = preprocess_img(FILE_PATH)
        predictions = model_predict(img)
        print(predictions)
        # os.remove(file_path)

        pred_class = predictions.argmax()
        result = "corrosion" if pred_class == 1 else "no corrosion"
        return result
    return None


@app.route('/gradcam', methods=['GET', 'POST'])
def gradcam_info():
    global FILE_PATH
    if request.method == 'POST':
        # apply gradcam
        # TODO: work with paths
        gradcam_output = apply_gradcam(FILE_PATH)
        base_path = os.path.dirname(__file__)  # path of the current directory under which a .py file is executed
        gradcam_output_fnm = os.path.join('static', "default_pictures", "gradcam_output.jpg")
        abs_gradcam_path = os.path.join(base_path, gradcam_output_fnm)
        cv2.imwrite(gradcam_output_fnm, gradcam_output)

        return "/static/default_pictures/gradcam_output.jpg"
    return None


if __name__ == '__main__':
    app.run(debug=True)
