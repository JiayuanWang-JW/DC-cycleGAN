#!/usr/bin/env python
# coding: utf-8

# # Code example: CycleGAN 
# 
# This code example provides a full implementation of CycleGAN in Keras. It is is based on [this implementation](https://github.com/simontomaskarlsson/CycleGAN-Keras) by Simon Karlsson. Although it is possible to run this code on a CPU, a computer with a **GPU is strongly recommended**. The code is provided ready to run, but also includes multiple adjustable settings.

from keras.layers import Layer, Input, Dropout, Conv2D, Activation, add, UpSampling2D,     Conv2DTranspose, Flatten,Reshape
from keras_contrib.layers.normalization.instancenormalization import InstanceNormalization, InputSpec
from keras.layers.advanced_activations import LeakyReLU
from keras.layers.core import Dense
from keras.optimizers import Adam
from keras.models import Model
from keras.engine.topology import Network
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from progress.bar import Bar
import datetime
import time
import json
import csv
import sys
import os
from skimage.transform import resize
import keras.backend as K
import tensorflow as tf
from helper_funcs import *

# If you have multiple GPUs you can select a single one of them by setting the visible CUDA device to 0, 1, ...

# os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"
# os.environ["CUDA_VISIBLE_DEVICES"]="0"

# #### Load data

def main():
    opt = {}
    opt['dataset_path'] = FLAGS.dataset_path
    image_folder = FLAGS.dataset
    data = load_data(image_folder,opt)

    # ### Model parameters

    # Data
    opt['channels'] = data["nr_of_channels"]
    opt['img_shape'] = data["image_size"] + (opt['channels'],)
    opt['A_train'] = data["trainA_images"]
    opt['B_train'] = data["trainB_images"]
    opt['A_test'] = data["testA_images"]
    opt['B_test'] = data["testB_images"]
    opt['testA_image_names'] = data["testA_image_names"]
    opt['testB_image_names'] = data["testB_image_names"]
    
    # CylceGAN can be used both on paired and unpaired data. The `paired_data` setting affects the presentation of output images as explained above.

    opt['paired_data'] = FLAGS.paired

    # #### Training parameters
    # - `lambda_ABA` and `lambda_BAB` set the importance of the cycle consistency losses in relation to the adversarial loss `lambda_adversarial`
    # - `learning_rate_D` and `learning_rate_G` are the learning rates for the discriminators and generators respectively.
    # - `generator_iterations` and `discriminator_iterations` represent how many times the generators or discriminators will be trained on every batch of images. This is very useful to keep the training of both systems balanced. In this case the discriminators become successful faster than the generators, so we account for this by training the generators 3 times on every batch of images.
    # - `synthetic_pool_size` sets the size of the image pool used for training the discriminators. The image pool has a certain probability of returning a synthetic image from previous iterations, thus forcing the discriminator to have a certain "memory". More information on this method can be found in [this paper](https://arxiv.org/abs/1612.07828).
    # - `beta_1` and `beta_2` are paremeters of the [Adam](https://arxiv.org/abs/1412.6980) optimizers used on the generators and discriminators.
    # - `batch_size` determines the number of images used for each update of the network weights. Due to the significant memory requirements of CycleGAN it is difficult to use a large batch size. For the small example dataset values between 1-30 may be possible.
    # - `epochs` sets the number of training epochs. Each epoch goes through all the training images once. The number of epochs necessary to train a model is therefore dependent on both the number of training images available and the batch size.

    # Training parameters
    opt['lambda_ABA'] = FLAGS.lambdaG  # Cyclic loss weight A_2_B
    opt['lambda_BAB'] = FLAGS.lambdaG  # Cyclic loss weight B_2_A
    opt['lambda_adversarial'] = 1.0  # Weight for loss from discriminator guess on synthetic images
    opt['learning_rate_D'] = FLAGS.lrD  #learning_rate always set 0.0002
    opt['learning_rate_G'] = FLAGS.lrG  #learning_rate always set 0.0002
    opt['generator_iterations'] = FLAGS.G_rate  # Number of generator training iterations in each training loop
    opt['discriminator_iterations'] = FLAGS.D_rate  # Number of discriminator training iterations in each training loop
    opt['synthetic_pool_size'] = 50  # Size of image pools used for training the discriminators
    opt['beta_1'] = 0.5  # Adam parameter
    opt['beta_2'] = 0.999  # Adam parameter
    opt['batch_size'] = 1  # Number of images per batch
    opt['epochs'] = FLAGS.epoch  # Choose multiples of 20 since the models are saved each 20th epoch

    # Output parameters
    opt['save_models'] = True  # Save or not the generator and discriminator models
    opt['save_training_img'] = True  # Save or not example training results or only tmp.png
    opt['save_training_img_interval'] = 20  # Number of epoch between saves of intermediate training results
    opt['self.tmp_img_update_frequency'] = 20  # Number of batches between updates of tmp.png

    # #### Architecture parameters
    # - `use_instance_normalization` is supposed to allow the selection of instance normalization or batch normalization layes. At the moment only instance normalization is implemented, so this option does not do anything.
    # - `use_dropout` and `use_bias` allows setting droupout layers in the generators and whether to use a bias term in the various convolutional layer in the genrators and discriminators.
    # - `use_linear_decay` applies linear decay on the learning rates of the generators and discriminators,   `decay_epoch`
    # - `use_patchgan` determines whether the discriminator evaluates the "realness" of images on a patch basis or on the whole. More information on PatchGAN can be found in [this paper](https://arxiv.org/abs/1611.07004).
    # - `use_resize_convolution` provides two ways to perfrom the upsampling in the generator, with significant differences in the results. More information can be found in [this article](https://distill.pub/2016/deconv-checkerboard/). Each has its advantages, and we have managed to get successful result with both methods
    # - `use_discriminator sigmoid` adds a sigmoid activation at the end of the discrimintator, forcing its output to the (0-1) range.

    # Architecture parameters
    opt['use_instance_normalization'] = True  # Use instance normalization or batch normalization
    opt['use_dropout'] = FLAGS.dropout  # Dropout in residual blocks
    opt['use_bias'] = True  # Use bias
