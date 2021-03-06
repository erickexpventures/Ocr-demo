#!/usr/bin/python3
#coding=utf-8
"""----------------------------------------------------------------------
+----------------------------------------------------------------------+
| @file main.py                                                        |
| @author Lucas Fontes Buzuti                                          |
| @version V0.0.1                                                      |
| @created 05/14/2019                                                  |
| @modified 05/15/2019                                                 |
| @e-mail lucas.buzuti@outlook.com                                     |
+----------------------------------------------------------------------+
          Source file containing the Algorithm and Pre-Processing
----------------------------------------------------------------------"""

import os
import sys
import time

import cv2
import numpy as np
import tensorflow as tf
import pytesseract

sys.path.append(os.getcwd())
from package.nets import model_train as model
from package.utils.rpn_msr.proposal_layer import proposal_layer
from package.utils.text_connector.detectors import TextDetector

tf.app.flags.DEFINE_string('gpu', '0', '')
tf.app.flags.DEFINE_string('checkpoint_path', 'checkpoints_mlt/', '')
FLAGS = tf.app.flags.FLAGS

class Algorithm_OCR():
    """ OCR """
    def __init__(self, image):
        self.image = image

    def resize_image(self, img):
        img_size = img.shape
        im_size_min = np.min(img_size[0:2])
        im_size_max = np.max(img_size[0:2])

        im_scale = float(600) / float(im_size_min)
        if np.round(im_scale * im_size_max) > 1200:
            im_scale = float(1200) / float(im_size_max)
        new_h = int(img_size[0] * im_scale)
        new_w = int(img_size[1] * im_scale)

        new_h = new_h if new_h // 16 == 0 else (new_h // 16 + 1) * 16
        new_w = new_w if new_w // 16 == 0 else (new_w // 16 + 1) * 16

        re_im = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        return re_im, (new_h / img_size[0], new_w / img_size[1])


    def main(self, argv=None):
        os.environ['CUDA_VISIBLE_DEVICES'] = FLAGS.gpu

        with tf.get_default_graph().as_default():
            input_image = tf.placeholder(tf.float32, shape=[None, None, None, 3], name='input_image')
            input_im_info = tf.placeholder(tf.float32, shape=[None, 3], name='input_im_info')

            global_step = tf.get_variable('global_step', [], initializer=tf.constant_initializer(0), trainable=False)

            bbox_pred, cls_pred, cls_prob = model.model(input_image)

            variable_averages = tf.train.ExponentialMovingAverage(0.997, global_step)
            saver = tf.train.Saver(variable_averages.variables_to_restore())

            with tf.Session(config=tf.ConfigProto(allow_soft_placement=True)) as sess:
                ckpt_state = tf.train.get_checkpoint_state(FLAGS.checkpoint_path)
                model_path = os.path.join(FLAGS.checkpoint_path, os.path.basename(ckpt_state.model_checkpoint_path))
                print('Restore from {}'.format(model_path))
                saver.restore(sess, model_path)

                start = time.time()

                hsv = cv2.cvtColor(self.image, cv2.COLOR_RGB2HSV)
                lower_green = np.array([65,60,60]) #65,60,60
                upper_green = np.array([80,255,255]) #80,255,255
                mask = cv2.inRange(hsv, lower_green, upper_green)
                _, thresh_mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY_INV)

                img = cv2.cvtColor(self.image, cv2.COLOR_RGB2GRAY)
                _, thresh_img = cv2.threshold(img, 162, 255, cv2.THRESH_BINARY) #162
                img = thresh_mask - thresh_img
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
                img = cv2.medianBlur(img, 3)
                img = cv2.GaussianBlur(img, (3,3), 0)
                img = cv2.GaussianBlur(img, (3,3), 0)

                img, (rh, rw) = self.resize_image(img)
                h, w, c = img.shape
                im_info = np.array([h, w, c]).reshape([1, 3])
                bbox_pred_val, cls_prob_val = sess.run([bbox_pred, cls_prob],
                                                       feed_dict={input_image: [img],
                                                                  input_im_info: im_info})

                textsegs, _ = proposal_layer(cls_prob_val, bbox_pred_val, im_info)
                scores = textsegs[:, 0]
                textsegs = textsegs[:, 1:5]

                textdetector = TextDetector(DETECT_MODE='H')
                boxes = textdetector.detect(textsegs, scores[:, np.newaxis], img.shape[:2])
                boxes = np.array(boxes, dtype=np.int)

                cost_time = (time.time() - start)
                print("cost time: {:.2f}s".format(cost_time))

                extracted = list()
                texts = list()
                img_copy, _ = self.resize_image(self.image)
                for i, box in enumerate(boxes):
                    pts = box[:8]
                    w = np.abs(pts[0] - pts[2])
                    h = np.abs(pts[1] - pts[-1])
                    x = pts[0]
                    y = pts[1]

                    config = ('-l por --oem 1 --psm 7')
                    text = pytesseract.image_to_string(img_copy[y:y+h+4, x:x+w], config=config)
                    texts.append(text)
                    extracted.append(pts)

                for i, box in enumerate(extracted):
                    cv2.polylines(img_copy, [box[:8].astype(np.int32).reshape((-1, 1, 2))], True, color=(0, 255, 0),
                                  thickness=2)
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    cv2.putText(img_copy, texts[i], (box[0],box[1]-2), font, 0.9, (0,0,0), 2, cv2.LINE_AA)

                img = cv2.resize(img_copy, None, None, fx=1.0 / rh, fy=1.0 / rw, interpolation=cv2.INTER_LINEAR)

        return img, texts
