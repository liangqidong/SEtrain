# SEtrain 项目执行文档

> 适用环境：Linux（路径示例 `/root/shaohua/SE/SEtrain`）
> 框架：DNS Challenge 3 (INTERSPEECH 2021) 基线 + GTCRN end-to-end 模型
> 目标：从零开始打通「环境搭建 → 数据下载 → 数据合成 → 训练 → 推理 → 评估」

---

## 目录

1. [环境准备](#1-环境准备)
2. [数据集下载](#2-数据集下载)
3. [生成数据索引](#3-生成数据索引)
4. [校验数据完整性](#4-校验数据完整性可选)
5. [离线合成训练数据](#5-离线合成训练数据)
6. [启动训练](#6-启动训练)
7. [推理与评估](#7-推理与评估)
8. [完整数据正式训练](#8-完整数据正式训练)
9. [常见问题](#9-常见问题-faq)

---

## 1. 环境准备

### 1.1 系统依赖（Ubuntu/Debian）

```bash
sudo apt update
sudo apt install -y build-essential python3-dev wget unzip git
```

### 1.2 创建 Python 环境（二选一）

**方式 A：Conda（推荐）**
```bash
conda create -n lqd_se python=3.9 -y
conda activate lqd_se
```

**方式 B：venv**
```bash
cd /root/shaohua/SE/SEtrain
python3.9 -m venv venv
source venv/bin/activate
```

### 1.3 安装依赖

```bash
cd /root/shaohua/SE/SEtrain
pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
```

### 1.4 验证

```bash
python -c "import torch, soundfile, pandas; print('OK', torch.__version__)"
```

---

## 2. 数据集下载

工程依赖三类数据，与 `gen_DNS3_datasets.py` 对应：

| 类别 | 来源 | 体积 | 用途 |
|------|------|------|------|
| clean | DNS3 read_speech | ~500GB | 干净语音 |
| noise | DNS3 noise | ~200GB | 噪声 |
| rir | OpenSLR SLR26 + SLR28 | ~5GB | 房间脉冲响应 |

### 2.1 执行下载脚本

```bash
cd /root/shaohua/SE/SEtrain/prepare_datasets
chmod +x download_datasets.sh
./download_datasets.sh
```

### 2.2 选择下载模式

脚本会交互提示：
```
1) 完整 DNS3 (>1TB, 方式A, Azure Blob)
2) 仅 RIR (~5GB, 方式B, OpenSLR)
3) HuggingFace 镜像 (方式C, 国内推荐)
```

**推荐策略：**

| 阶段 | 选项 | 理由 |
|------|------|------|
| 第一次（联调流水线） | **2** | 仅 5GB，国内直连，10~30 分钟完成 |
| 正式训练（国内服务器） | **3** | hf-mirror.com 加速，避免外网超时 |
| 正式训练（海外服务器） | **1** | 微软官方 Azure 源，最权威 |

### 2.3 下载后目录结构

```
prepare_datasets/
├── clean/                # 真实 clean wav（方式 1/3 下载后）
├── noise/                # 真实 noise wav（方式 1/3 下载后）
└── rir/
    ├── SLR26/            # 仿真 RIR（wav 文件已平铺）
    └── SLR28/            # 真实 RIR（wav 文件已平铺，已排除 noise）
```

> **注意**：下载脚本会自动将 zip 包中的 wav 文件平铺到 SLR26/ 和 SLR28/ 目录下，
> 不会产生嵌套子目录问题。SLR28 的 noise 文件会被自动排除。

---

## 3. 生成数据索引

```bash
cd /root/shaohua/SE/SEtrain/prepare_datasets
python generate_csv_files.py
```

输出：
- `train_clean_dir.csv` — clean 文件列表
- `train_noise_dir.csv` — noise 文件列表
- `train_rir_dir.csv` — RIR 文件列表

每个 CSV 仅一列 `file_dir`，记录相对路径（以 `./` 开头）。

> **提示**：该脚本使用 `os.path.abspath(__file__)` 确保路径计算一致，
> 无论从哪个目录运行都能正确生成 CSV。

---

## 4. 校验数据完整性（可选）

```bash
python check_audio_files.py
```

会生成 `*_errors.log`，列出损坏/不可读的 wav。建议大数据集下载后跑一次。

---

## 5. 离线合成训练数据

### 5.1 执行合成

```bash
cd /root/shaohua/SE/SEtrain/prepare_datasets
python gen_DNS3_datasets.py
```

### 5.2 关键参数（在 `gen_DNS3_datasets.py` 的 `__main__` 中）

| 参数 | 默认值 | 含义 |
|------|--------|------|
| `fs` | 16000 | 采样率 |
| `wav_len` | 10 | 每条样本时长（秒） |
| `snr_range` | [-5, 15] | 信噪比范围（dB） |
| `num_tot` | min(50000, 最小数据集大小) | 生成样本数 |
| `save_root` | `./DNS3/` | 输出目录 |
| `flag` | 'train' | 改为 'dev' 可生成验证集 |

### 5.3 输出

```
prepare_datasets/DNS3/
├── train_noisy/         # 训练输入（带混响+噪声）
│   ├── 00001.wav
│   └── ...
├── train_clean/         # 训练目标（去混响 clean）
│   ├── 00001.wav
│   └── ...
└── train_INFO.csv       # 每条样本的 clean/noise/snr 元数据
```

### 5.4 生成验证集

将 `gen_DNS3_datasets.py` 中的 `flag = 'train'` 改为 `flag = 'dev'`，
并准备对应的 `dev_clean_dir.csv` 等，再跑一次。

> **注意**：如果验证集不存在，`dataloader_dns3.py` 会自动回退使用训练集作为验证集，
> 不会导致训练报错。

---

## 6. 启动训练

### 6.1 数据加载器说明

项目使用 `dataloader_dns3.py`（`train.py` 中的导入目标），数据路径自动指向
`prepare_datasets/DNS3/`，无需手动修改硬编码路径。也可通过环境变量覆盖：

```bash
export DNS3_DATA_ROOT=/your/custom/data/path
```

### 6.2 单卡训练

```bash
cd /root/shaohua/SE/SEtrain
python train.py -C configs/cfg_train.yaml -D 0
```

### 6.3 多卡训练（DDP）

```bash
python train.py -C configs/cfg_train.yaml -D 0,1,2,3
```

同时需将 `configs/cfg_train.yaml` 中 `DDP.world_size` 设为对应卡数。

### 6.4 后台运行

```bash
nohup python train.py -C configs/cfg_train.yaml -D 0,1 > train.log 2>&1 &
tail -f train.log
```

### 6.5 训练配置说明（`configs/cfg_train.yaml`）

| 参数 | 快速验证值 | 正式训练值 | 说明 |
|------|-----------|-----------|------|
| `DDP.world_size` | 1 | GPU 数量 | DDP 进程数 |
| `train_dataset.num_data_tot` | 5 | 72000 | 训练总样本数 |
| `train_dataset.num_data_per_epoch` | 5 | 10000 | 每 epoch 采样数 |
| `train_dataloader.batch_size` | 2 | 8 | 批大小 |
| `trainer.epochs` | 3 | 200 | 训练轮数 |
| `trainer.exp_path` | `./exp_gtcrn` | 自定义 | 实验输出路径 |

---

## 7. 推理与评估

### 7.1 修改 `configs/cfg_infer.yaml`

设置训练好的 checkpoint 路径和待推理音频目录。

### 7.2 推理

```bash
python infer.py -C configs/cfg_infer.yaml -D 0
```

### 7.3 评估指标

```bash
# 有参考指标（PESQ / STOI / SI-SDR）
python evaluation/calculate_intrusive_se_metrics.py

# 无参考指标（DNSMOS）—— 需先下载 DNSMOS 模型
python evaluation/calculate_nonintrusive_dnsmos.py
```

DNSMOS 模型从 `https://github.com/microsoft/DNS-Challenge/tree/master/DNSMOS` 下载，
放到 `DNSMOS/DNSMOS/` 目录。

---

## 8. 完整数据正式训练

快速验证流水线通过后，下载完整数据并进行正式训练：

### 8.1 下载完整 clean + noise 数据

```bash
cd /root/shaohua/SE/SEtrain/prepare_datasets
./download_datasets.sh   # 选择 1（海外）或 3（国内 HuggingFace 镜像）
```

### 8.2 重新生成索引并合成

```bash
python generate_csv_files.py
python gen_DNS3_datasets.py
```

### 8.3 恢复正式训练配置

修改 `configs/cfg_train.yaml`：

```yaml
DDP:
  world_size: 4              # 根据 GPU 数量

train_dataset: 
  num_data_tot: 72000
  num_data_per_epoch: 10000

train_dataloader: 
  batch_size: 8
  num_workers: 4

trainer:
  epochs: 200
  exp_path: /data/ssd0/your_path/exp_gtcrn
```

### 8.4 启动正式训练

```bash
nohup python train.py -C configs/cfg_train.yaml -D 0,1,2,3 > train.log 2>&1 &
```

---

## 9. 常见问题 FAQ

### Q1：`conda create` 提示 ToS 未接受
```bash
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
```

### Q2：`pip install pesq` 编译失败
```bash
pip install --upgrade pip wheel setuptools
sudo apt install build-essential python3-dev
```

### Q3：HuggingFace 下载慢
```bash
export HF_ENDPOINT=https://hf-mirror.com
export HF_HUB_ENABLE_HF_TRANSFER=1
```

### Q4：磁盘不足
- DNS3 完整数据 >1TB，至少预留 1.5TB
- 合成 50000 条 10s/16kHz 双通道（noisy+clean）约 ~30GB
- 建议合成输出目录挂在大盘上，可通过修改 `save_root` 重定向

### Q5：训练 OOM
- 降低 `train_dataloader.batch_size`
- 降低 `train_dataset.length_in_seconds`（默认 10 秒）
- 多卡 DDP 切分负载

### Q6：合成时大量 "file not found"
- 跑一次 `check_audio_files.py` 排查
- 检查 CSV 中相对路径与实际目录是否一致
- 注意脚本会跳过 `._xxx` 这类 macOS 隐藏文件

### Q7：训练目标 clean 为什么不是原始 clean？
`gen_DNS3_datasets.py` 中目标是 `clean ⊛ rir[:100ms]`（早期反射），
让模型同时学**降噪 + 去混响**。这是 DNS3 任务的标准设计。

### Q8：`ModuleNotFoundError: No module named 'pkg_resources'`
已通过 `dataloader_dns3.py` 使用 `glob.glob` 替代 `librosa.util.find_files` 解决。
若其他脚本仍有此问题，执行 `pip install setuptools`。

### Q9：CSV 文件没有变化 / RIR 文件扫描不到
`download_datasets.sh` 已修复：解压后将 wav 文件平铺到 `SLR26/` 和 `SLR28/` 目录，
避免 zip 内部嵌套子目录导致扫描不到。重新执行下载脚本即可。

---

## 附：完整一键流程速查

```bash
# 1. 环境
conda create -n lqd_se python=3.9 -y && conda activate lqd_se
cd /root/shaohua/SE/SEtrain
pip install --upgrade pip wheel setuptools
pip install -r requirements.txt

# 2. 下载数据（第一次选 2 快速联调，正式训练选 3）
cd prepare_datasets
chmod +x download_datasets.sh
./download_datasets.sh

# 3. 生成索引 + 校验 + 合成
python generate_csv_files.py
python check_audio_files.py
python gen_DNS3_datasets.py

# 4. 启动训练（dataloader_dns3.py 自动定位数据路径，无需手动修改）
cd ..
python train.py -C configs/cfg_train.yaml -D 0

# 5. 推理 + 评估
vim configs/cfg_infer.yaml     # 设置 checkpoint 和音频路径
python infer.py -C configs/cfg_infer.yaml -D 0
python evaluation/calculate_intrusive_se_metrics.py
```