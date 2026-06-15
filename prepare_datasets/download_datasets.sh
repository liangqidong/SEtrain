#!/bin/bash
# =============================================================================
# DNS3 (DNS Challenge 3 / INTERSPEECH 2021) 数据集下载脚本
# Linux 运行路径示例: /root/shaohua/SE/SEtrain/prepare_datasets
# =============================================================================
# 数据集组成 (与 gen_DNS3_datasets.py 对应):
#   1) clean/  -> DNS3 clean speech (read_speech)
#   2) noise/  -> DNS3 noise
#   3) rir/    -> RIR (SLR26 + SLR28, openslr 镜像)
#
# 注意:
#   - DNS3 完整数据约 ~1TB,建议挑选 read_speech + noise 子集 (~200GB)
#   - 全量下载耗时长,请根据需要在下方注释/取消注释相应模块
# =============================================================================

set -e   # 出错立即止
set -u   # 未定义变量报错

# ---- 配置区 ----
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DATA_ROOT="${SCRIPT_DIR}"
CLEAN_DIR="${DATA_ROOT}/clean"
NOISE_DIR="${DATA_ROOT}/noise"
RIR_DIR="${DATA_ROOT}/rir"

mkdir -p "${CLEAN_DIR}" "${NOISE_DIR}" "${RIR_DIR}/SLR26" "${RIR_DIR}/SLR28"

echo "==> 数据目录: ${DATA_ROOT}"

# ---- 工具检查 ----
need_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "[ERROR] 需要安装命令: $1"
        exit 1
    fi
}
need_cmd wget
need_cmd tar
# git lfs 可选 (HuggingFace 镜像方式才用到)

# =============================================================================
# 方式 A (推荐): 通过 DNS Challenge 官方仓库脚本下载 (Azure Blob)
# 仓库: https://github.com/microsoft/DNS-Challenge (interspeech2021 分支)
# 仓库里 download-dns-challenge-3.sh 列出了所有 BLOB_NAMES 链接
# =============================================================================
download_dns3_official() {
    echo "==> [方式A] 从 microsoft/DNS-Challenge (interspeech2021 分支) 拉取下载列表"
    REPO_DIR="${DATA_ROOT}/DNS-Challenge"
    if [ ! -d "${REPO_DIR}" ]; then
        git clone --depth=1 --branch interspeech2021 \
            https://github.com/microsoft/DNS-Challenge.git "${REPO_DIR}"
    fi

    # 官方下载脚本会下载所有 tar.bz2 分片到当前目录
    echo "==> 执行官方下载脚本 (默认下载完整数据,可能 >1TB,请确认磁盘空间)"
    cd "${REPO_DIR}"
    bash download-dns-challenge-3.sh
    cd "${DATA_ROOT}"

    # 解压后会得到 datasets/clean/read_speech, datasets/noise, datasets/impulse_responses
    echo "==> 合并文件到 clean/noise/rir 目录"
    if [ -d "${REPO_DIR}/datasets/clean/read_speech" ]; then
        find "${REPO_DIR}/datasets/clean/read_speech" -name "*.wav" -exec ln -sf {} "${CLEAN_DIR}/" \;
    fi
    if [ -d "${REPO_DIR}/datasets/noise" ]; then
        find "${REPO_DIR}/datasets/noise" -name "*.wav" -exec ln -sf {} "${NOISE_DIR}/" \;
    fi
    if [ -d "${REPO_DIR}/datasets/impulse_responses/SLR26" ]; then
        find "${REPO_DIR}/datasets/impulse_responses/SLR26" -name "*.wav" -exec ln -sf {} "${RIR_DIR}/SLR26/" \;
    fi
    if [ -d "${REPO_DIR}/datasets/impulse_responses/SLR28" ]; then
        find "${REPO_DIR}/datasets/impulse_responses/SLR28" -name "*.wav" -exec ln -sf {} "${RIR_DIR}/SLR28/" \;
    fi
}

