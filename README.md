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
> @article{wang2022dc,
> <br>  title={DC-cycleGAN: Bidirectional CT-to-MR Synthesis from Unpaired Data},
> <br>  author={Wang, Jiayuan and Wu, QM and Pourpanah, Farhad},
> <br>  journal={arXiv preprint arXiv:2211.01293},
> <br>  year={2022}
> <br>}

## Reference
The tensorflow implementation of CycleGAN: 
