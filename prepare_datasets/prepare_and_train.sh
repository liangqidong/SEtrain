#!/bin/bash
# =============================================================================
# DNS3 数据解压、链接、生成训练数据 一键脚本
# 适用场景: 已通过选项1下载了 DNS-Challenge 数据（含 wideband + fullband）
# 使用方法: bash prepare_and_train.sh /path/to/DNS-Challenge
# =============================================================================

set -e
set -u

# ---- 配置区 ----
# DNS-Challenge 仓库路径（从命令行参数获取，或使用默认值）
DNS_REPO="${1:-${PWD}/DNS-Challenge}"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

CLEAN_DIR="${SCRIPT_DIR}/clean"
NOISE_DIR="${SCRIPT_DIR}/noise"
RIR_DIR="${SCRIPT_DIR}/rir"

echo "============================================================"
echo "  DNS3 数据准备 + 训练 一键脚本"
echo "============================================================"
echo "  DNS-Challenge 路径: ${DNS_REPO}"
echo "  数据输出路径:       ${SCRIPT_DIR}"
echo "============================================================"

# ---- 检查 DNS-Challenge 目录 ----
if [ ! -d "${DNS_REPO}" ]; then
    echo "[ERROR] 找不到 DNS-Challenge 目录: ${DNS_REPO}"
    echo "用法: bash prepare_and_train.sh /path/to/DNS-Challenge"
    exit 1
fi

