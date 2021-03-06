import argparse
import numpy as np
import matplotlib.pyplot as plt
import random
import os
import scipy.stats
import math
from os import path
from os.path import join


class_descriptions = [
    {
        'sprite': [
            [0, 1, 0],
            [1, 1, 1],
            [0, 1, 0]
        ],
        'sprite_x': 0,
        'sprite_y': 0
    },
    {
        'sprite': [
            [1, 1, 1],
            [1, 0, 1],
            [1, 1, 1]
        ],
        'sprite_x': 3,
        'sprite_y': 0
    },
    {
        'sprite': [
            [1, 0, 0],
            [1, 1, 0],
            [1, 1, 1]
        ],
        'sprite_x': 0,
        'sprite_y': 3
    },
    {
        'sprite': [
            [1, 1, 1],
            [0, 1, 0],
            [0, 1, 0]
        ],
        'sprite_x': 3,
        'sprite_y': 3
    }
]


def class_descriptions_to_class_pics(num_classes, image_size):
    class_pics = []
    for i, desc in enumerate(class_descriptions):
        if i >= num_classes:
            break
        pic = np.zeros((image_size, image_size), dtype=np.float32)
        for dx in range(3):
            for dy in range(3):
                if desc['sprite'][dy][dx] == 1:
                    pic[desc['sprite_y'] + dy, desc['sprite_x'] + dx] = 1.0
        class_pics.append(pic)
    return class_pics


def print_images(filepath, image_infos, image_min=-1, image_max=2):
    """
    image_infos is list of dicts.  It can be 1d or 2d
    each dict has:
    - title (string)
    - data (np.array)
    """
    plt.clf()
    plt.figure(1)
    if not isinstance(image_infos, list):
        image_infos = [image_infos]
    if not isinstance(image_infos[0], list):
        image_infos = [image_infos]
    rows = len(image_infos)
    cols = len(image_infos[0])

    for row, row_infos in enumerate(image_infos):
        for col, image_info in enumerate(row_infos):
            if 'data' not in image_info:
                continue
            image = image_info['data']
            image_rows = image.shape[0]
            image_cols = image.shape[1]
            image_range = image_max - image_min
            image = np.maximum(image_min, image)
            image = np.minimum(image_max, image)
            image = (image - image_min) / image_range
            image_rgb = np.zeros((image_rows, image_cols, 3), dtype=np.float32)
            image_rgb[:, :, 0] = image
            image_rgb[:, :, 1] = image
            image_rgb[:, :, 2] = image
            plt.subplot(rows, cols, row * cols + col + 1)
            plt.imshow(image_rgb, interpolation='nearest')
            plt.axis('off')
            if image_info.get('title', None) is not None:
                plt.title(image_info['title'])
    plt.savefig(filepath)


def draw_samples(out_dir, image_size, num_classes, sigma_X, N, class_pics):
    samples = []
    ground_truth_Z = np.zeros((N, num_classes), dtype=np.int8)
    images_to_print = []
    num_cols = int(math.sqrt(N))
    images_row = []
    for n in range(N):
        image = np.zeros((image_size, image_size), dtype=np.float32)
        features = np.random.choice(2, size=(num_classes,))
        ground_truth_Z[n] = features
        for k, v in enumerate(features):
            if v == 1:
                image += class_pics[k]

        noise = np.random.randn(image_size, image_size).astype(np.float32) * sigma_X

        image += noise
        images_row.append({'data': image})
        if(len(images_row)) == num_cols:
            images_to_print.append(images_row)
            images_row = []

        samples.append(image)

    if len(images_row) > 0:
        images_to_print.append(images_row)

    print_images(join(out_dir, 'samples.png'), images_to_print)
    print_images(join(out_dir, 'samples_Z.png'), {'data': 1 - ground_truth_Z}, image_min=0, image_max=1)
    return samples, ground_truth_Z


def columns_to_array(columns):
    if len(columns) == 0:
        return None
    rows = columns[0].shape[0]
    cols = len(columns)
    array = np.zeros((rows, cols), dtype=np.float32)
    for col, column in enumerate(columns):
        array[:, col] = column
    return array


def calc_log_p_X_given_Z(Z, X, sigma_X, sigma_A):
    #     print('Z', Z)
    ZTZI = Z.T.dot(Z) + (sigma_X * sigma_X / sigma_A / sigma_A) * np.identity(Z.shape[1])
