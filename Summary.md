## Summary

Improvements to the MNIST federated learning demo across training accuracy,
data loading, and canvas inference quality.

---

## Changes

### `edgefl/data/mnist/store_data.py`
**Stratified data loading**

Previously, images were loaded sequentially from the MNIST dataset, causing
early training rounds to be heavily biased toward lower digit classes (MNIST
is sorted by label). Replaced with stratified sampling that builds a
per-class index list and takes exactly `num_rows // 10` images per class per
round. This guarantees balanced class exposure across all stored data
regardless of how many rounds or rows are configured.

---

### `edgefl/platform_components/data_handlers/custom_data_handler.py`
**Training pipeline fixes and accuracy improvements**

- **Removed double normalization:** `preprocess()` was dividing pixel values
  by 255 a second time after `load_dataset()` had already done it. Fixed to
  only cast dtype.
- **Removed `WHERE round_number` filter:** The original query fetched only 50
  images per training round. Changed to `LIMIT 1000` with no round filter so
  each round trains on all available data.
- **Added class weights:** `compute_class_weight('balanced')` applied during
  `fit()` to prevent the model from biasing toward majority classes in
  imbalanced rounds.
- **Removed BatchNormalization:** Was added as an improvement but caused
  complete model collapse under FedAvg. FedAvg averages `moving_mean` and
  `moving_variance` across nodes, corrupting the running statistics. Removed
  entirely.
- **Fixed `direct_inference()`:** Added normalization check
  (`if data.max() > 1.0: data / 255.0`) so the inference endpoint handles
  both raw 0–255 and pre-normalized 0–1 inputs correctly.
- **Replaced `val_accuracy` with `run_inference()`:** Removed
  `validation_data` from `fit()` and updated `EarlyStopping` to monitor
  `loss`. After each training round, `run_inference()` is called to evaluate
  against `TEST_TABLE` and log clean per-round test accuracy.

---

### `gui/edgefl-gui/src/components/InputDataSelector.js`
**Thicker canvas brush**

The draw canvas used a 1×1 pixel brush. MNIST digits have strokes 2–4 pixels
wide, so thin canvas strokes produced weak activations in the model's
convolutional filters. Changed to a 2×2 brush — each mouse position now fills
a 2×2 block of cells, better matching MNIST stroke width.

---

### `gui/edgefl-gui/src/pages/InferPage.js`
**Canvas preprocessing — auto-centering and Gaussian blur**

Two preprocessing steps are now applied to canvas input before inference:

1. **`centerAndScale()`** — Computes the bounding box of all drawn pixels,
   scales the digit so its largest dimension fits within a 20×20 target area,
   and translates it to the center of the 28×28 grid. MNIST digits are
   centered and scaled to fill roughly 20×20 of the 28×28 grid; freehand
   drawings are not, causing the model's spatially-trained filters to
   misfire.

2. **`gaussianBlur()`** — Applies 3 passes of a Gaussian kernel and
   normalizes to max=1.0. Converts the hard binary 0/1 canvas output into
   smooth gradients that more closely resemble the normalized float values
   the model was trained on.

Pipeline for canvas input: `draw → centerAndScale → gaussianBlur → inference`

---

## Test Results

- JSON array inference (smooth 0–255 normalized): ~92% on 30-sample test set
- JSON array inference (binary 0/1): ~90% on 30-sample test set  
- Canvas inference: all digits 0–9 correctly classified after fixes;
  noticeable improvement on curved digits (6, 9) after auto-centering
