# Disclaimer
This training and inference pipeline was developed by NVIDIA. It is based on a segmentation model developed by NVIDIA researchers.
# Model Overview
A pre-trained model for volumetric (3D) segmentation of the spleen from CT image.

## Workflow
This model is trained using the UNet architecture [1].

![image](https://lh3.googleusercontent.com/pw/ACtC-3cPu2fsBZRgqX5ZXxekGTGf2UdBWfHDGYYrPVmripLfeQ_aioGYdEHljx37RtK8EAVFkWYuztf47T2icluexhlULsTh0NxneHpd48N75hzsw8fAPdQjluz5Ue6Mj78EcgVrf-QeX0hMp5UIboMaiVQO=w1499-h432-no?authuser=0)

## Training Algorithm
The segmentation of spleen region is formulated as the voxel-wise binary classification. Each voxel is predicted as either foreground (spleen) or background. And the model is optimized with gradient descent method minimizing soft dice loss [2] between the predicted mask and ground truth segmentation. 

## Data
The training data is from the [Medical Decathlon](http://medicaldecathlon.com/).

- Target: Spleen
- Task: Segmentation
- Modality: CT  
- Size: 61 3D volumes (31 Training, 4 Validation, 6 Testing, 20 challenge Test Set)
- Challenge: Large ranging foreground size

The training dataset contains 31 images while the validation and testing datasets contain 4 and 6 images respectively. The challenge test set contains 20 images.

### Data Preparation
The data must be converted to 1mm resolution before training:
``` bash
medl-dataconvert -d ${SOURCE_IMAGE_ROOT} -r 1 -s .nii.gz -e .nii.gz -o ${DESTINATION_IMAGE_ROOT}
```
**NOTE**: To match the default setting, we suggest that ${DESTINATION_IMAGE_ROOT} match DATA_ROOT as defined in environment.json in this MMAR's config folder.

# Training configuration
The training was performed with the following:

- Script: train.sh
- GPU: At least 16GB of GPU memory. 
- Actual Model Input: 96 x 96 x 96
- AMP: True
- Optimizer: Adam
- Learning Rate: 2e-4
- Loss: DiceLoss

## Input
Input: 1 channel CT image with intensity in HU and fixed spacing (1x1x1 mm)

1. Converting to channel first
2. Normalizing to unit std with zero mean
3. Cropping foreground surrounding regions.
4. Cropping random fixed sized regions of size [96,96,96] with the center being a foreground or background voxel at ratio 1 : 1. 
5. Randomly shifting intensity of the volume.

## Output
Output: 2 channels
- Label 0: background
- Label 1: foreground (spleen)

## Inference Details
Inference is performed in a sliding window manner with a specified stride.

# Model Performance
Dice score is used for evaluating the performance of the model. The trained model achieved a dice score of 0.9587 on the testing set.

## Training Performance
A graph showing the training loss over 20000 Steps steps.

![](https://lh3.googleusercontent.com/pw/ACtC-3fl9EHvCGyvjnAkfGyJVaYNLPKDJ8lhfJ5Ib3n9Xp76Fy7_62oiCIkr0d520OGiC9SN4OvoH_Ug90OTCXLKpObNKA9-WSriWALUhU2UhyZfboImTTfGN8_o25uaTqe-karTw3mO1RdfCheN4hd4JFra=w1400-h469-no?authuser=0) <br>

## Validation Performance
A graph showing the validation mean dice over 1260 epochs.

![](https://lh3.googleusercontent.com/pw/ACtC-3fgSyiPribO4Fgwl8L4YPZgbeyKBivB0ncJEcg0JmtR0Yz6V_ekjOrSjIEW03YTZXgtf27p5JH2HOZKmfZyRfVWPVkQ9GSi_Ocqm9lk1TC68tA4MEggnpHmG3PkPqcuevjpoDn8GmuEjllLK0RqtEZq=w1412-h468-no?authuser=0) <br>

# Intended Use
The model needs to be used with NVIDIA hardware and software. For hardware, the model can run on any NVIDIA GPU with memory greater than 16 GB. For software, this model is usable only as part of Transfer Learning &amp; Annotation Tools in Clara Train SDK container.  Find out more about Clara Train at the [Clara Train Collections on NGC](https://ngc.nvidia.com/catalog/collections/nvidia:claratrainframework).

**The Clara pre-trained models are for developmental purposes only and cannot be used directly for clinical procedures.**

# License
[End User License Agreement](https://developer.nvidia.com/clara-train-eula) is included with the product. Licenses are also available along with the model application zip file. By pulling and using the Clara Train SDK container and downloading models, you accept the terms and conditions of these licenses.

# References
[1] Çiçek, Özgün, et al. "3D U-Net: learning dense volumetric segmentation from sparse annotation." International conference on medical image computing and computer-assisted intervention. Springer, Cham, 2016. https://arxiv.org/abs/1606.06650.

[2] Milletari, Fausto, Nassir Navab, and Seyed-Ahmad Ahmadi. "V-net: Fully convolutional neural networks for volumetric medical image segmentation." 2016 fourth international conference on 3D vision (3DV). IEEE, 2016. https://arxiv.org/abs/1606.04797.
