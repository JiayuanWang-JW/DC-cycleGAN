## DC-cycleGAN: Bidirectional CT-to-MR Synthesis from Unpaired Data
> [**DC-cycleGAN: Bidirectional CT-to-MR Synthesis from Unpaired Data**](https://arxiv.org/abs/2211.01293)

---

# DC-CycleGAN


## Installation
Please use Python 3.6
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
```
Please follows "test_image.ipynb" annotation to run, you should change the path to yours.
When you test your model meet the problem about "alueError: Dimension 0 in both shapes must be equal, but are 3 and 128. Shapes are [3,3,128,64] and [128,64,3,3]."
Please check the training code and test code setting for opt['use_resize_convolution'], they should be kept the same and then will work. 
```

Then use "evaluate.ipynb" to calculate MAE, PSNR, and SSIM.

## Note
I am really thanks for your interest in my work, if you have any problem with the code, please contact me or submit an issue, and I will reply to you if I can help you. 

## Citation:
If you use this code for your research, please give us a star and cite our paper:
> @article{wang2023dc,
> <br>  title={DC-cycleGAN: Bidirectional CT-to-MR synthesis from unpaired data},
> <br>  author={Wang, Jiayuan and Wu, QM Jonathan and Pourpanah, Farhad},
> <br>  journal={Computerized Medical Imaging and Graphics},
> <br>  pages={102249},
> <br>  year={2023},
> <br>  publisher={Elsevier}
}

