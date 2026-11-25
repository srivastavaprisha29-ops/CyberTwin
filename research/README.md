# Offline media detector evaluation

FaceForensics++ evaluates facial manipulation detectors under compression. DeepfakeBench standardizes detector inputs and evaluation. CyberTwin uses those ideas to compare clip-level error rates across datasets and compression conditions.

- [FaceForensics++ (ICCV 2019)](https://openaccess.thecvf.com/content_ICCV_2019/html/Rossler_FaceForensics_Learning_to_Detect_Manipulated_Facial_Images_ICCV_2019_paper.html)
- [DeepfakeBench (NeurIPS 2023)](https://proceedings.neurips.cc/paper_files/paper/2023/file/0e735e4b4f07de483cbe250130992726-Paper-Datasets_and_Benchmarks.pdf)

Export one score per clip per compression level from the detector under study. Higher scores must indicate stronger evidence of manipulation. Set the threshold on a separate calibration split and keep it fixed across test datasets and compression levels. Keep related clips, including re-encodings and manipulated derivatives of the same source, together when splitting data. Record the checkpoint, dataset versions, split, and clip aggregation method with any published results.

The evaluator needs Python 3 and uses the standard library. It reads scores already produced by a detector.

```csv
dataset,compression,clip_id,label,score
example,high,clip-a,genuine,0.20
example,high,clip-b,manipulated,0.70
example,low,clip-a,genuine,0.60
example,low,clip-b,manipulated,0.40
```

```sh
python3 research/evaluate_media.py scores.csv --threshold 0.50
```

The fictional example yields zero false alarms and misses at high quality, and one false alarm and one miss at low quality. Each group reports counts alongside rates. A missing class produces a JSON null rate. Scores equal to the threshold count as positive.

These example scores verify the evaluator. Measuring detector accuracy requires scores from held-out labeled media.
