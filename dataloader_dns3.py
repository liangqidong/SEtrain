import os
import glob
import soundfile as sf
import torch
from torch.utils import data
import numpy as np
import random


def find_wav_files(directory):
    """查找目录下所有 wav 文件（替代 librosa.util.find_files，避免 pkg_resources 依赖）"""
    if not os.path.isdir(directory):
        return []
    pattern = os.path.join(directory, '**', '*.wav')
    return sorted(glob.glob(pattern, recursive=True))


# 默认数据路径：指向 gen_DNS3_datasets.py 生成的数据
# 可通过环境变量 DNS3_DATA_ROOT 覆盖
_DEFAULT_DATA_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prepare_datasets', 'DNS3')
NOISY_DATABASE_TRAIN = os.environ.get('DNS3_DATA_ROOT', _DEFAULT_DATA_ROOT) + '/train_noisy'
NOISY_DATABASE_VALID = os.environ.get('DNS3_DATA_ROOT', _DEFAULT_DATA_ROOT) + '/dev_noisy'


class DNS3Dataset(torch.utils.data.Dataset):
    def __init__(
        self,
        fs=16000,
        length_in_seconds=8,
        num_data_tot=720000,
        num_data_per_epoch=40000,
        random_start_point=False,
        train=True
    ):
        if train:
            print("You are using this DNS3 training data:", NOISY_DATABASE_TRAIN)
        else:
            print("You are using this DNS3 validation data:", NOISY_DATABASE_VALID)
        self.noisy_database_train = find_wav_files(NOISY_DATABASE_TRAIN)[:num_data_tot]
        self.noisy_database_valid = find_wav_files(NOISY_DATABASE_VALID)
        # 如果验证集为空，回退使用训练集作为验证集
        if not self.noisy_database_valid:
            print("[WARNING] Validation set is empty, falling back to training set for validation")
            self.noisy_database_valid = self.noisy_database_train
        self.L = int(length_in_seconds * fs)
        self.random_start_point = random_start_point
        self.fs = fs
        self.length_in_seconds = length_in_seconds
        self.num_data_per_epoch = num_data_per_epoch
        self.train = train

    def sample_data_per_epoch(self):
        self.noisy_data_train = random.sample(self.noisy_database_train, self.num_data_per_epoch)

    def __getitem__(self, idx):
        if self.train:
            noisy_list = self.noisy_data_train
        else:
            noisy_list = self.noisy_database_valid

        if self.random_start_point:
            Begin_S = int(np.random.uniform(0, 10 - self.length_in_seconds)) * self.fs
            noisy, _ = sf.read(noisy_list[idx], dtype='float32', start=Begin_S, stop=Begin_S + self.L)
            clean, _ = sf.read(noisy_list[idx].replace('noisy', 'clean'), dtype='float32', start=Begin_S, stop=Begin_S + self.L)

        else:
            noisy, _ = sf.read(noisy_list[idx], dtype='float32', start=0, stop=self.L)
            clean, _ = sf.read(noisy_list[idx].replace('noisy', 'clean'), dtype='float32', start=0, stop=self.L)

        return noisy, clean

    def __len__(self):
        if self.train:
            return self.num_data_per_epoch
        else:
            return len(self.noisy_database_valid)


if __name__ == '__main__':
    from tqdm import tqdm
    from omegaconf import OmegaConf

    config = OmegaConf.load('configs/cfg_train.yaml')

    train_dataset = DNS3Dataset(**config['train_dataset'])
    train_dataloader = data.DataLoader(train_dataset, **config['train_dataloader'])
    train_dataloader.dataset.sample_data_per_epoch()

    validation_dataset = DNS3Dataset(**config['validation_dataset'])
    validation_dataloader = data.DataLoader(validation_dataset, **config['validation_dataloader'])

    print(len(train_dataloader), len(validation_dataloader))

    for noisy, clean in tqdm(train_dataloader):
        print(noisy.shape, clean.shape)
        break

    for noisy, clean in tqdm(validation_dataloader):
        print(noisy.shape, clean.shape)
        break