#     print('ZTZI', ZTZI)
    ZTZIInv = np.linalg.inv(ZTZI)
#     print('ZTZIInv', ZTZIInv)
    IZZZIZ = np.identity(Z.shape[0]) - Z.dot(ZTZIInv).dot(Z.T)
#     print('IZZZIZ\n', IZZZIZ)
    XT___X = X.T.dot(IZZZIZ).dot(X)
#     print('XT___X\n', XT___X)
    trace_term = np.trace(XT___X)
#     print('trace_term', trace_term)
    exponent = - 1 / (sigma_X * sigma_X * 2) * trace_term
#     print('exponent', exponent)
    return exponent
#     gaussian_unnorm = np.exp(exponent)
#     print('gaussian prob [%s]' % gaussian_unnorm)
#     return gaussian_unnorm


def print_A(img_path, image_size, sigma_X, sigma_A, X, Z):
    I = sigma_X * sigma_X / (sigma_A * sigma_A) * np.identity(Z.shape[1])
    ZTZI = Z.T.dot(Z) + I
    ZTX = Z.T.dot(X)

    # print('ZTX\n', ZTX)
    E_A = np.linalg.solve(ZTZI, ZTX)

    # just for debugging:
    ZTZIinvZT = np.linalg.inv(ZTZI).dot(Z.T)
    # print('ZTZIinvZT', ZTZIinvZT)
    print_images(
        img_path + '_ZTZIinvZT.png', {'data': ZTZIinvZT.T},
        image_min=np.min(ZTZIinvZT), image_max=np.max(ZTZIinvZT))

    print_images(
        img_path + '_Z.png', {'data': Z})

    image_infos = []
    for k in range(E_A.shape[0]):
        image_flat = E_A[k]
        image = image_flat.reshape(image_size, image_size)
        image_infos.append({'data': image})
    print_images(img_path, image_infos)
    return E_A


def samples_to_X(samples):
    N = len(samples)
    X_features = samples[0].shape[0] * samples[0].shape[1]
    X = np.zeros((N, X_features), dtype=np.float32)
    for n, sample in enumerate(samples):
        X[n] = sample.reshape(X_features)
    return X


