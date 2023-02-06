# Copyright (c) Facebook, Inc. and its affiliates.
# Copied from: https://github.com/facebookresearch/detectron2/blob/master/demo/predictor.py
import atexit
import bisect
import multiprocessing as mp
from collections import deque
import time

import torch

from detectron2.data import MetadataCatalog
from detectron2.engine.defaults import DefaultPredictor
from detectron2.utils.video_visualizer import VideoVisualizer
from detectron2.utils.visualizer import ColorMode, Visualizer, _PanopticPrediction, _create_text_labels
import numpy as np

_OFF_WHITE = (1.0, 1.0, 240.0 / 255)
class PersonVisualizer(Visualizer):
    
    def draw_panoptic_seg(self, panoptic_seg, segments_info, area_threshold=None, alpha=0.7):
        """
        Draw panoptic prediction annotations or results.

        Args:
            panoptic_seg (Tensor): of shape (height, width) where the values are ids for each
                segment.
            segments_info (list[dict] or None): Describe each segment in `panoptic_seg`.
                If it is a ``list[dict]``, each dict contains keys "id", "category_id".
                If None, category id of each pixel is computed by
                ``pixel // metadata.label_divisor``.
            area_threshold (int): stuff segments with less than `area_threshold` are not drawn.

        Returns:
            output (VisImage): image object with visualizations.
        """
        
   
    

       
        pred = _PanopticPrediction(panoptic_seg, segments_info, self.metadata)
       
        
        if self._instance_mode == ColorMode.IMAGE_BW:
            self.output.reset_image(self._create_grayscale_image(pred.non_empty_mask()))
     
        # # draw mask for all semantic segments first i.e. "stuff"
        # for mask, sinfo in pred.semantic_masks():
        #     print("sinfo",sinfo)
        #     if sinfo['category_id'] != 12:
        #         continue
        #     category_idx = sinfo["category_id"]
        #     sinfo = [x for x in sinfo if x["category_id"] == 12]
        #     print(sinfo)
        #     try:
        #         mask_color = [x / 255 for x in self.metadata.stuff_colors[category_idx]]
        #     except AttributeError:
        #         mask_color = None

            # text = self.metadata.stuff_classes[category_idx]
            # # print(text, "is", category_idx)
            # self.draw_binary_mask(
            #     mask,
            #     color=mask_color,
            #     edge_color=_OFF_WHITE,
            #     text=text,
            #     alpha=alpha,
            #     area_threshold=area_threshold,
            # )

        # draw mask for all instances second
        all_instances = list(pred.instance_masks())
        if len(all_instances) == 0:
            return self.output
        m, s = list(zip(*all_instances))
        sinfo= []
        masks = []
        # print("panoptic m", m)
        # print("s", s)
        for x,y in zip(m,s):
            if y["category_id"] == 12:
                masks.append(x)
                sinfo.append(y)
        # print(masks)
        # print(sinfo)
        category_ids = [x["category_id"] for x in sinfo]
        try:
            scores = [x["score"] for x in sinfo]
        except KeyError:
            scores = None
        labels = _create_text_labels(
            category_ids, scores, self.metadata.thing_classes, [x.get("iscrowd", 0) for x in sinfo]
        )
        # print(labels)

        try:
            colors = [
                self._jitter([x / 255 for x in self.metadata.thing_colors[c]]) for c in category_ids
            ]
        except AttributeError:
            colors = None
        
        self.overlay_instances(masks=masks, labels=labels, assigned_colors=colors, alpha=alpha)

        return self.output
    
    
    
    draw_panoptic_seg_predictions = draw_panoptic_seg
    
    def draw_sem_seg(self, sem_seg, area_threshold=None, alpha=0.8):
        """
        Draw semantic segmentation predictions/labels.

        Args:
            sem_seg (Tensor or ndarray): the segmentation of shape (H, W).
                Each value is the integer label of the pixel.
            area_threshold (int): segments with less than `area_threshold` are not drawn.
            alpha (float): the larger it is, the more opaque the segmentations are.

        Returns:
            output (VisImage): image object with visualizations.
        """
        if isinstance(sem_seg, torch.Tensor):
            sem_seg = sem_seg.numpy()
        labels, areas = np.unique(sem_seg, return_counts=True)

        sorted_idxs = np.argsort(-areas).tolist()
        labels = labels[sorted_idxs]
        # print("labels", labels)
   
        for label in filter(lambda l: l < len(self.metadata.stuff_classes), labels):
            if label != 12:
                continue
            try:
                mask_color = [x / 255 for x in self.metadata.stuff_colors[label]]
            except (AttributeError, IndexError):
                mask_color = None

            binary_mask = (sem_seg == label).astype(np.uint8)
            print(np.unique(binary_mask))
            text = self.metadata.stuff_classes[label]
            self.draw_binary_mask(
                binary_mask,
                color=mask_color,
                edge_color=_OFF_WHITE,
                text=text,
                alpha=alpha,
                area_threshold=area_threshold,
            )
        return self.output

