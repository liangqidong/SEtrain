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
        s1_ref = s1_ref /M

    return mix, s1_ref


if __name__ == "__main__":
    np.random.seed(10)
    
    flag = 'train'
    
    # 根据您的数据量，建议生成50000个样本（或您可以根据需要调整）
    # 基于最小数据集（noise: 65303条）来确定生成数量
    num_tot = min(50000, 65303)  # 使用噪声数据的总数作为上限
    
    nfill = len(str(num_tot))
    
    fs = 16000
    wav_len = 10  # in seconds
    random_start = True
    snr_range = [-5, 15]
    
    # 使用当前工作目录作为保存根目录，避免权限问题
    save_root = './DNS3/'
    
    # 获取当前脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if not script_dir:
        script_dir = '.'
    
    print(f"Current working directory: {os.getcwd()}")
    print(f"Script directory: {script_dir}")
    
    # 数据根目录设为脚本所在目录
    data_root = script_dir
    
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

    # 读取所有数据
    clean_list_all = pd.read_csv(clean_csv)['file_dir'].tolist()
    noise_list_all = pd.read_csv(noise_csv)['file_dir'].tolist()
    rir_list_all = pd.read_csv(rir_csv)['file_dir'].tolist()
    
    print(f"Total clean files: {len(clean_list_all)}")
    print(f"Total noise files: {len(noise_list_all)}")
    print(f"Total rir files: {len(rir_list_all)}")
    
    # 检查列表是否为空
    if len(clean_list_all) == 0:
        print("Error: Clean list is empty!")
        sys.exit(1)
    if len(noise_list_all) == 0:
        print("Error: Noise list is empty!")
        sys.exit(1)
    if len(rir_list_all) == 0:
        print("Error: RIR list is empty!")
        sys.exit(1)
    
    # 根据数据量决定生成多少样本
    # 为了平衡数据使用，我们可以基于最小的数据集来确定生成数量
    min_dataset_size = min(len(clean_list_all), len(noise_list_all), len(rir_list_all))
    actual_num_tot = min(num_tot, min_dataset_size)
    
    print(f"Generating {actual_num_tot} samples (limited by smallest dataset: {min_dataset_size})")
    
    # 随机打乱并选择指定数量的数据
    clean_list = np.random.choice(clean_list_all, actual_num_tot, replace=len(clean_list_all) < actual_num_tot).tolist()
    noise_list = np.random.choice(noise_list_all, actual_num_tot, replace=len(noise_list_all) < actual_num_tot).tolist()
    rir_list = np.random.choice(rir_list_all, actual_num_tot, replace=len(rir_list_all) < actual_num_tot).tolist()

    snr_list = np.random.uniform(snr_range[0], snr_range[1], size=actual_num_tot)
    
    info = pd.DataFrame([str(idx+1).zfill(nfill)+'.wav' for idx in range(actual_num_tot)], columns=['file_name'])
    info['clean'] = clean_list
    info['noise'] = noise_list
    info['snr'] = snr_list
    
    # 创建输出目录
    os.makedirs(os.path.join(save_root, f'{flag}_noisy'), exist_ok=True)
    os.makedirs(os.path.join(save_root, f'{flag}_clean'), exist_ok=True)
    
    info.to_csv(os.path.join(save_root, f'{flag}_INFO.csv'), index=None)
    
    print(f"Starting to generate {actual_num_tot} audio pairs...")
    
    for idx in tqdm(range(actual_num_tot)):  # 只迭代实际生成的数量
        
        if random_start:
            start_s = int(np.random.uniform(0, 15 - wav_len)) * fs
            start_n = int(np.random.uniform(0, 30 - wav_len)) * fs
        else:
            start_s = 0
            start_n = 0
        
        # 构建完整的文件路径 - 修正路径构建逻辑
        # 首先解析CSV中的路径（移除 ./ 前缀）
        # 注意：不能用 lstrip('./')，因为它会按字符集去除所有前导的 '.' 和 '/'
        # 例如 "./rir/..." 会被错误处理为 "rir/..."（看似正确），
        # 但 "../rir/..." 会被处理为 "rir/..."（错误！去掉了 "../" 前缀）
        def strip_dot_slash(path_str):
            """安全地移除路径开头的 './' 前缀"""
            while path_str.startswith('./'):
                path_str = path_str[2:]
            return path_str
        
        clean_relative_path = strip_dot_slash(clean_list[idx])
        noise_relative_path = strip_dot_slash(noise_list[idx])
        rir_relative_path = strip_dot_slash(rir_list[idx])
        
        # 然后构建完整路径
        clean_path = os.path.join(data_root, clean_relative_path)
        noise_path = os.path.join(data_root, noise_relative_path)
        rir_path = os.path.join(data_root, rir_relative_path)
        
        # 规范化路径，解决任何可能的路径问题
        clean_path = os.path.normpath(clean_path)
        noise_path = os.path.normpath(noise_path)
        rir_path = os.path.normpath(rir_path)
        
        # 添加文件存在性检查
        if not os.path.exists(clean_path):
            print(f"Error: Clean audio file does not exist: {clean_path}")
            continue  # 跳过当前文件，继续下一个
        if not os.path.exists(noise_path):
            print(f"Error: Noise audio file does not exist: {noise_path}")
            continue  # 跳过当前文件，继续下一个
        if not os.path.exists(rir_path):
            print(f"Error: RIR audio file does not exist: {rir_path}")
            continue  # 跳过当前文件，继续下一个
        
        # 检查文件大小
        clean_size = os.path.getsize(clean_path)
        noise_size = os.path.getsize(noise_path)
        rir_size = os.path.getsize(rir_path)
        
        # 检查文件是否太小
        if clean_size < 44:  # WAV header is typically 44 bytes
            print(f"Warning: Clean file too small: {clean_path} (size: {clean_size})")
            continue
        if noise_size < 44:
            print(f"Warning: Noise file too small: {noise_path} (size: {noise_size})")
            continue
        if rir_size < 44:
            print(f"Warning: RIR file too small: {rir_path} (size: {rir_size})")
            continue
        
        try:
            # 先获取文件信息
            clean_info = sf.info(clean_path)
            noise_info = sf.info(noise_path)
            rir_info = sf.info(rir_path)
            
            # 检查音频长度是否足够
            if clean_info.duration < wav_len:
                # 如果不够长，就读取整个文件
                clean = sf.read(clean_path, dtype='float32')[0]
            else:
                clean = sf.read(clean_path, dtype='float32', start=start_s, stop=start_s + wav_len*fs)[0]
                
            if noise_info.duration < wav_len:
                # 如果不够长，就读取整个文件
                noise = sf.read(noise_path, dtype='float32')[0]
            else:
                noise = sf.read(noise_path, dtype='float32', start=start_n, stop=start_n + wav_len*fs)[0]
            
            rir = sf.read(rir_path, dtype='float32')[0]
            
        except Exception as e:
            print(f"Error reading audio files: {e}")
            print(f"Paths: clean={clean_path}, noise={noise_path}, rir={rir_path}")
            continue  # 跳过当前文件，继续下一个
        
        # 检查读取的信号是否为空
        if len(clean) == 0:
            print(f"Warning: Clean signal is empty: {clean_path}")
            continue
        if len(noise) == 0:
            print(f"Warning: Noise signal is empty: {noise_path}")
            continue
        if len(rir) == 0:
            print(f"Warning: RIR signal is empty: {rir_path}")
            continue
            
        if len(rir.shape) > 1:
            rir = rir[:, 0]
        max_index = np.argmax(np.abs(rir))
        rir = rir[max_index:]
        rir_e = rir[:min(int(100 * 16000 / 1000), len(rir))]  # rir_e: early rir, 选取前100ms的rir，用来生成低混响的干净语音 
        
        rev_clean = add_pyreverb(clean, rir)   # reverbrant clean speech
        drb_clean = add_pyreverb(clean, rir_e) # clean speech with low reverbration
        
        try:
            mixture, target = mk_mixture(rev_clean, noise, drb_clean, snr_list[idx], eps=1e-8)
        except ValueError as e:
            print(f"Error in mk_mixture: {e}")
            print(f"Paths: clean={clean_path}, noise={noise_path}, rir={rir_path}")
            print(f"Signal lengths - clean: {len(clean)}, noise: {len(noise)}, rir: {len(rir)}, rir_e: {len(rir_e)}")
            continue  # 跳过当前文件，继续下一个
        
        sf.write(os.path.join(save_root, f'{flag}_noisy', str(idx+1).zfill(nfill)+'.wav'), mixture, fs)
        sf.write(os.path.join(save_root, f'{flag}_clean', str(idx+1).zfill(nfill)+'.wav'), target, fs)
    
    print(f"Data generation completed! Generated {actual_num_tot} audio pairs.")