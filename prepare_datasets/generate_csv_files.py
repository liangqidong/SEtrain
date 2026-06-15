import os
import pandas as pd
from pathlib import Path


def get_base_path():
    """
    获取脚本所在目录的绝对路径，确保在不同运行方式下都能正确定位。
    无论从哪个目录运行 python generate_csv_files.py，
    都能正确找到 prepare_datasets/ 目录。
    """
    # os.path.abspath 确保即使 __file__ 是相对路径也能得到绝对路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return Path(script_dir)


def find_wav_files_recursive(directory):
    """
    递归搜索目录及其所有子目录中的WAV文件
    过滤掉系统生成的隐藏文件（如以 ._ 开头的文件）
    """
    # 获取基准目录（脚本所在目录的绝对路径）
    base_dir = get_base_path()
    
    wav_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            # 检查是否是WAV文件，同时排除系统生成的隐藏文件
            if file.lower().endswith('.wav') and not file.startswith('._'):
                # 获取相对于脚本所在目录（prepare_datasets目录）的相对路径
                # 使用绝对路径计算，避免空字符串导致路径错乱
                abs_path = os.path.abspath(os.path.join(root, file))
                rel_path = os.path.relpath(abs_path, str(base_dir))
                # 确保路径以 ./ 开头
                if not rel_path.startswith('./'):
                    rel_path = './' + rel_path
                wav_files.append(rel_path)
    return sorted(wav_files)  # 排序以保证一致性

def generate_csv_files():
    """
    扫描 clean/, noise/, 和 rir/ 目录，并生成相应的 CSV 文件
    """
    base_path = get_base_path()  # 脚本所在目录的绝对路径 (prepare_datasets/)
    
    # 获取 clean 目录下的所有 wav 文件（递归搜索）
    clean_dir = base_path / "clean"
    clean_files = []
    if clean_dir.exists():
        clean_files = find_wav_files_recursive(clean_dir)
    
    # 获取 noise 目录下的所有 wav 文件（递归搜索）
    noise_dir = base_path / "noise"
    noise_files = []
    if noise_dir.exists():
        noise_files = find_wav_files_recursive(noise_dir)
    
    # 获取 rir 目录下的所有 wav 文件（递归搜索）
    rir_dir = base_path / "rir"
    rir_files = []
    if rir_dir.exists():
        rir_files = find_wav_files_recursive(rir_dir)
    
    # 如果没有找到 RIR 文件，至少保留一个占位符
    if not rir_files:
        rir_files = ['./dummy_rir.wav']  # 占位符
    
    # 生成 train_clean_dir.csv
    clean_data = {
        'file_dir': clean_files
    }
    clean_df = pd.DataFrame(clean_data)
    clean_csv_path = base_path / 'train_clean_dir.csv'
    clean_df.to_csv(clean_csv_path, index=False)
    print(f"Generated {clean_csv_path.name} with {len(clean_files)} files")
    
    # 生成 train_noise_dir.csv
    noise_data = {
        'file_dir': noise_files
    }
    noise_df = pd.DataFrame(noise_data)
    noise_csv_path = base_path / 'train_noise_dir.csv'
    noise_df.to_csv(noise_csv_path, index=False)
    print(f"Generated {noise_csv_path.name} with {len(noise_files)} files")
    
    # 生成 train_rir_dir.csv
    rir_data = {
        'file_dir': rir_files
    }
    rir_df = pd.DataFrame(rir_data)
    rir_csv_path = base_path / 'train_rir_dir.csv'
    rir_df.to_csv(rir_csv_path, index=False)
    print(f"Generated {rir_csv_path.name} with {len(rir_files)} files")
    
    print("\nCSV files generation completed!")
    # print(f"Clean files found: {clean_files}")
    # print(f"Noise files found: {noise_files}")
    # print(f"RIR files found: {rir_files}")

if __name__ == "__main__":
    generate_csv_files()