from sys import platform
if platform =="win32":
    import cv2
class VisualizationDemo(object):
    def __init__(self, cfg, instance_mode=ColorMode.IMAGE, parallel=False):
        """
        Args:
            cfg (CfgNode):
            instance_mode (ColorMode):
            parallel (bool): whether to run the model in different processes from visualization.
                Useful since the visualization logic can be slow.
        """
        self.metadata = MetadataCatalog.get(
            cfg.DATASETS.TEST[0] if len(cfg.DATASETS.TEST) else "__unused"
        )
        self.cpu_device = torch.device("cpu")
        self.instance_mode = instance_mode

        self.parallel = parallel
        if parallel:
            num_gpu = torch.cuda.device_count()
            self.predictor = AsyncPredictor(cfg, num_gpus=num_gpu)
        else:
            self.predictor = DefaultPredictor(cfg)

    def run_on_image(self, image):
        """
        Args:
            image (np.ndarray): an image of shape (H, W, C) (in BGR order).
                This is the format used by OpenCV.
        Returns:
            predictions (dict): the output of the model.
            vis_output (VisImage): the visualized image output.
        """

        # if platform != 'win32':
        #     from google.colab.patches import cv2_imshow
            
        #     vis_output = None
        #     predictions = self.predictor(image)
        #     # Convert image from OpenCV BGR format to Matplotlib RGB format.
        #     image = image[:, :, ::-1]
        #     visualizer = Visualizer(image, self.metadata, instance_mode=self.instance_mode)
        #     # if "panoptic_seg" in predictions:
        #     #     panoptic_seg, segments_info = predictions["panoptic_seg"]
        #     #     vis_output = visualizer.draw_panoptic_seg_predictions(
        #     #         panoptic_seg.to(self.cpu_device), segments_info
        #     #     )
        #     # else:
        #     if "sem_seg" in predictions:
        #         print(predictions['sem_seg'].shape)
        #         pred = predictions["sem_seg"].argmax(dim=0).to(self.cpu_device)
        #         print(pred.shape)

        #     cv2_imshow(pred)
        #     return 
     

        vis_output = None

        t1 = time.perf_counter()
        predictions = self.predictor(image)
        t2 = time.perf_counter()
        elapsed_time = t2 - t1

            # Print the elapsed time
        
        # print(f"Inference took {elapsed_time:.10f} seconds")
        # Convert image from OpenCV BGR format to Matplotlib RGB format.
        image = image[:, :, ::-1]
        visualizer = PersonVisualizer(image, self.metadata, instance_mode=self.instance_mode) # if you want to visualize only person
        # visualizer = Visualizer(image, self.metadata, instance_mode=self.instance_mode) # if you want to visualize everything
        # print("predictions",predictions)
        if "panoptic_seg" in predictions:
            # print("panoptic segmentation")
            panoptic_seg, segments_info = predictions["panoptic_seg"]
            vis_output = visualizer.draw_panoptic_seg_predictions(
                panoptic_seg.to(self.cpu_device), segments_info
            )
        else:
            if "sem_seg" in predictions:
                # print("semantic segmenation")
                vis_output = visualizer.draw_sem_seg(
                    predictions["sem_seg"].argmax(dim=0).to(self.cpu_device)
                )
            if "instances" in predictions:
                instances = predictions["instances"].to(self.cpu_device)
                # print("instances ",instances)
                vis_output = visualizer.draw_instance_predictions(predictions=instances)

        return predictions, vis_output

    def _frame_from_video(self, video):
        while video.isOpened():
            success, frame = video.read()
            if success:
                yield frame
            else:
                break

    def run_on_video(self, video):
        """
        Visualizes predictions on frames of the input video.
        Args:
            video (cv2.VideoCapture): a :class:`VideoCapture` object, whose source can be
                either a webcam or a video file.
        Yields:
            ndarray: BGR visualizations of each video frame.
        """
        video_visualizer = VideoVisualizer(self.metadata, self.instance_mode)

        def process_predictions(frame, predictions):
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            if "panoptic_seg" in predictions:
                panoptic_seg, segments_info = predictions["panoptic_seg"]
                vis_frame = video_visualizer.draw_panoptic_seg_predictions(
                    frame, panoptic_seg.to(self.cpu_device), segments_info
                )
            elif "instances" in predictions:
                predictions = predictions["instances"].to(self.cpu_device)
                vis_frame = video_visualizer.draw_instance_predictions(frame, predictions)
            elif "sem_seg" in predictions:
                vis_frame = video_visualizer.draw_sem_seg(
                    frame, predictions["sem_seg"].argmax(dim=0).to(self.cpu_device)
                )

            # Converts Matplotlib RGB format to OpenCV BGR format
            vis_frame = cv2.cvtColor(vis_frame.get_image(), cv2.COLOR_RGB2BGR)
            return vis_frame

        frame_gen = self._frame_from_video(video)
        if self.parallel:
            buffer_size = self.predictor.default_buffer_size

            frame_data = deque()

            for cnt, frame in enumerate(frame_gen):
                frame_data.append(frame)
                self.predictor.put(frame)

                if cnt >= buffer_size:
                    frame = frame_data.popleft()
                    predictions = self.predictor.get()
                    yield process_predictions(frame, predictions)

            while len(frame_data):
                frame = frame_data.popleft()
                predictions = self.predictor.get()
                yield process_predictions(frame, predictions)
        else:
            for frame in frame_gen:
                yield process_predictions(frame, self.predictor(frame))


