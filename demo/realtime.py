# Copyright (c) Facebook, Inc. and its affiliates.
# Modified by Bowen Cheng from: https://github.com/facebookresearch/detectron2/blob/master/demo/demo.py
import argparse
import glob
import multiprocessing as mp
import os

# fmt: off
import sys
sys.path.insert(1, os.path.join(sys.path[0], '..'))
# fmt: on
# import register_cs
import tempfile
import time
import warnings
from sys import platform
if platform == 'win32':
    import cv2
import numpy as np
import tqdm
import mss

from detectron2.config import get_cfg
from detectron2.data.detection_utils import read_image
from detectron2.projects.deeplab import add_deeplab_config
from detectron2.utils.logger import setup_logger

from mask_former import add_mask_former_config
from predictor import VisualizationDemo
from custom_model import CustomModel
#python demo\demo.py --config-file 'C:\Users\Kai Ji\Desktop\Maskformer\MaskFormer\configs\myconfig.yaml' --input 'C:\Users\Kai Ji\Desktop\Maskformer\MaskFormer\datasets\cs\test\images\36.jpg' --opts MODEL.WEIGHTS output\model_final.pth
# constants
WINDOW_NAME = "MaskFormer demo"
custom = CustomModel()

def setup_cfg(args):
    # load config from file and command-line arguments
    cfg = get_cfg()
    add_deeplab_config(cfg)
    add_mask_former_config(cfg)
    cfg.merge_from_file(args.config_file)
    cfg.merge_from_list(args.opts)
    cfg.freeze()
    return cfg


def get_parser():
    parser = argparse.ArgumentParser(description="Detectron2 demo for builtin configs")
    parser.add_argument(
        "--config-file",
        default="configs/ade20k-150/maskformer_R50_bs16_160k.yaml",
        metavar="FILE",
        help="path to config file",
    )
    parser.add_argument("--webcam", action="store_true", help="Take inputs from webcam.")
    parser.add_argument("--video-input", help="Path to video file.")
    parser.add_argument(
        "--input",
        nargs="+",
        help="A list of space separated input images; "
        "or a single glob pattern such as 'directory/*.jpg'",
    )
    parser.add_argument(
        "--output",
        help="A file or directory to save output visualizations. "
        "If not given, will show output in an OpenCV window.",
    )

    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.5,
        help="Minimum score for instance predictions to be shown",
    )
    parser.add_argument(
        "--opts",
        help="Modify config options using the command-line 'KEY VALUE' pairs",
        default=[],
        nargs=argparse.REMAINDER,
    )
    return parser


