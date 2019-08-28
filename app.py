#!/usr/bin/python3
"""----------------------------------------------------------------------
+----------------------------------------------------------------------+
| @file main.py                                                        |
| @author Lucas Fontes Buzuti                                          |
| @version V0.0.1                                                      |
| @created 05/14/2019                                                  |
| @modified 05/15/2019                                                 |
| @e-mail lucas.buzuti@outlook.com                                     |
+----------------------------------------------------------------------+
               Source file containing the App function
----------------------------------------------------------------------"""


import os
#import shutil
import cv2
from flask import Flask, render_template, request
from package.algorithm.ocr import Algorithm_OCR


UPLOAD_FOLDER = '/static/uploads/'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

app = Flask(__name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home_page():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_page():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            return render_template('upload.html', msg='No file selected')
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            return render_template('upload.html', msg='No file selected')

        if file and allowed_file(file.filename):
            if not os.path.isdir(os.getcwd()+UPLOAD_FOLDER):
                os.makedirs(os.getcwd()+UPLOAD_FOLDER)

            file.save(os.path.join(os.getcwd()+UPLOAD_FOLDER, file.filename))
            img = cv2.imread(os.path.join(os.getcwd()+UPLOAD_FOLDER, file.filename))
            # Algorithm
            img, texts = Algorithm_OCR(img).main()

            cv2.imwrite(os.path.join(os.getcwd()+UPLOAD_FOLDER, file.filename+'_results.png'), img)

            # extract the text and display it
            return render_template('upload.html',
                                   msg='Successfully processed',
                                   extracted_text=texts,
                                   Name=texts[0],
                                   ID_1=texts[7],
                                   ID_2=texts[6],
                                   Parents=texts[5],
                                   img_upload=UPLOAD_FOLDER+file.filename,
                                   img_src=UPLOAD_FOLDER+file.filename+'_results.png')

    elif request.method == 'GET':
        return render_template('upload.html')


if __name__ == '__main__':
	app.run()
    #if os.path.isdir(os.getcwd()+UPLOAD_FOLDER):
        #shutil.rmtree(os.getcwd()+UPLOAD_FOLDER)