class AsyncPredictor:
    """
    A predictor that runs the model asynchronously, possibly on >1 GPUs.
    Because rendering the visualization takes considerably amount of time,
    this helps improve throughput a little bit when rendering videos.
    """

    class _StopToken:
        pass

    class _PredictWorker(mp.Process):
        def __init__(self, cfg, task_queue, result_queue):
            self.cfg = cfg
            self.task_queue = task_queue
            self.result_queue = result_queue
            super().__init__()

        def run(self):
            predictor = DefaultPredictor(self.cfg)

            while True:
                task = self.task_queue.get()
                if isinstance(task, AsyncPredictor._StopToken):
                    break
                idx, data = task
                result = predictor(data)
                self.result_queue.put((idx, result))

    def __init__(self, cfg, num_gpus: int = 1):
        """
        Args:
            cfg (CfgNode):
            num_gpus (int): if 0, will run on CPU
        """
        num_workers = max(num_gpus, 1)
        self.task_queue = mp.Queue(maxsize=num_workers * 3)
        self.result_queue = mp.Queue(maxsize=num_workers * 3)
        self.procs = []
        for gpuid in range(max(num_gpus, 1)):
            cfg = cfg.clone()
            cfg.defrost()
            cfg.MODEL.DEVICE = "cuda:{}".format(gpuid) if num_gpus > 0 else "cpu"
            self.procs.append(
                AsyncPredictor._PredictWorker(cfg, self.task_queue, self.result_queue)
            )

        self.put_idx = 0
        self.get_idx = 0
        self.result_rank = []
        self.result_data = []

        for p in self.procs:
            p.start()
        atexit.register(self.shutdown)

    def put(self, image):
        self.put_idx += 1
        self.task_queue.put((self.put_idx, image))

    def get(self):
        self.get_idx += 1  # the index needed for this request
        if len(self.result_rank) and self.result_rank[0] == self.get_idx:
            res = self.result_data[0]
            del self.result_data[0], self.result_rank[0]
            return res

        while True:
            # make sure the results are returned in the correct order
            idx, res = self.result_queue.get()
            if idx == self.get_idx:
                return res
            insert = bisect.bisect(self.result_rank, idx)
            self.result_rank.insert(insert, idx)
            self.result_data.insert(insert, res)

    def __len__(self):
        return self.put_idx - self.get_idx

    def __call__(self, image):
        self.put(image)
        return self.get()

    def shutdown(self):
        for _ in self.procs:
            self.task_queue.put(AsyncPredictor._StopToken())

    @property
    def default_buffer_size(self):
        return len(self.procs) * 5
