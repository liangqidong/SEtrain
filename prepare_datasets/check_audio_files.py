import os
import pandas as pd
import soundfile as sf
from tqdm import tqdm

def check_audio_files_with_progress(csv_file_path, base_path, output_log_file):
    """
    检查CSV文件中列出的所有音频文件是否存在、可读及基本信息，并输出错误日志
    """
    print(f"正在检查CSV文件: {csv_file_path}")
    
    # 读取CSV文件
    df = pd.read_csv(csv_file_path)
    file_paths = df['file_dir'].tolist()
    
    print(f"总共找到 {len(file_paths)} 个文件路径")
    print("-" * 80)
    
    valid_files = []
    invalid_files = []
    
    # 使用tqdm显示进度条
    for idx, rel_path in enumerate(tqdm(file_paths, desc=f"检查 {os.path.basename(csv_file_path)}", unit="file")):
        # 构建完整路径
        full_path = os.path.join(base_path, rel_path)
        
        # 检查文件是否存在
        if not os.path.exists(full_path):
            invalid_files.append((rel_path, "文件不存在"))
            continue
        
        # 检查文件大小
        file_size = os.path.getsize(full_path)
        if file_size < 44:  # WAV文件最小应有头部
            invalid_files.append((rel_path, f"文件过小 ({file_size} bytes)"))
            continue
        
        # 尝试读取音频信息
        try:
            info = sf.info(full_path)
            
            # 尝试读取一小段音频数据
            data, _ = sf.read(full_path, start=0, stop=min(1000, int(info.samplerate * info.duration)))
            if len(data) == 0:
                invalid_files.append((rel_path, "音频数据为空"))
            else:
                valid_files.append(rel_path)
                
        except Exception as e:
            invalid_files.append((rel_path, f"读取失败: {str(e)}"))
    
    print(f"\n检查完成! 总计: {len(file_paths)}, 有效: {len(valid_files)}, 无效: {len(invalid_files)}")
    
    # 写入错误日志文件
    with open(output_log_file, 'w', encoding='utf-8') as log_file:
        log_file.write(f"音频文件检查报告 - {csv_file_path}\n")
        log_file.write("="*80 + "\n")
        log_file.write(f"总计文件数: {len(file_paths)}\n")
        log_file.write(f"有效文件数: {len(valid_files)}\n")
        log_file.write(f"无效文件数: {len(invalid_files)}\n\n")
        
        if invalid_files:
            log_file.write("无效文件列表:\n")
            log_file.write("-"*80 + "\n")
            for path, reason in invalid_files:
                log_file.write(f"文件: {path}\n")
                log_file.write(f"原因: {reason}\n")
                log_file.write("-"*40 + "\n")
        else:
            log_file.write("所有文件均有效!\n")
    
    return valid_files, invalid_files

if __name__ == "__main__":
    # 获取当前脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 定义要检查的CSV文件
    csv_files = [
        ("train_clean_dir.csv", os.path.join(script_dir, "train_clean_dir.csv")),
        ("train_noise_dir.csv", os.path.join(script_dir, "train_noise_dir.csv")), 
        ("train_rir_dir.csv", os.path.join(script_dir, "train_rir_dir.csv"))
    ]
    
    print("开始检查音频文件...")
    print(f"基础路径: {script_dir}\n")
    
    all_results = {}
    
    for name, csv_file in csv_files:
        if os.path.exists(csv_file):
            log_file = os.path.join(script_dir, f"{name.replace('.csv', '_errors.log')}")
            print(f"\n检查 {name}:")
            valid, invalid = check_audio_files_with_progress(csv_file, script_dir, log_file)
            all_results[name] = {"valid": len(valid), "invalid": len(invalid), "log_file": log_file}
        else:
            print(f"❌ CSV文件不存在: {csv_file}")
    
    print("\n" + "="*80)
    print("总结报告:")
    for csv_name, stats in all_results.items():
        print(f"{csv_name}: 有效 {stats['valid']} 个, 无效 {stats['invalid']} 个")
        print(f"  错误日志文件: {stats['log_file']}")
    
    print("\n检查完成！错误详情已保存到对应的日志文件中。")