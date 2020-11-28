from __future__ import division, print_function
import os
import io
import numpy as np
from pyimagesearch.gradcam import GradCAM
import cv2
import uuid
import base64
import sqlite3
from PIL import Image, ImageFilter
from scipy.ndimage import gaussian_filter, fourier_gaussian
from scipy import misc

# Keras
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image

# Flask utils
from flask import Flask, request, render_template, jsonify
from werkzeug.utils import secure_filename
from gevent.pywsgi import WSGIServer

app = Flask(__name__)


ROOT_PATH = os.path.dirname(__file__)
UPLOADS_PATH = os.path.join(ROOT_PATH, "uploads")
MODEL_DIR = "model2"
TRAINED_MODEL = load_model(MODEL_DIR)
TARGET_SIZE = (240, 320)
NAME_PATTERNS = {
    '0_0_0': 'no corrosion',
    '1_0_0': 'soft corrosion',
    '1_1_0': 'medium corossion',
    '1_1_1': 'hard corossion',
    '2_0_0': 'soft damage'
}


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
    heatmap_legend, heatmap, output = cam.overlay_heatmap(heatmap, original_img, alpha=0.2)

    white_strip = 255 * np.ones((255, 1, 3), np.uint8)
    white_strip = cv2.resize(white_strip, (original_img.shape[1], 20))

    output = np.vstack([heatmap_legend, white_strip, heatmap, output])
    return output


def apply_blur(img_path, val):
    img = Image.open(img_path)
    return gaussian_filter(img, sigma=val)


def apply_fourier(img_path, val):
    img = Image.open(img_path)
    return fourier_gaussian(img, sigma=val)


def apply_sharpen(img_path):
    img = Image.open(img_path)
    return img.filter(ImageFilter.SHARPEN).convert('RGB')


def apply_edges(img_path):
    img = Image.open(img_path)
    return img.filter(ImageFilter.CONTOUR).convert('RGB')


def apply_grayscale(img_path):
    img = Image.open(img_path)
    return img.convert('L')


def apply_transform_to_image(file, transform, transform_args=None):
    _, abs_file_path = save_uploaded_file(file)
    if transform_args:
        transform_output = transform(abs_file_path, transform_args)
    else:
        transform_output = transform(abs_file_path)
    os.remove(abs_file_path)
    return transform_output, os.path.join(UPLOADS_PATH, str(uuid.uuid4()) + ".jpg")


def save_uploaded_file(file):
    # Save the file to ./uploads
    name, ext = secure_filename(file.filename).split(".")
    abs_file_path = os.path.join(UPLOADS_PATH, str(uuid.uuid4()) + "." + ext)
    file.save(abs_file_path)
    return name, abs_file_path


def prepare_base64_message(output_fnm):
    byte_data = io.BytesIO()
    with open(output_fnm, 'rb') as fo:
        byte_data.write(fo.read())
    byte_data.seek(0)

    img_base64 = base64.b64encode(byte_data.read())
    base64_message = img_base64.decode('utf-8')
    return base64_message


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/predict', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        name, abs_file_path = save_uploaded_file(request.files['file'])

        true_class = ""
        for class_pattern in NAME_PATTERNS:
            if name.endswith(class_pattern):
                true_class = NAME_PATTERNS.get(class_pattern)
                break

        # Make prediction
        img = preprocess_img(abs_file_path)
        predictions = model_predict(img)
        print(predictions)
        os.remove(abs_file_path)

        pred_class = predictions.argmax()
        result = "corrosion" if pred_class == 1 else "no corrosion"
        probabilities = " (" + str("%.2f" % predictions[pred_class]) + " vs " + str(
            "%.2f" % predictions[abs(1 - pred_class)]) + ")"
        return jsonify(true_class=true_class, result=result, probabilities=probabilities)
    return None


@app.route('/gradcam', methods=['GET', 'POST'])
def gradcam_info():
    if request.method == 'POST':
        # apply gradcam
        gradcam_output, gradcam_output_path = apply_transform_to_image(request.files['file'], apply_gradcam)
        cv2.imwrite(gradcam_output_path, gradcam_output)
        base64_message = prepare_base64_message(gradcam_output_path)
        os.remove(gradcam_output_path)
        return str(base64_message)
    return None


@app.route('/blur', methods=['GET', 'POST'])
def blur():
    if request.method == 'POST':
        blur_output, blur_output_path = apply_transform_to_image(request.files['file'], apply_blur,
                                                                 int(request.form['val']))
        cv2.imwrite(blur_output_path, blur_output)
        base64_message = prepare_base64_message(blur_output_path)
        os.remove(blur_output_path)
        return str(base64_message)
    return None


@app.route('/fourier', methods=['GET', 'POST'])
def fourier():
    if request.method == 'POST':
        fourier_output, fourier_output_path = apply_transform_to_image(request.files['file'], apply_fourier,
                                                                       int(request.form['val'])/5.)
        cv2.imwrite(fourier_output_path, fourier_output)
        base64_message = prepare_base64_message(fourier_output_path)
        os.remove(fourier_output_path)
        return str(base64_message)
    return None


@app.route('/sharpen', methods=['GET', 'POST'])
def sharpen():
    if request.method == 'POST':
        sharpen_output, sharpen_output_path = apply_transform_to_image(request.files['file'], apply_sharpen)
        sharpen_output.save(sharpen_output_path)
        base64_message = prepare_base64_message(sharpen_output_path)
        os.remove(sharpen_output_path)
        return str(base64_message)
    return None


@app.route('/contour', methods=['GET', 'POST'])
def contour():
    if request.method == 'POST':
        edges_output, edges_output_path = apply_transform_to_image(request.files['file'], apply_edges)
        edges_output.save(edges_output_path)
        base64_message = prepare_base64_message(edges_output_path)
        os.remove(edges_output_path)
        return str(base64_message)
    return None


@app.route('/grayscale', methods=['GET', 'POST'])
def grayscale():
    if request.method == 'POST':
        grayscale_output, grayscale_output_path = apply_transform_to_image(request.files['file'], apply_grayscale)
        grayscale_output.save(grayscale_output_path)
        base64_message = prepare_base64_message(grayscale_output_path)
        os.remove(grayscale_output_path)
        return str(base64_message)
    return None


if __name__ == '__main__':
    app.run(debug=True)
