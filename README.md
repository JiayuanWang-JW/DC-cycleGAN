## DC-cycleGAN: Bidirectional CT-to-MR Synthesis from Unpaired Data
> [**DC-cycleGAN: Bidirectional CT-to-MR Synthesis from Unpaired Data**](https://arxiv.org/abs/2211.01293)

---

# DC-CycleGAN


## Installation
```
pip3 install -r requirements.txt
```

## Usage
Train:
```
python DC-CycleGAN.py --lambdaG=5 --date='time1' --dataset='100dataset'
```
You can change "--date" to any name you want. We use time1 because we train each method five times. Then calculate the average as the final quantitative result.


Test:

Please follows "test_image.ipynb" annotation to run, you should change the path to yours.

Then use "evaluate.ipynb" to calculate MAE, PSNR, and SSIM.

## Citation:
If you use this code for your research, please cite our paper:
@article{wang2022dc,
  title={DC-cycleGAN: Bidirectional CT-to-MR Synthesis from Unpaired Data},
  author={Wang, Jiayuan and Wu, QM and Pourpanah, Farhad},
  journal={arXiv preprint arXiv:2211.01293},
  year={2022}
}