# =============================================================================
# 方式 B: 仅下载 RIR (SLR26 / SLR28),用于本地小规模联调
# OpenSLR 提供 HTTP 直链,体量 ~5GB,适合先打通流水线
# =============================================================================
download_rir_only() {
    echo "==> [方式B] 仅下载 RIR 子集 (SLR26 + SLR28)"

    # SLR26: simulated RIRs (~171MB for 16k version)
    if [ ! -f "${RIR_DIR}/SLR26.zip" ]; then
        wget -c -O "${RIR_DIR}/SLR26.zip" \
            https://www.openslr.org/resources/26/sim_rir_16k.zip
    fi
    # 解压到临时目录，避免嵌套子目录问题
    SLR26_TMP="${RIR_DIR}/SLR26_tmp"
    rm -rf "${SLR26_TMP}"
    mkdir -p "${SLR26_TMP}"
    unzip -o "${RIR_DIR}/SLR26.zip" -d "${SLR26_TMP}/"
    # 将解压出的 wav 文件平铺到 SLR26/ 目录下
    # OpenSLR SLR26 zip 内部结构: sim_rir_16k/Room*/*.wav
    mkdir -p "${RIR_DIR}/SLR26"
    find "${SLR26_TMP}" -name "*.wav" -exec mv {} "${RIR_DIR}/SLR26/" \;
    rm -rf "${SLR26_TMP}"
    echo "==> SLR26 wav files count: $(find "${RIR_DIR}/SLR26" -name '*.wav' | wc -l)"

    # SLR28: real RIRs (~1.2GB)
    if [ ! -f "${RIR_DIR}/SLR28.zip" ]; then
        wget -c -O "${RIR_DIR}/SLR28.zip" \
            https://www.openslr.org/resources/28/rirs_noises.zip
    fi
    # 解压到临时目录，只提取 RIR 文件（排除 noise 文件）
    SLR28_TMP="${RIR_DIR}/SLR28_tmp"
    rm -rf "${SLR28_TMP}"
    mkdir -p "${SLR28_TMP}"
    unzip -o "${RIR_DIR}/SLR28.zip" -d "${SLR28_TMP}/"
    # 将解压出的 RIR wav 文件平铺到 SLR28/ 目录下
    # OpenSLR SLR28 zip 内部结构: RIRS_NOISES/ (包含 RIR 和 noise)
    # 只提取 RIR 相关文件，排除 noise 和 pointsource_noise
    mkdir -p "${RIR_DIR}/SLR28"
    find "${SLR28_TMP}" -name "*.wav" ! -path "*/noise*" ! -path "*/pointsource*" -exec mv {} "${RIR_DIR}/SLR28/" \;
    rm -rf "${SLR28_TMP}"
    echo "==> SLR28 wav files count: $(find "${RIR_DIR}/SLR28" -name '*.wav' | wc -l)"
}

# =============================================================================
# 方式 C: HuggingFace 镜像 (国内推荐, 不需 VPN)
# 数据集: ChrisIsKing/DNS-challenge / pyf98/DNS3 等社区镜像
# =============================================================================
download_via_huggingface() {
    echo "==> [方式C] 通过 HuggingFace 镜像下载"
    need_cmd python
    pip install -q "huggingface_hub[cli]" hf_transfer
    export HF_HUB_ENABLE_HF_TRANSFER=1
    # 国内镜像加速 (可选)
    export HF_ENDPOINT=https://hf-mirror.com

    # 示例: 下载某个社区维护的 DNS3 子集
    # huggingface-cli download <repo_id> --repo-type dataset \
    #     --local-dir "${DATA_ROOT}/DNS3_hf" --local-dir-use-symlinks False

    echo "请编辑脚本填入实际 HF repo_id 后再运行"
}

# =============================================================================
# 主流程: 默认仅下载 RIR (轻量, 打通流水线), 其余按需启用
# =============================================================================
echo ""
echo "请选择下载模式:"
echo "  1) 完整 DNS3 (>1TB, 方式A)"
echo "  2) 仅 RIR (~5GB, 方式B, 用于快速联调)"
echo "  3) HuggingFace 镜像 (方式C, 需自行填写 repo_id)"
read -p "输入选项 [1/2/3] (默认 2): " choice
choice=${choice:-2}

case "${choice}" in
    1) download_dns3_official ;;
    2) download_rir_only ;;
    3) download_via_huggingface ;;
    *) echo "无效选项"; exit 1 ;;
esac

echo ""
echo "==> 下载完成!"
echo "==> 接下来执行:"
echo "    cd ${SCRIPT_DIR}"
echo "    python generate_csv_files.py    # 生成 CSV 索引"
echo "    python check_audio_files.py     # (可选) 校验文件可读性"
echo "    python gen_DNS3_datasets.py     # 合成训练对 (noisy + clean)"