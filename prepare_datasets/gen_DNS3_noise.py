import os
import random
import numpy as np
import pandas as pd
import soundfile as sf
from scipy import signal
from tqdm import tqdm
import sys

def add_pyreverb(clean_speech, rir):
    # max_index = np.argmax(np.abs(rir))
    # rir = rir[max_index:]
    reverb_speech = signal.fftconvolve(clean_speech, rir, mode="full")
    
    # make reverb_speech same length as clean_speech
    reverb_speech = reverb_speech[: clean_speech.shape[0]]

    return reverb_speech


def mk_mixture(s1, s2, s1_ref, snr, eps=1e-8):
    """
    s1: reverbrant speech
    s2: reverbrant speech or noise
    s1_ref: s1 with low reverbration, as target in training
    """
    # 检查输入信号是否为空
    if len(s1) == 0 or len(s2) == 0 or len(s1_ref) == 0:
        raise ValueError("Input signals s1, s2, or s1_ref are empty!")
    
    # 确保所有信号长度一致（截断或补零）
    min_len = min(len(s1), len(s2), len(s1_ref))
    s1 = s1[:min_len]
    s2 = s2[:min_len]
    s1_ref = s1_ref[:min_len]

    amp = 0.5 * np.random.rand() + 0.01
    s1_ref = amp * s1_ref / (np.max(np.abs(s1)) + eps) 
    s1 = amp * s1 / (np.max(np.abs(s1)) + eps) 
    norm_sig1 = s1

    norm_sig2 = s2 * np.math.sqrt(np.sum(s1 ** 2) + eps) / np.math.sqrt(np.sum(s2 ** 2) + eps)
    alpha = 10**(-snr*1.5 / 20)
    freq_num = np.random.randint(0, 4)
    sins = np.zeros(len(s1))
    if freq_num > 1:
        freq = np.random.choice(range(50, 8000), freq_num)
        for f in freq:
            s_sin = np.sin(2*np.pi * f * np.arange(len(s1)) / 16000)
            sins = sins + (0.5*np.random.rand() + 0.5) * alpha * s_sin * np.math.sqrt(np.sum(s1 ** 2) + eps) / np.math.sqrt(np.sum(s_sin ** 2) + eps)
    
    mix = norm_sig1 + alpha * norm_sig2 + sins
    # mix = norm_sig1 + alpha * norm_sig2
    
    M = max(np.max(abs(mix)), np.max(abs(norm_sig1)), np.max(abs(alpha*norm_sig2))) + eps
    if M > 1.0:    
        mix = mix / M
        norm_sig1 = norm_sig1 / M
        norm_sig2 = norm_sig2 / M
        s1_ref = s1_ref / M

    return mix, s1_ref