#     opt['use_linear_decay'] = True  # Linear decay of learning rate, for both discriminators and generators
    if FLAGS.decay>=FLAGS.epoch:
        opt['use_linear_decay'] = False  # Linear decay of learning rate, for both discriminators and generators
    else:
        opt['use_linear_decay'] = True
    opt['decay_epoch'] = FLAGS.decay  # The epoch where the linear decay of the learning rates start
    opt['use_patchgan'] = True  # PatchGAN - if false the discriminator learning rate should be decreased
    opt['use_resize_convolution'] = False  # Resize convolution - instead of transpose convolution in deconvolution layers (uk) - can reduce checkerboard artifacts but the blurring might affect the cycle-consistency
    opt['discriminator_sigmoid'] = False  # Add a final sigmoid activation to the discriminator

    # Tweaks
    opt['REAL_LABEL'] = 1.0  # Use e.g. 0.9 to avoid training the discriminators to zero loss

    # Read the triplet negative data.
    
    image_array_ct,image_array_mri = load_negative_data(image_folder,opt)
    
    # ### Model architecture
    # #### Layer blocks
    # These are the individual layer blocks that are used to build the generators and discriminator. More information can be found in the appendix of the [CycleGAN paper](https://arxiv.org/abs/1703.10593).

    # Discriminator layers
    def ck(model, opt, x, k, use_normalization, use_bias):
        x = Conv2D(filters=k, kernel_size=4, strides=2, padding='same', use_bias=use_bias)(x)
        if use_normalization:
            x = model['normalization'](axis=3, center=True, epsilon=1e-5)(x, training=True)
        x = LeakyReLU(alpha=0.2)(x)
        return x

    # First generator layer
    def c7Ak(model, opt, x, k):
        x = Conv2D(filters=k, kernel_size=7, strides=1, padding='valid', use_bias=opt['use_bias'])(x)
        x = model['normalization'](axis=3, center=True, epsilon=1e-5)(x, training=True)
        x = Activation('relu')(x)
        return x

    # Downsampling
    def dk(model, opt, x, k):  # Should have reflection padding
        x = Conv2D(filters=k, kernel_size=3, strides=2, padding='same', use_bias=opt['use_bias'])(x)
        x = model['normalization'](axis=3, center=True, epsilon=1e-5)(x, training=True)
        x = Activation('relu')(x)
        return x

    # Residual block
    def Rk(model, opt, x0):
        k = int(x0.shape[-1])

        # First layer
        x = ReflectionPadding2D((1,1))(x0)
        x = Conv2D(filters=k, kernel_size=3, strides=1, padding='valid', use_bias=opt['use_bias'])(x)
        x = model['normalization'](axis=3, center=True, epsilon=1e-5)(x, training=True)
        x = Activation('relu')(x)

        if opt['use_dropout']:
            x = Dropout(0.5)(x)

        # Second layer
        x = ReflectionPadding2D((1, 1))(x)
        x = Conv2D(filters=k, kernel_size=3, strides=1, padding='valid', use_bias=opt['use_bias'])(x)
        x = model['normalization'](axis=3, center=True, epsilon=1e-5)(x, training=True)
        # Merge
        x = add([x, x0])

        return x

    # Upsampling
    def uk(model, opt, x, k):
        # (up sampling followed by 1x1 convolution <=> fractional-strided 1/2)
        if opt['use_resize_convolution']:
            x = UpSampling2D(size=(2, 2))(x)  # Nearest neighbor upsampling
            x = ReflectionPadding2D((1, 1))(x)
            x = Conv2D(filters=k, kernel_size=3, strides=1, padding='valid', use_bias=opt['use_bias'])(x)
        else:
            x = Conv2DTranspose(filters=k, kernel_size=3, strides=2, padding='same', use_bias=opt['use_bias'])(x)  # this matches fractionally stided with stride 1/2
        x = model['normalization'](axis=3, center=True, epsilon=1e-5)(x, training=True)
        x = Activation('relu')(x)
        return x

    # #### Architecture functions

    def build_discriminator(model, opt, name=None):
        # Input
        input_img = Input(shape=opt['img_shape'])

        # Layers 1-4
        x = ck(model, opt, input_img, 64, False, True) #  Instance normalization is not used for this layer)
        x = ck(model, opt, x, 128, True, opt['use_bias'])
        x = ck(model, opt, x, 256, True, opt['use_bias'])
        x = ck(model, opt, x, 512, True, opt['use_bias'])

        # Layer 5: Output
        if opt['use_patchgan']:
            x = Conv2D(filters=1, kernel_size=4, strides=1, padding='same', use_bias=True)(x)
        else:
            x = Flatten()(x)
            x = Dense(1)(x)

        if opt['discriminator_sigmoid']:
            x = Activation('sigmoid')(x)

        return Model(inputs=input_img, outputs=x, name=name)

    def build_generator(model, opt, name=None):
        # Layer 1: Input
        input_img = Input(shape=opt['img_shape'])
        x = ReflectionPadding2D((3, 3))(input_img)
        x = c7Ak(model, opt, x, 32)

        # Layer 2-3: Downsampling
        x = dk(model, opt, x, 64)
        x = dk(model, opt, x, 128)

        # Layers 4-12: Residual blocks
        for _ in range(4, 13):
            x = Rk(model, opt, x)

        # Layer 13:14: Upsampling
        x = uk(model, opt, x, 64)
        x = uk(model, opt, x, 32)

        # Layer 15: Output
        x = ReflectionPadding2D((3, 3))(x)
        x = Conv2D(opt['channels'], kernel_size=7, strides=1, padding='valid', use_bias=True)(x)
        x = Activation('tanh')(x)
    #     x = Reshape((217,181,1))(x)

        return Model(inputs=input_img, outputs=x, name=name)

    # #### Loss functions
    # The discriminators use MSE loss. The generators use MSE for the adversarial losses and MAE for the cycle consistency losses. We use ssim and CE loss instead of MAE and MSE, respectively.

    # Mean squared error
    def mse(y_true, y_pred):
        loss = tf.reduce_mean(tf.squared_difference(y_pred, y_true))
        return losss

    # Mean absolute error
    def mae(y_true, y_pred):
        loss = tf.reduce_mean(tf.abs(y_pred - y_true))
        return loss

    # Structural similarity index measure loss
    def ssim(y_true, y_pred):
        loss = 1 - tf.reduce_mean(tf.image.ssim(y_true, y_pred, max_val=1.0))
        return loss
    
    # cross-entropy loss. celoss will implement sigmoid. So the discriminator need not implement sigmoid activation.
    def celoss(y_true, y_pred):
        loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(labels=y_true, logits=y_pred))
        return loss

    # #### Build CycleGAN model

    model = {}

    # Normalization
    model['normalization'] = InstanceNormalization

    # Optimizers
    model['opt_D'] = Adam(opt['learning_rate_D'], opt['beta_1'], opt['beta_2'])
    model['opt_G'] = Adam(opt['learning_rate_G'], opt['beta_1'], opt['beta_2'])

    # Build discriminators
    D_A = build_discriminator(model, opt, name='D_A')
    D_B = build_discriminator(model, opt, name='D_B')

    # Define discriminator models
    image_A = Input(shape=opt['img_shape'])
    image_B = Input(shape=opt['img_shape'])
    guess_A = D_A(image_A)
    guess_B = D_B(image_B)
    model['D_A'] = Model(inputs=image_A, outputs=guess_A, name='D_A_model')
    model['D_B'] = Model(inputs=image_B, outputs=guess_B, name='D_B_model')

    # Compile discriminator models
    loss_weights_D = [1/3]  # 0.5 since we train on real and synthetic images
    model['D_A'].compile(optimizer=model['opt_D'],
                     loss=celoss,
                     loss_weights=loss_weights_D)
    model['D_B'].compile(optimizer=model['opt_D'],
                     loss=celoss,
                     loss_weights=loss_weights_D)

    # Use containers to make a static copy of discriminators, used when training the generators
    model['D_A_static'] = Network(inputs=image_A, outputs=guess_A, name='D_A_static_model')
    model['D_B_static'] = Network(inputs=image_B, outputs=guess_B, name='D_B_static_model')

    # Do not update discriminator weights during generator training
    model['D_A_static'].trainable = False
    model['D_B_static'].trainable = False

    # Build generators
    model['G_A2B'] = build_generator(model, opt, name='G_A2B_model')
    model['G_B2A'] = build_generator(model, opt, name='G_B2A_model')

    # Define full CycleGAN model, used for training the generators
    real_A = Input(shape=opt['img_shape'], name='real_A')
    real_B = Input(shape=opt['img_shape'], name='real_B')
    synthetic_B = model['G_A2B'](real_A)
    synthetic_A = model['G_B2A'](real_B)
    dB_guess_synthetic = model['D_B_static'](synthetic_B)
    dA_guess_synthetic = model['D_A_static'](synthetic_A)
    reconstructed_A = model['G_B2A'](synthetic_B)
    reconstructed_B = model['G_A2B'](synthetic_A)

    # Compile full CycleGAN model
    model_outputs = [reconstructed_A, reconstructed_B,
                     dB_guess_synthetic, dA_guess_synthetic]
    compile_losses = [ssim, ssim,
                      celoss, celoss]
    compile_weights = [opt['lambda_ABA'], opt['lambda_BAB'],
                       opt['lambda_adversarial'], opt['lambda_adversarial']]

    model['G_model'] = Model(inputs=[real_A, real_B],
                         outputs=model_outputs,
                         name='G_model')

    model['G_model'].compile(optimizer=model['opt_G'],
                         loss=compile_losses,
                         loss_weights=compile_weights)

    # #### Folders and configuration

    opt['date_time'] = 'trip-ce-ssim'+'G_rate'+str(opt['generator_iterations']) + str(opt['paired_data']) + str(opt['lambda_ABA'])+str(FLAGS.dataset) + str(FLAGS.date)

    # Output folder for run data and images
    opt['out_dir'] = os.path.join(FLAGS.save_image_path, opt['date_time'])
    if not os.path.exists(opt['out_dir']):
        os.makedirs(opt['out_dir'])

    # Output folder for saved models
    if opt['save_models']:
        opt['model_out_dir'] = os.path.join(FLAGS.save_model, 'saved_models', opt['date_time'])
        if not os.path.exists(opt['model_out_dir']):
            os.makedirs(opt['model_out_dir'])

    write_metadata_to_JSON(model, opt)

    # Don't pre-allocate GPU memory; allocate as-needed
    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True
    K.tensorflow_backend.set_session(tf.Session(config=config))

    # ### Training function

    def train(model, opt):

        def run_training_batch():

            # ======= Discriminator training ======
            # Generate batch of synthetic images
            synthetic_images_B = model['G_A2B'].predict(real_images_A)
            synthetic_images_A = model['G_B2A'].predict(real_images_B)
            synthetic_images_B = synthetic_pool_B.query(synthetic_images_B)
            synthetic_images_A = synthetic_pool_A.query(synthetic_images_A)

            # Train discriminators on batch
            D_loss = []
            for _ in range(opt['discriminator_iterations']):
                D_A_loss_real = model['D_A'].train_on_batch(x=real_images_A, y=ones)
                D_A_loss_trip = model['D_A'].train_on_batch(x=image_array_mri, y=zeros)
                D_B_loss_real = model['D_B'].train_on_batch(x=real_images_B, y=ones)
                D_B_loss_trip = model['D_B'].train_on_batch(x=image_array_ct, y=zeros)
                D_A_loss_synthetic = model['D_A'].train_on_batch(x=synthetic_images_A, y=zeros)
                D_B_loss_synthetic = model['D_B'].train_on_batch(x=synthetic_images_B, y=zeros)
                D_A_loss = D_A_loss_real + D_A_loss_synthetic + 0.5*D_A_loss_trip
                D_B_loss = D_B_loss_real + D_B_loss_synthetic + 0.5*D_B_loss_trip
                D_loss.append(D_A_loss + D_B_loss)

            # ======= Generator training ==========
            target_data = [real_images_A, real_images_B, ones, ones]  # Reconstructed images need to match originals, discriminators need to predict ones

            # Train generators on batch
            G_loss = []
            for _ in range(opt['generator_iterations']):
                G_loss.append(model['G_model'].train_on_batch(
                    x=[real_images_A, real_images_B], y=target_data))

            # Update learning rates
            if opt['use_linear_decay'] and epoch >= opt['decay_epoch']:
                update_lr(model['D_A'], decay_D)
                update_lr(model['D_B'], decay_D)
                update_lr(model['G_model'], decay_G)

            # Store training losses
            D_A_losses.append(D_A_loss)
            D_B_losses.append(D_B_loss)
            D_losses.append(D_loss[-1])

            ABA_reconstruction_loss = G_loss[-1][1]
            BAB_reconstruction_loss = G_loss[-1][2]
            reconstruction_loss = ABA_reconstruction_loss + BAB_reconstruction_loss
            G_AB_adversarial_loss = G_loss[-1][3]
            G_BA_adversarial_loss = G_loss[-1][4]

            ABA_reconstruction_losses.append(ABA_reconstruction_loss)
            BAB_reconstruction_losses.append(BAB_reconstruction_loss)
            reconstruction_losses.append(reconstruction_loss)
            G_AB_adversarial_losses.append(G_AB_adversarial_loss)
            G_BA_adversarial_losses.append(G_BA_adversarial_loss)
            G_losses.append(G_loss[-1][0])

            # Print training status
            print('\n')
            print('Epoch ---------------------', epoch, '/', opt['epochs'])
            print('Loop index ----------------', loop_index + 1, '/', nr_im_per_epoch)
            if opt['discriminator_iterations'] > 1:
                print('  Discriminator losses:')
                for i in range(opt['discriminator_iterations']):
                    print('D_loss', D_loss[i])
            if opt['generator_iterations'] > 1:
                print('  Generator losses:')
                for i in range(opt['generator_iterations']):
                    print('G_loss', G_loss[i])
            print('  Summary:')
            print('D_lr:', K.get_value(model['D_A'].optimizer.lr))
            print('G_lr', K.get_value(model['G_model'].optimizer.lr))
            print('D_loss: ', D_loss[-1])
            print('G_loss: ', G_loss[-1][0])
            print('reconstruction_loss: ', reconstruction_loss)
            print_ETA(opt, start_time, epoch, nr_im_per_epoch, loop_index)
            sys.stdout.flush()

            if loop_index % 3*opt['batch_size'] == 0:
                # Save temporary images continously
                save_tmp_images(model, opt, real_images_A[0], real_images_B[0],
                                     synthetic_images_A[0], synthetic_images_B[0])

        # ======================================================================
        # Begin training
        # ======================================================================
        if opt['save_training_img'] and not os.path.exists(os.path.join(opt['out_dir'], 'train_A')):
            os.makedirs(os.path.join(opt['out_dir'], 'train_A'))
            os.makedirs(os.path.join(opt['out_dir'], 'train_B'))
            os.makedirs(os.path.join(opt['out_dir'], 'test_A'))
            os.makedirs(os.path.join(opt['out_dir'], 'test_B'))

        D_A_losses = []
        D_B_losses = []
        D_losses = []

        ABA_reconstruction_losses = []
        BAB_reconstruction_losses = []
        reconstruction_losses = []
        G_AB_adversarial_losses = []
        G_BA_adversarial_losses = []
        G_losses = []

        # Image pools used to update the discriminators
        synthetic_pool_A = ImagePool(opt['synthetic_pool_size'])
        synthetic_pool_B = ImagePool(opt['synthetic_pool_size'])

        # Labels used for discriminator training
        label_shape = (opt['batch_size'],) + model['D_A'].output_shape[1:]
        ones = np.ones(shape=label_shape) * opt['REAL_LABEL']
        zeros = ones * 0

        # Linear learning rate decay
        if opt['use_linear_decay']:
            decay_D, decay_G = get_lr_linear_decay_rate(opt)

        nr_train_im_A = opt['A_train'].shape[0]
        nr_train_im_B = opt['B_train'].shape[0]
        nr_im_per_epoch = int(np.ceil(np.max((nr_train_im_A, nr_train_im_B)) / opt['batch_size']) * opt['batch_size'])

        # Start stopwatch for ETAs
        start_time = time.time()
        timer_started = False

        for epoch in range(1, opt['epochs'] + 1):
            
            random_order_A = np.concatenate((np.random.permutation(nr_train_im_A),
                                             np.random.randint(nr_train_im_A, size=nr_im_per_epoch - nr_train_im_A)))
            random_order_B = np.concatenate((np.random.permutation(nr_train_im_B),
                                             np.random.randint(nr_train_im_B, size=nr_im_per_epoch - nr_train_im_B)))

            # Train on image batch
            for loop_index in range(0, nr_im_per_epoch, opt['batch_size']):
                indices_A = random_order_A[loop_index:loop_index + opt['batch_size']]
                indices_B = random_order_B[loop_index:loop_index + opt['batch_size']]

                real_images_A = opt['A_train'][indices_A]
                real_images_B = opt['B_train'][indices_B]

                # Train on image batch
                run_training_batch()

                # Start timer after first (slow) iteration has finished
                if not timer_started:
                    start_time = time.time()
                    timer_started = True

            # Save training images
            if opt['save_training_img'] and epoch % opt['save_training_img_interval'] == 0:
                print('\n', '\n', '-------------------------Saving images for epoch', epoch, '-------------------------', '\n', '\n')
                save_epoch_images(model, opt, epoch)

            # Save model
            if opt['save_models'] and epoch % opt['epochs'] == 0:
                save_model(opt, model['D_A'], epoch)
                save_model(opt, model['D_B'], epoch)
                save_model(opt, model['G_A2B'], epoch)
                save_model(opt, model['G_B2A'], epoch)

            # Save training history
            training_history = {
                'DA_losses': D_A_losses,
                'DB_losses': D_B_losses,
                'G_AB_adversarial_losses': G_AB_adversarial_losses,
                'G_BA_adversarial_losses': G_BA_adversarial_losses,
                'ABA_reconstruction_losses': ABA_reconstruction_losses,
                'BAB_reconstruction_losses': BAB_reconstruction_losses,
                'reconstruction_losses': reconstruction_losses,
                'D_losses': D_losses,
                'G_losses': G_losses}

    # ### Train CycleGAN

    train(model, opt)

