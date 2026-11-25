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

## Frame-change baseline

The baseline samples the first 30 seconds at 5 frames per second, resizes each frame to 64×64 grayscale, and reports the largest mean absolute pixel change between adjacent frames, normalized to 0–1. It needs FFmpeg on your PATH.

Create a manifest CSV with the columns `dataset,compression,clip_id,label,path`. Paths can be absolute or relative to the manifest. Use short labeled clips and keep related versions together across splits.

```sh
python3 research/score_media.py heldout.csv > scores.csv
python3 research/evaluate_media.py scores.csv --threshold 0.50
```

The threshold above is illustrative. Select a threshold on a separate calibration set before evaluating held-out clips. Cuts, motion and lighting changes can raise the score on genuine clips. Subtle edits can produce low scores. Use this heuristic as a baseline for comparison with a learned detector.

## Select a threshold on a separate split

Generate score files for calibration and held-out clips, then run:

```sh
python3 research/evaluate_media.py heldout-scores.csv --calibration calibration-scores.csv --max-fpr 0.05
```

The example caps the pooled calibration false-positive rate at 5%. The evaluator maximizes calibration recall under that cap, preferring fewer false positives and then a higher threshold when tied. It applies the selected cutoff to every held-out stratum and reports calibration counts and rates separately. The cap applies to calibration observations. Held-out rates may differ.

The evaluator rejects identical dataset and clip identifiers across splits, even at different compressions. Assign related versions and derivatives of each source to the same split before scoring. The check relies on identifiers and cannot infer shared origins from media content.

## Compare two scorers on the same clips

Supply four score CSVs in the format above. The two calibration files must describe the same labeled clips and compression levels, as must the two held-out files. The order of the rows can differ. Each scorer receives its own calibration cutoff under the same false-alarm cap.

```sh
python3 research/compare_media.py \
  --baseline-calibration baseline-cal.csv --candidate-calibration candidate-cal.csv \
  --baseline-test baseline-test.csv --candidate-test candidate-test.csv --max-fpr 0.05
```

The report shows each scorer's calibration cutoff, held-out confusion counts, and the change in error rates in percentage points for each dataset and compression level. Negative changes mean fewer errors for the candidate. Rates remain unavailable for strata without the corresponding class. Any excluded clip must be excluded from both files for its split, and exclusions should be recorded in the experiment notes.

## Train a logistic regression candidate

Install scikit-learn in your Python environment and make FFmpeg available on your PATH. Use three clip manifests with the same columns as the frame-change baseline.

```sh
python3 research/learn_media.py --train train.csv --calibration calibration.csv \
  --test heldout.csv --max-fpr 0.05
```

The candidate learns from peak and mean adjacent-frame change. Feature scaling and logistic regression are fitted on the training split. The peak-only baseline and candidate receive their own calibration cutoffs, then share the same held-out clips. The command rejects repeated dataset/clip identifiers and repeated resolved media paths across splits. Keep derivatives and re-encodings together even when filenames and IDs differ.

This candidate measures temporal changes across the frame. It can miss subtle facial edits and can respond to motion or cuts in genuine videos. Synthetic clips exercise the implementation. Estimates of deepfake detection performance require real held-out data.

## Synthetic compression and motion stress test

Run `python3 research/stress_media.py` to generate separate training, calibration and held-out clips from fixed seeds. Each split contains five source clips, each encoded at two MJPEG quality settings. The genuine scenarios are a hard cut, a moving object and lighting flicker. The simulated edits alternate a local patch or the full frame. The report breaks out each case and quality setting.

In the initial run at a zero pooled calibration false-alarm cap, both scorers produced zero false alarms across the six genuine held-out encodings and missed all four edit encodings. The two encodings of each source are related observations. This pilot illustrates a failure of the selected operating points on controlled inputs. It provides no estimate of accuracy on real deepfake footage.

## Compare whole-frame and spatial features

Use `--spatial` with `learn_media.py` to add three measurements from 8×8 pixel blocks. For each frame pair, subtract the median signed pixel change before measuring absolute residuals. This reduces the contribution of uniform brightness shifts. The model then sees the average strongest block residual, average residual across blocks, and their average difference.

The stress command runs both candidates on identical splits at the same calibration cap and includes the spatial run under `spatial_experiment`. In the exploratory pilot at the zero cap, the whole-frame candidate detected 0 of 4 simulated edit encodings and the spatial candidate detected 3 of 4. Both flagged 0 of 6 genuine encodings. The remaining miss was the low-quality full-frame edit. These cases were already used to examine earlier failures. Evaluate on fresh source clips before drawing performance conclusions.

## Fresh synthetic holdout

Run `python3 research/stress_media.py --fresh` to change only the test split. The training and calibration scenarios, seeds, feature definitions and false-positive cap stay the same. The fresh split includes camera panning, gradual lighting change, a cut during motion, a low-contrast patch and a one-frame patch, each at the same two MJPEG settings.

At the default cap, the peak-only and whole-frame scorers flagged 0 of 6 genuine encodings and both missed all 4 simulated edit encodings. The spatial model also missed all 4 edits and flagged 4 of the 6 genuine encodings: both qualities of the pan and the moving cut. The calibration outputs matched the original run. These results show that the spatial improvement failed to transfer to this fresh synthetic suite. They do not establish performance on real videos.

## Motion-aligned candidate

Run `python3 research/stress_media.py --fresh --motion` to add a motion-aligned candidate to the same comparison. For custom manifests, pass `--motion` to `learn_media.py`. The candidate searches integer translations of up to eight pixels in each direction, minimizing the mean absolute difference between brightness-centered crops. It computes block-change features on the aligned 48×48 interior and retains the original whole-frame features.

With the same training and calibration clips and the default zero calibration false-alarm cap, the motion-aligned candidate flagged 0 of 6 genuine encodings, compared with 4 of 6 for the unaligned spatial candidate. Both missed all 4 simulated edit encodings. The comparison changes both the registration and the spatial crop, so it cannot isolate which change explains the reduction. The fresh suite was used to identify the original motion failure and now serves as a regression set.