if __name__ == "__main__":
    np.random.seed(10)
    
    flag = 'train'
    num_tot = 50000
    nfill = len(str(num_tot))
    
    fs = 16000
    wav_len = 10  # in seconds
    random_start = True
    snr_range = [-5, 15]
    
    # 修改输出路径，确保它存在
    save_root = '/export/shaohua/DNS3/'  # 你可以在服务器上创建此目录
    
    # 使用绝对路径或相对于当前脚本的路径来查找CSV文件
    script_dir = os.path.dirname(os.path.abspath(__file__))  # 获取当前脚本所在目录
    data_root = script_dir  # 数据根目录设为脚本所在目录
    
    clean_csv = os.path.join(data_root, f'{flag}_clean_dir.csv')
    noise_csv = os.path.join(data_root, f'{flag}_noise_dir.csv')
    rir_csv = os.path.join(data_root, f'{flag}_rir_dir.csv')

    print(f"Loading clean CSV from: {clean_csv}")
    print(f"Loading noise CSV from: {noise_csv}")
    print(f"Loading rir CSV from: {rir_csv}")
    
    # 添加错误检查
    if not os.path.exists(clean_csv):
        print(f"Error: Clean CSV file does not exist: {clean_csv}")
        sys.exit(1)
    if not os.path.exists(noise_csv):
        print(f"Error: Noise CSV file does not exist: {noise_csv}")
        sys.exit(1)
    if not os.path.exists(rir_csv):
        print(f"Error: RIR CSV file does not exist: {rir_csv}")
        sys.exit(1)

    clean_list = pd.read_csv(clean_csv)['file_dir'].tolist()[: num_tot]
    noise_list = pd.read_csv(noise_csv)['file_dir'].tolist()[: num_tot]
    rir_list = pd.read_csv(rir_csv)['file_dir'].tolist()[: num_tot]
    
    # 检查列表是否为空
    if len(clean_list) == 0:
        print("Error: Clean list is empty!")
        sys.exit(1)
    if len(noise_list) == 0:
        print("Error: Noise list is empty!")
        sys.exit(1)
    if len(rir_list) == 0:
        print("Error: RIR list is empty!")
        sys.exit(1)
    
    # 循环使用列表，确保有足够的数据
    original_clean_len = len(clean_list)
    original_noise_len = len(noise_list)
    original_rir_len = len(rir_list)
    
    # 如果列表长度小于num_tot，则循环使用
    if len(clean_list) < num_tot:
        clean_list = [clean_list[i % original_clean_len] for i in range(num_tot)]
    if len(noise_list) < num_tot:
        noise_list = [noise_list[i % original_noise_len] for i in range(num_tot)]
    if len(rir_list) < num_tot:
        rir_list = [rir_list[i % original_rir_len] for i in range(num_tot)]

    snr_list = np.random.uniform(snr_range[0], snr_range[1], size=num_tot)
    
    info = pd.DataFrame([str(idx+1).zfill(nfill)+'.wav' for idx in range(num_tot)], columns=['file_name'])
    info['clean'] = clean_list
    info['noise'] = noise_list
    info['snr'] = snr_list
    
    # 创建输出目录
    os.makedirs(os.path.join(save_root, f'{flag}_noisy'), exist_ok=True)
    os.makedirs(os.path.join(save_root, f'{flag}_clean'), exist_ok=True)
    
    info.to_csv(os.path.join(save_root, f'{flag}_INFO.csv'), index=None)
    
    for idx in tqdm(range(min(num_tot, len(clean_list)))):  # 只迭代实际可用的数量
        
        if random_start:
            start_s = int(np.random.uniform(0, 15 - wav_len)) * fs
            start_n = int(np.random.uniform(0, 30 - wav_len)) * fs
        else:
            start_s = 0
            start_n = 0
        
        # 构建绝对路径
        clean_path = os.path.join(script_dir, clean_list[idx])
        noise_path = os.path.join(script_dir, noise_list[idx])
        rir_path = os.path.join(script_dir, rir_list[idx])
        
        print(f"Processing idx={idx}: clean={clean_path}, noise={noise_path}, rir={rir_path}")
        
        # 添加文件存在性检查
        if not os.path.exists(clean_path):
            print(f"Error: Clean audio file does not exist: {clean_path}")
            sys.exit(1)
        if not os.path.exists(noise_path):
            print(f"Error: Noise audio file does not exist: {noise_path}")
            sys.exit(1)
        if not os.path.exists(rir_path):
            print(f"Error: RIR audio file does not exist: {rir_path}")
            sys.exit(1)
        
        try:
            clean = sf.read(clean_path, dtype='float32', start=start_s, stop=start_s + wav_len*fs)[0]
            noise = sf.read(noise_path, dtype='float32', start=start_n, stop=start_n + wav_len*fs)[0]
            rir = sf.read(rir_path, dtype='float32')[0]
        except Exception as e:
            print(f"Error reading audio files: {e}")
            print(f"Paths: clean={clean_path}, noise={noise_path}, rir={rir_path}")
            sys.exit(1)
        
        # 检查读取的信号是否为空
        if len(clean) == 0:
            print(f"Error: Clean signal is empty: {clean_path}")
            continue
        if len(noise) == 0:
            print(f"Error: Noise signal is empty: {noise_path}")
            continue
        if len(rir) == 0:
            print(f"Error: RIR signal is empty: {rir_path}")
            continue
            
        if len(rir.shape) > 1:
            rir = rir[:, 0]
        max_index = np.argmax(np.abs(rir))
        rir = rir[max_index:]
        rir_e = rir[:min(int(100 * 16000 / 1000), len(rir))]  # rir_e: early rir, 选取前100ms的rir，用来生成低混响的干净语音 
        
        rev_clean = add_pyreverb(clean, rir)   # reverbrant clean speech
        drb_clean = add_pyreverb(clean, rir_e) # clean speech with low reverbration
        
        mixture, target = mk_mixture(rev_clean, noise, drb_clean, snr_list[idx], eps=1e-8)
        
        sf.write(os.path.join(save_root, f'{flag}_noisy', str(idx+1).zfill(nfill)+'.wav'), mixture, fs)
        sf.write(os.path.join(save_root, f'{flag}_clean', str(idx+1).zfill(nfill)+'.wav'), target, fs)