# ---- Step 1: 解压 ----
echo ""
echo "==> [Step 1/5] 解压 wideband 数据..."
for f in "${DNS_REPO}"/datasets/*.tar.bz2; do
    if [ -f "$f" ]; then
        echo "    解压: $(basename $f)"
        tar -xjf "$f" -C "${DNS_REPO}/datasets/"
    fi
done

echo "==> [Step 1/5] 解压 fullband 数据..."
for f in "${DNS_REPO}"/datasets_fullband/*.tar.bz2; do
    if [ -f "$f" ]; then
        echo "    解压: $(basename $f)"
        tar -xjf "$f" -C "${DNS_REPO}/datasets_fullband/"
    fi
done

echo "    解压完成!"

# ---- Step 2: 创建目标目录 ----
echo ""
echo "==> [Step 2/5] 创建目标目录..."
mkdir -p "${CLEAN_DIR}" "${NOISE_DIR}" "${RIR_DIR}/SLR26" "${RIR_DIR}/SLR28"

# ---- Step 3: 链接 Wideband 数据 (16kHz, 直接可用) ----
echo ""
echo "==> [Step 3/5] 链接 Wideband 数据 (16kHz)..."

# Clean: read_speech + 其他语种
echo "    链接 clean/read_speech ..."
if [ -d "${DNS_REPO}/datasets/clean/read_speech" ]; then
    find "${DNS_REPO}/datasets/clean/read_speech" -name "*.wav" -exec ln -sf {} "${CLEAN_DIR}/" \;
fi

for subdir in emotional_speech french_data german_speech italian_speech mandarin_speech russian_speech singing_voice spanish_speech; do
    if [ -d "${DNS_REPO}/datasets/clean/${subdir}" ]; then
        echo "    链接 clean/${subdir} ..."
        find "${DNS_REPO}/datasets/clean/${subdir}" -name "*.wav" -exec ln -sf {} "${CLEAN_DIR}/" \;
    fi
done

# Noise
echo "    链接 noise ..."
if [ -d "${DNS_REPO}/datasets/noise" ]; then
    find "${DNS_REPO}/datasets/noise" -name "*.wav" -exec ln -sf {} "${NOISE_DIR}/" \;
fi

# RIR
echo "    链接 impulse_responses ..."
if [ -d "${DNS_REPO}/datasets/impulse_responses/SLR26" ]; then
    find "${DNS_REPO}/datasets/impulse_responses/SLR26" -name "*.wav" -exec ln -sf {} "${RIR_DIR}/SLR26/" \;
fi
if [ -d "${DNS_REPO}/datasets/impulse_responses/SLR28" ]; then
    find "${DNS_REPO}/datasets/impulse_responses/SLR28" -name "*.wav" -exec ln -sf {} "${RIR_DIR}/SLR28/" \;
fi

# ---- Step 4: (可选) 链接 Fullband 数据 (48kHz → 需降采样) ----
echo ""
echo "==> [Step 4/5] 检查 Fullband 数据..."
FULLBAND_DIR="${DNS_REPO}/datasets_fullband"
if [ -d "${FULLBAND_DIR}/clean_fullband" ]; then
    echo "    检测到 Fullband 数据 (48kHz), 需降采样到 16kHz 才能用于训练"
    read -p "    是否将 Fullband 降采样并链接? (y/N): " do_resample
    if [[ "${do_resample}" =~ ^[Yy]$ ]]; then
        # 检查 sox
        if ! command -v sox >/dev/null 2>&1; then
            echo "    [WARN] 未安装 sox, 尝试安装..."
            apt-get install -y sox 2>/dev/null || yum install -y sox 2>/dev/null || {
                echo "    [ERROR] 无法安装 sox, 跳过 Fullband 降采样"
                do_resample="n"
            }
        fi
        if [[ "${do_resample}" =~ ^[Yy]$ ]]; then
            echo "    降采样 Fullband clean (这会花费较长时间)..."
            RESAMPLE_DIR="${SCRIPT_DIR}/clean_fullband_16k"
            mkdir -p "${RESAMPLE_DIR}"
            find "${FULLBAND_DIR}/clean_fullband" -name "*.wav" | while read f; do
                out_name="$(basename "${f}" .wav)_16k.wav"
                sox "$f" -r 16000 "${RESAMPLE_DIR}/${out_name}" 2>/dev/null
            done
            ln -sf "${RESAMPLE_DIR}"/*.wav "${CLEAN_DIR}/"
            echo "    Fullband clean 降采样完成!"

            echo "    降采样 Fullband noise..."
            RESAMPLE_NOISE_DIR="${SCRIPT_DIR}/noise_fullband_16k"
            mkdir -p "${RESAMPLE_NOISE_DIR}"
            find "${FULLBAND_DIR}/noise_fullband" -name "*.wav" | while read f; do
                out_name="$(basename "${f}" .wav)_16k.wav"
                sox "$f" -r 16000 "${RESAMPLE_NOISE_DIR}/${out_name}" 2>/dev/null
            done
            ln -sf "${RESAMPLE_NOISE_DIR}"/*.wav "${NOISE_DIR}/"
            echo "    Fullband noise 降采样完成!"
        fi
    fi
else
    echo "    未检测到 Fullband 数据, 跳过"
fi

# ---- 统计 ----
echo ""
echo "==> [Step 5/5] 数据统计:"
CLEAN_COUNT=$(find "${CLEAN_DIR}" -name "*.wav" | wc -l)
NOISE_COUNT=$(find "${NOISE_DIR}" -name "*.wav" | wc -l)
RIR_COUNT=$(find "${RIR_DIR}" -name "*.wav" | wc -l)
echo "    Clean: ${CLEAN_COUNT} files"
echo "    Noise: ${NOISE_COUNT} files"
echo "    RIR:   ${RIR_COUNT} files"

if [ "${CLEAN_COUNT}" -eq 0 ] || [ "${NOISE_COUNT}" -eq 0 ] || [ "${RIR_COUNT}" -eq 0 ]; then
    echo ""
    echo "[ERROR] 数据不完整! 请检查 DNS-Challenge 目录和解压结果"
    exit 1
fi

# ---- 生成 CSV 和训练数据 ----
echo ""
echo "============================================================"
echo "  数据链接完成, 接下来生成训练数据"
echo "============================================================"

echo ""
echo "==> 生成 CSV 索引..."
cd "${SCRIPT_DIR}"
python generate_csv_files.py

echo ""
echo "==> 合成训练数据 (noisy + clean 对)..."
python gen_DNS3_datasets.py

echo ""
echo "============================================================"
echo "  全部完成! 启动4卡DDP训练:"
echo "  cd /path/to/SEtrain"
echo "  torchrun --nproc_per_node=4 train.py -c configs/cfg_train.yaml"
echo "============================================================"

# ---- 可选: 清理压缩包 ----
echo ""
read -p "是否删除已解压的 .tar.bz2 压缩包以节省空间? (y/N): " do_cleanup
if [[ "${do_cleanup}" =~ ^[Yy]$ ]]; then
    echo "    删除 wideband 压缩包..."
    find "${DNS_REPO}/datasets" -name "*.tar.bz2" -delete 2>/dev/null || true
    echo "    删除 fullband 压缩包..."
    find "${DNS_REPO}/datasets_fullband" -name "*.tar.bz2" -delete 2>/dev/null || true
    echo "    清理完成!"
fi