def run(
        print_every, num_its, N, num_classes, image_size, alpha, sigma_X, sigma_A, out_dir,
        new_features_ignore_posterior=False):
    if not path.isdir(out_dir):
        os.makedirs(out_dir)

    class_pics = class_descriptions_to_class_pics(
        num_classes=num_classes, image_size=image_size)

    samples, ground_truth_Z = draw_samples(
        out_dir=out_dir, image_size=image_size, num_classes=num_classes,
        sigma_X=sigma_X, N=N, class_pics=class_pics)

    Z_columns = []
    column = np.random.choice(2, (N,))
    Z_columns.append(column)
    # K_plus = len(Z_columns)
    M = []
    M.append(np.sum(Z_columns[0]))

    X = samples_to_X(samples)
    print('X.shape', X.shape)
    np.set_printoptions(suppress=False, precision=3)
    for filename in os.listdir(out_dir):
        if filename.startswith('A_draws_it') and filename.endswith('.png'):
            os.unlink(join(out_dir, filename))
    print_A(
        img_path=join(out_dir, 'A_from_ground_truth_Z.png'), image_size=image_size,
        X=X, Z=ground_truth_Z, sigma_X=sigma_X, sigma_A=sigma_A)
    # sigma_X = 1
    for it in range(num_its):
        num_added = 0
        num_removed = 0
        for n in range(N):
            k = 0
            while k < len(Z_columns):
                old_zik = Z_columns[k][n]
                if old_zik == 1:
                    m_minusi_k = M[k] - 1
                else:
                    m_minusi_k = M[k]
                if m_minusi_k > 0:
                    # get the probabilty of z_ik given Z_minus_ik, for
                    # zik = 0 and zik = 1
                    p_zik_given_Zminus = np.zeros((2,), dtype=np.float32)
                    p_zik_given_Zminus[1] = m_minusi_k / N
                    p_zik_given_Zminus[0] = 1.0 - m_minusi_k / N

                    # we need also to get the probability from the gaussian, again
                    # for zik=0 and zik=1
                    # for now, lets just stupidly calculate it, not do rank-1s or anything

                    # calculate as log first, then normalize this first, then
                    # exp it, to avoid crazily tiny values etc
                    log_p_X_given_Z = np.zeros((2,), dtype=np.float32)
                    for zik in [0, 1]:
                        Z_columns[k][n] = zik
                        log_p_X_given_Z[zik] = calc_log_p_X_given_Z(
                            columns_to_array(Z_columns), X, sigma_X, sigma_A)
    #                 print('log_p_X_given_Z', log_p_X_given_Z)
                    log_p_X_given_Z -= np.min(log_p_X_given_Z)

                    # if either of the log probs are more than 12, then its
                    # basically infinitely likely we'll choose that one, so we
                    # just choose it directly
                    if np.max(log_p_X_given_Z) > 12:
                        if log_p_X_given_Z[1] > log_p_X_given_Z[0]:
                            new_zik = 1
                        else:
                            new_zik = 0
                    else:
                        p_X_given_Z = np.exp(log_p_X_given_Z)

                        p_zik_given_X_Z_unnorm = np.multiply(
                            p_zik_given_Zminus, p_X_given_Z)
                        p_zik_given_X_Z = p_zik_given_X_Z_unnorm / np.sum(p_zik_given_X_Z_unnorm)

                        prob_zik_one = p_zik_given_X_Z[1]

                        p = random.uniform(0, 1)
                        new_zik = 1 if p <= prob_zik_one else 0

                    Z_columns[k][n] = new_zik
                    M[k] += new_zik - old_zik
                else:
                    del M[k]
                    del Z_columns[k]
                    num_removed += 1
                    k -= 1

                k += 1
            # add new features
            k1_range = 3
            # we calculate the posterior probability for each possible
            # number of new features, for a smallish range, up to
            # some reasonable upperbound, here 2
            log_p_next = np.zeros((k1_range,), dtype=np.float32)
            Z = columns_to_array(Z_columns)
            for k1 in range(k1_range):
                log_prior_p = scipy.stats.poisson.logpmf(k1, alpha / N)
                if new_features_ignore_posterior:
                    log_p_next[k1] = log_prior_p
                else:
                    if k1 == 0:
                        Z_k1 = Z
                    else:
                        Z_k1 = np.zeros((N, Z.shape[1] + k1), dtype=np.float32)
                        Z_k1[:, :Z.shape[1]] = Z
                        Z_k1[n, Z.shape[1]:].fill(1)
                    log_posterior = calc_log_p_X_given_Z(
                        Z_k1, X, sigma_X, sigma_A)
                    log_p_next[k1] = log_prior_p + log_posterior
            log_p_next -= np.max(log_p_next)
            p_next = np.exp(log_p_next)
            p_next /= np.sum(p_next)
            num_new_features = np.random.choice(a=k1_range, p=p_next)
            for j in range(num_new_features):
                M.append(1)
                new_col = np.zeros((N,), dtype=np.float32)
                new_col[n] = 1
                Z_columns.append(new_col)
                num_added += 1

        if (it + 1) % print_every == 0:
            print('it %s' % (it + 1))
            it_str = str(it + 1)
            while len(it_str) < 3:
                it_str = '0' + it_str
            Z = columns_to_array(Z_columns)
            if Z is not None:
                print_A(
                    img_path=join(out_dir, 'A_draws_it%s.png' % it_str), X=X, Z=Z,
                    sigma_X=sigma_X, sigma_A=sigma_A, image_size=image_size)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--num-classes', type=int, default=4)
    parser.add_argument('--image-size', type=int, default=6)
    parser.add_argument('--N', type=int, default=100)
    # num_samples_to_print = 7
    parser.add_argument('--sigma-X', type=float, default=0.5)
    parser.add_argument('--sigma-A', type=float, default=1.0)
    parser.add_argument('--alpha', type=float, default=0.07)
    parser.add_argument('--num-its', type=int, default=1000)
    parser.add_argument('--print-every', type=int, default=1)
    parser.add_argument('--out-dir', type=str, default='/tmp/toysamples1')
    parser.add_argument(
        '--new-features-ignore-posterior', action='store_true',
        help='if true, number of new features comes just from Poisson prior, not from '
             'checking also posterior probability based on X')
    args = parser.parse_args()
    run(**args.__dict__)