def test_opencv_video_format(codec, file_ext):
    with tempfile.TemporaryDirectory(prefix="video_format_test") as dir:
        filename = os.path.join(dir, "test_file" + file_ext)
        writer = cv2.VideoWriter(
            filename=filename,
            fourcc=cv2.VideoWriter_fourcc(*codec),
            fps=float(30),
            frameSize=(10, 10),
            isColor=True,
        )
        [writer.write(np.zeros((10, 10, 3), np.uint8)) for _ in range(30)]
        writer.release()
        if os.path.isfile(filename):
            return True
        return False


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    args = get_parser().parse_args()
    setup_logger(name="fvcore")
    logger = setup_logger()
    logger.info("Arguments: " + str(args))

    cfg = setup_cfg(args)
    cfg.defrost()
    cfg.MODEL.DEVICE = 'cpu'
    demo = VisualizationDemo(cfg)
    
    offset = 30
    times = []
    sct = mss.mss()
        
    top = 30
    left = 0
    width =640
    height =480
    autoaim = False


    if args.input:
        # if len(args.input) == 1:

        while True:
            # print("hello")
            img = np.array(sct.grab({"top": top, "left": left, "width": width, "height": height}))
            # if True:
            #     custom.detectImg(img)
            # else:
                # cx,cy = getCenter(left, top, left + width, top + height)
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            # args.input = glob.glob(os.path.expanduser(args.input[0]))
            # assert args.input, "The input path(s) was not found"
            # for path in tqdm.tqdm(args.input, disable=not args.output):
            #     # use PIL, to be consistent with evaluation
            # img = read_image(path, format="BGR")

            
            start = time.perf_counter()
            predictions, visualized_output = demo.run_on_image(img)
            end = time.perf_counter()
            print("inference time",  end - start)
            # logger.info(
            #     "{}: {} in {:.2f}s".format(
            #         path,
            #         "detected {} instances".format(len(predictions["instances"]))
            #         if "instances" in predictions
            #         else "finished",
            #         time.time() - start_time,
            #     )
            # )
            # cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
            vis =visualized_output.get_image()[:, :, ::-1]
            # print("hello")
            cv2.imshow('WINDOW_NAME',vis)
            # if cv2.waitKey(25) & 0xFF == ord("p"):
            #     cv2.destroyAllWindows()
            #     break

            cv2.waitKey(1)
                # time.sleep(1)
                # cv2.destroyAllWindows()

                # if cv2.waitKey(0) == 27:
                #     break  # esc to quit
                # cv2.waitKey(1)

                # if args.output:
                #     if os.path.isdir(args.output):
                #         assert os.path.isdir(args.output), args.output
                #         out_filename = os.path.join(args.output, os.path.basename(path))
                #     else:
                #         assert len(args.input) == 1, "Please specify a directory with args.output"
                #         out_filename = args.output
                #     visualized_output.save(out_filename)
                # else:
                
        # elif args.webcam:
        #     assert args.input is None, "Cannot have both --input and --webcam!"
        #     assert args.output is None, "output not yet supported with --webcam!"
        #     cam = cv2.VideoCapture(0)
        #     for vis in tqdm.tqdm(demo.run_on_video(cam)):
        #         cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
        #         cv2.imshow(WINDOW_NAME, vis)
        #         if cv2.waitKey(1) == 27:
        #             break  # esc to quit
        #     cam.release()
        #     cv2.destroyAllWindows()
        # elif args.video_input:
        #     video = cv2.VideoCapture(args.video_input)
        #     width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
        #     height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        #     frames_per_second = video.get(cv2.CAP_PROP_FPS)
        #     num_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        #     basename = os.path.basename(args.video_input)
        #     codec, file_ext = (
        #         ("x264", ".mkv") if test_opencv_video_format("x264", ".mkv") else ("mp4v", ".mp4")
        #     )
        #     if codec == ".mp4v":
        #         warnings.warn("x264 codec not available, switching to mp4v")
        #     if args.output:
        #         if os.path.isdir(args.output):
        #             output_fname = os.path.join(args.output, basename)
        #             output_fname = os.path.splitext(output_fname)[0] + file_ext
        #         else:
        #             output_fname = args.output
        #         assert not os.path.isfile(output_fname), output_fname
        #         output_file = cv2.VideoWriter(
        #             filename=output_fname,
        #             # some installation of opencv may not support x264 (due to its license),
        #             # you can try other format (e.g. MPEG)
        #             fourcc=cv2.VideoWriter_fourcc(*codec),
        #             fps=float(frames_per_second),
        #             frameSize=(width, height),
        #             isColor=True,
        #         )
        #     assert os.path.isfile(args.video_input)
        #     for vis_frame in tqdm.tqdm(demo.run_on_video(video), total=num_frames):
        #         if args.output:
        #             output_file.write(vis_frame)
        #         else:
        #             cv2.namedWindow(basename, cv2.WINDOW_NORMAL)
        #             cv2.imshow(basename, vis_frame)
        #             if cv2.waitKey(1) == 27:
        #                 break  # esc to quit
        #     video.release()
        #     if args.output:
        #         output_file.release()
        #     else:
        #         cv2.destroyAllWindows()