import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dropout", 
        action='store_true',
        help='set dropout or False'
    )
    parser.add_argument(
        '--lambdaG',
        type=float,
        default=10,
        help='set the lambdaG_A&B'
    )
    parser.add_argument(
        "--paired", 
        action='store_true',
        help='set paired or False'
    )
    parser.add_argument(
        '--date',
        type=str,
        default=5.13,
        help='set a date'
    )
    parser.add_argument(
        '--dataset',
        type=str,
        default='368dataset',
        help='set a datasets'
    )
    parser.add_argument(
        "--G_rate", 
        type=int,
        default=1,
        help='set the G rate'
    )
    parser.add_argument(
        "--D_rate", 
        type=int,
        default=1,
        help='set the D rate'
    )
    parser.add_argument(
        "--epoch", 
        type=int,
        default=200,
        help='set epoch'
    )
    parser.add_argument(
        "--decay", 
        type=int,
        default=101,
        help='set decay'
    )
    parser.add_argument(
        '--lrG',
        type=float,
        default=2e-4,
        help='set learning rate of G'
    )
    parser.add_argument(
        '--lrD',
        type=float,
        default=2e-4,
        help='set learning rate of D'
    )
    parser.add_argument(
        '--dataset_path',
        type=str,
        default='/data/jiayuan/dataset',
        help='training dataset path'
    )
    parser.add_argument(
        '--save_image_path',
        type=str,
        default='/data/jiayuan/train_image/images_trip_cessim',
        help='set save temporary image path'
    )
    parser.add_argument(
        '--save_model',
        type=str,
        default='/data/jiayuan',
        help='set save model path'
    )
    FLAGS, unparsed = parser.parse_known_args()
    print("Parameter as following:")
    print(FLAGS)
    print("=========================================")
    main()




