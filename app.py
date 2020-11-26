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
from flask import Flask, request, render_template
from werkzeug.utils import secure_filename
from gevent.pywsgi import WSGIServer

app = Flask(__name__)

MODEL_DIR = "model2"
TRAINED_MODEL = load_model(MODEL_DIR)
TARGET_SIZE = (240, 320)


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
        _, ext = secure_filename(f.filename).split(".")
        file_path = os.path.join('uploads', str(uuid.uuid4()) + "." + ext)
        abs_file_path = os.path.join(base_path, file_path)
        f.save(abs_file_path)

        # Make prediction
        img = preprocess_img(file_path)
        predictions = model_predict(img)
        print(predictions)
        os.remove(file_path)

        pred_class = predictions.argmax()
        result = "corrosion" if pred_class == 1 else "no corrosion"
        return result
    return None


@app.route('/gradcam', methods=['GET', 'POST'])
def gradcam_info():
    if request.method == 'POST':
        # apply gradcam
        # TODO: work with paths
        f = request.files['file']

        # Save the file to ./uploads
        base_path = os.path.dirname(__file__)  # path of the current directory under which a .py file is executed
        _, ext = secure_filename(f.filename).split(".")
        file_path = os.path.join('uploads', str(uuid.uuid4()) + "." + ext)
        abs_file_path = os.path.join(base_path, file_path)
        f.save(abs_file_path)

        gradcam_output = apply_gradcam(file_path)

        os.remove(file_path)

        gradcam_output_fnm = os.path.join('uploads', str(uuid.uuid4()) + ".jpg")
        abs_gradcam_path = os.path.join(base_path, gradcam_output_fnm)
        cv2.imwrite(gradcam_output_fnm, gradcam_output)

        byte_data = io.BytesIO()
        with open(gradcam_output_fnm, 'rb') as fo:
            byte_data.write(fo.read())
        byte_data.seek(0)

        img_base64 = base64.b64encode(byte_data.read())
        base64_message = img_base64.decode('utf-8')

        os.remove(gradcam_output_fnm)

        return str(base64_message)
    return None

@app.route('/blur', methods=['GET', 'POST'])
def blur():
    if request.method == 'POST':
        f = request.files['file']
        sigma = int(request.form['val'])

        # Save the file to ./uploads
        base_path = os.path.dirname(__file__)  # path of the current directory under which a .py file is executed
        _, ext = secure_filename(f.filename).split(".")
        file_path = os.path.join('uploads', str(uuid.uuid4()) + "." + ext)
        abs_file_path = os.path.join(base_path, file_path)
        f.save(abs_file_path)

        blur_output = apply_blur(file_path, sigma)

        os.remove(file_path)

        blur_output_fnm = os.path.join('uploads', str(uuid.uuid4()) + ".jpg")
        cv2.imwrite(blur_output_fnm, blur_output)

        byte_data = io.BytesIO()
        with open(blur_output_fnm, 'rb') as fo:
            byte_data.write(fo.read())
        byte_data.seek(0)

        img_base64 = base64.b64encode(byte_data.read())
        base64_message = img_base64.decode('utf-8')

        os.remove(blur_output_fnm)

        return str(base64_message)
    return None

@app.route('/fourier', methods=['GET', 'POST'])
def fourier():
    if request.method == 'POST':
        f = request.files['file']
        sigma = int(request.form['val'])
        
        # Save the file to ./uploads
        base_path = os.path.dirname(__file__)  # path of the current directory under which a .py file is executed
        _, ext = secure_filename(f.filename).split(".")
        file_path = os.path.join('uploads', str(uuid.uuid4()) + "." + ext)
        abs_file_path = os.path.join(base_path, file_path)
        f.save(abs_file_path)

        fourier_output = apply_fourier(file_path, sigma)

        os.remove(file_path)

        fourier_output_fnm = os.path.join('uploads', str(uuid.uuid4()) + ".jpg")
        cv2.imwrite(fourier_output_fnm, fourier_output)

        byte_data = io.BytesIO()
        with open(fourier_output_fnm, 'rb') as fo:
            byte_data.write(fo.read())
        byte_data.seek(0)

        img_base64 = base64.b64encode(byte_data.read())
        base64_message = img_base64.decode('utf-8')

        os.remove(fourier_output_fnm)

        return str(base64_message)
    return None

@app.route('/sharpen', methods=['GET', 'POST'])
def sharpen():
    if request.method == 'POST':
        f = request.files['file']
        
        # Save the file to ./uploads
        base_path = os.path.dirname(__file__)  # path of the current directory under which a .py file is executed
        _, ext = secure_filename(f.filename).split(".")
        file_path = os.path.join('uploads', str(uuid.uuid4()) + "." + ext)
        abs_file_path = os.path.join(base_path, file_path)
        f.save(abs_file_path)

        sharpen_output = apply_sharpen(file_path)

        os.remove(file_path)

        sharpen_output_fnm = os.path.join('uploads', str(uuid.uuid4()) + ".jpg")
        sharpen_output.save(sharpen_output_fnm)

        byte_data = io.BytesIO()
        with open(sharpen_output_fnm, 'rb') as fo:
            byte_data.write(fo.read())
        byte_data.seek(0)

        img_base64 = base64.b64encode(byte_data.read())
        base64_message = img_base64.decode('utf-8')

        os.remove(sharpen_output_fnm)

        return str(base64_message)
    return None

@app.route('/contour', methods=['GET', 'POST'])
def contour():
    if request.method == 'POST':
        f = request.files['file']
        
        # Save the file to ./uploads
        base_path = os.path.dirname(__file__)  # path of the current directory under which a .py file is executed
        _, ext = secure_filename(f.filename).split(".")
        file_path = os.path.join('uploads', str(uuid.uuid4()) + "." + ext)
        abs_file_path = os.path.join(base_path, file_path)
        f.save(abs_file_path)

        edges_output = apply_edges(file_path)

        os.remove(file_path)

        edges_output_fnm = os.path.join('uploads', str(uuid.uuid4()) + ".jpg")
        edges_output.save(edges_output_fnm)

        byte_data = io.BytesIO()
        with open(edges_output_fnm, 'rb') as fo:
            byte_data.write(fo.read())
        byte_data.seek(0)

        img_base64 = base64.b64encode(byte_data.read())
        base64_message = img_base64.decode('utf-8')

        os.remove(edges_output_fnm)

        return str(base64_message)
    return None


if __name__ == '__main__':
    app.run(debug=True)
