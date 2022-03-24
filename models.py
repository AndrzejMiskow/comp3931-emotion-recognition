import numpy as np
import os
import PIL
import tensorflow as tf

from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras import Model
from tensorflow.keras.layers import Input, Conv2D, MaxPool2D, Flatten, Dense
from tensorflow.keras.optimizers import Adam, RMSprop, SGD, Adamax

from layers import *


def gpu_check():
    print("Num GPUs Available: ", len(tf.config.list_physical_devices('GPU')))


def model_vgg16(img_height=48,
                img_width=48,
                a_hidden='relu',  # Hidden activation
                a_output='softmax',  # Output activation
                grayscale=True,
                num_classes = 7
                ):
    """A group of stacked residual blocks for ResNetV1
       Args:
          img_height: integer,default '48', input image height
          img_width: integer,default '48', input image width
          a_hidden: string,default 'relu', activation function used for hidden layerss
          a_output: string, default 'softmax', output activation function
          grayscale: bool, states when the input tensor is RGB or Grayscale
          num_classes: integer, default 7,states the number of classes
        Returns:
          Output A `keras.Model` instance.
    """
    # Input
    if grayscale:
        input_img = Input(shape=(img_height, img_width, 1), name="img")
    else:
        input_img = Input(shape=(img_height, img_width, 3), name="img")
        # Rescale if the data is RGB
        input_img = layers.experimental.preprocessing.Rescaling(1. / 255)(input_img)

    # 1st Conv Block
    x = Conv2D(filters=64, kernel_size=3, padding='same', activation=a_hidden, name="Conv1.1")(input_img)
    x = Conv2D(filters=64, kernel_size=3, padding='same', activation=a_hidden, name="Conv1.2")(x)
    x = MaxPool2D(pool_size=2, strides=2, padding='same', name="MaxPool2D_1")(x)

    # 2nd Conv Block
    x = Conv2D(filters=128, kernel_size=3, padding='same', activation=a_hidden, name="Conv2.1")(x)
    x = Conv2D(filters=128, kernel_size=3, padding='same', activation=a_hidden, name="Conv2.2")(x)
    x = MaxPool2D(pool_size=2, strides=2, padding='same', name="MaxPool2D_2")(x)

    # 3rd Conv block
    x = Conv2D(filters=256, kernel_size=3, padding='same', activation=a_hidden, name="Conv3.1")(x)
    x = Conv2D(filters=256, kernel_size=3, padding='same', activation=a_hidden, name="Conv3.2")(x)
    x = Conv2D(filters=256, kernel_size=3, padding='same', activation=a_hidden, name="Conv3.3")(x)
    x = MaxPool2D(pool_size=2, strides=2, padding='same', name="MaxPool2D_3")(x)

    # 4th Conv block
    x = Conv2D(filters=512, kernel_size=3, padding='same', activation=a_hidden, name="Conv4.1")(x)
    x = Conv2D(filters=512, kernel_size=3, padding='same', activation=a_hidden, name="Conv4.2")(x)
    x = Conv2D(filters=512, kernel_size=3, padding='same', activation=a_hidden, name="Conv4.3")(x)
    x = MaxPool2D(pool_size=2, strides=2, padding='same', name="MaxPool2D_4")(x)

    # 5th Conv block
    x = Conv2D(filters=512, kernel_size=3, padding='same', activation=a_hidden, name="Conv5.1")(x)
    x = Conv2D(filters=512, kernel_size=3, padding='same', activation=a_hidden, name="Conv5.2")(x)
    x = Conv2D(filters=512, kernel_size=3, padding='same', activation=a_hidden, name="Conv5.3")(x)
    x = MaxPool2D(pool_size=2, strides=2, padding='same', name="MaxPool2D_5")(x)

    # Fully connected layers
    x = Flatten()(x)
    x = Dense(units=4096, activation=a_hidden, name="Dense1")(x)
    x = Dense(units=4096, activation=a_hidden, name="Dense2")(x)

    output = Dense(units=num_classes, activation=a_output, name="DenseFinal")(x)

    model = Model(inputs=input_img, outputs=output, name="VGG16")

    return model


def model_ResNet50_V1(
        img_height=48,
        img_width=48,
        a_output='softmax',
        pooling='avg',
        grayscale=True,
        num_classes=7):
    """A group of stacked residual blocks for ResNetV1
       Args:
          img_height: integer,default '48', input image height
          img_width: integer,default '48', input image width
          a_output: string, default 'softmax', output activation function
          pooling: string,default 'avg', pooling used for the final layer either 'avg' or 'max'
          grayscale: bool, states when the input tensor is RGB or Grayscale
          num_classes: integer, default 7,states the number of classes
        Returns:
          Output A `keras.Model` instance.
    """
    # Input
    if grayscale:
        input_img = Input(shape=(img_height, img_width, 1), name="img")
        batch_axis = 1
    else:
        input_img = Input(shape=(img_height, img_width, 3), name="img")
        input_img = layers.experimental.preprocessing.Rescaling(1. / 255)(input_img)
        batch_axis = 3

    bias = False  # False for resnet V1 True for V2

    # Conv_1
    x = layers.ZeroPadding2D(padding=((3, 3), (3, 3)), name='Conv1_Pad')(input_img)
    x = layers.Conv2D(64, 7, strides=2, use_bias=bias, name='Conv1')(x)
    x = layers.BatchNormalization(axis=batch_axis, epsilon=1.001e-5, name='Conv1_BN')(x)
    x = layers.Activation('relu', name='Conv1_relu')(x)

    x = layers.ZeroPadding2D(padding=((1, 1), (1, 1)), name='MaxPool2D_1_Pad')(x)
    x = layers.MaxPooling2D(3, strides=2, name='MaxPool2D_1')(x)

    # Residual Stacked Blocks
    x = group_residuals_v1(x, [64, 64, 256], 3, stride1=1, name='Conv2', grayscale=grayscale)
    x = group_residuals_v1(x, [128, 128, 512], 4, name='Conv3', grayscale=grayscale)
    x = group_residuals_v1(x, [256, 256, 1024], 6, name='Conv4', grayscale=grayscale)
    x = group_residuals_v1(x, [512, 512, 2048], 3, name='Conv5', grayscale=grayscale)

    # Output
    if pooling == 'avg':
        x = layers.GlobalAveragePooling2D(name='AvgPool2D_Final')(x)
    else:
        x = layers.GlobalMaxPooling2D(name='MaxPool2D_Final')(x)

    output = layers.Dense(num_classes, activation=a_output, name='DenseFinal')(x)

    model = Model(inputs=input_img, outputs=output, name="ResNet50_V1")
    return model