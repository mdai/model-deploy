#!/usr/bin/env bash
set -f

my_dir="$(dirname "$0")"
. "${my_dir}"/set_env.sh

echo "MMAR_ROOT set to $MMAR_ROOT"
if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
  echo "----------------------------------------------------------------"
  echo "./prepare_dataset.sh <SOURCE_DIR> <DEST_DIR> <SPLIT> <ADDITIONAL_OPTIONS>*"
  echo "----------------------------------------------------------------"
  echo "Default <SOURCE_DIR>: $MMAR_ROOT/dataset"
  echo "Default <DEST_DIR>:   $MMAR_ROOT/dataset_0"
  echo "Default <SPLIT>:      0.8"
  echo ""
  echo "Refer Following for ADDITIONAL_OPTIONS:"
  python3 -u -m medl.tools.convert_medical_image -h
  echo "----------------------------------------------------------------"
  echo ""
  exit 0
fi

SRC="${MMAR_ROOT}/dataset"
SOURCE_IMAGE_ROOT="${1:-$SRC}"

DES="${SOURCE_IMAGE_ROOT}_0"
DESTINATION_IMAGE_ROOT="${2:-$DES}"

SPLIT="${3:-0.8}"
additional_options="${*:4}"

echo "++ Using Source Dir: ${SOURCE_IMAGE_ROOT}"
echo "++ Using Destination Dir: ${DESTINATION_IMAGE_ROOT}"
echo "++ Using Train/Validation Split: ${SPLIT}"

echo "Pre-processing raw images..."
rm -rf "${DESTINATION_IMAGE_ROOT}"

if [ ! -f "${SOURCE_IMAGE_ROOT}"/dataset.json ]; then
  python3 -u -m medl.tools.create_dataset_json \
    --input "${SOURCE_IMAGE_ROOT}" \
    --output "${SOURCE_IMAGE_ROOT}/dataset.json" \
    --extensions ".nii,.nii.gz" \
    --split 0
fi

python3 -u -m medl.tools.convert_medical_image \
  -d "${SOURCE_IMAGE_ROOT}" \
  -r 1 \
  -s .nii.gz \
  -e .nii.gz \
  -o "${DESTINATION_IMAGE_ROOT}" \
  -f \
  -a \
  ${additional_options}

echo "Generating ${DESTINATION_IMAGE_ROOT}/dataset_0.json ..."
if [ ! -d "${SOURCE_IMAGE_ROOT}"/validation ] || [ $(find ${SOURCE_IMAGE_ROOT}/validation | wc -l) -eq 1 ]; then
  echo "Validation folder not-exists/empty; Will pick (1 - ${SPLIT}) of training images for validation"
fi

python3 -u -m medl.tools.create_dataset_json \
  --input "${DESTINATION_IMAGE_ROOT}" \
  --output "${DESTINATION_IMAGE_ROOT}/dataset_0.json" \
  --extensions ".nii,.nii.gz" \
  --split "${SPLIT}"
