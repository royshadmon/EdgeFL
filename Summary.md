## Summary

Improvements to the MNIST federated learning demo across training accuracy,
data loading, and canvas inference quality.


## Changes

### edgefl/data/mnist/store_data.py

Stratified data loading

Previously, images were loaded sequentially from the MNIST dataset, causing
early training rounds to be heavily biased toward lower digit classes (MNIST
is sorted by label). Replaced with stratified sampling that builds a
per-class index list for both the train and test datasets, then takes exactly
num_rows // 10 images per class per round (shuffled within each class for
variety). This guarantees balanced class exposure across all stored data
regardless of how many rounds or rows are configured. Image arrays are also
now serialized with json.dumps() before insertion to ensure consistent
string encoding in the database.


### edgefl/platform_components/data_handlers/custom_data_handler.py

Training pipeline fixes and accuracy improvements


1. Fixed normalization: load_dataset() was returning raw uint8 pixel
values without normalizing them. Added / 255.0 to both the train and test
arrays in load_dataset() so data arrives pre-normalized. preprocess()
now only casts dtype to float32 and no longer reshapes (since
load_dataset() already handles reshaping).
2. Removed WHERE round_number filter: The original query fetched only
images matching the current round number. Changed to LIMIT 1000
(train) and LIMIT 200 (test) with no round filter so each training round
uses all available data. load_dataset() signature updated to make
round_number optional.
3. Added Dropout regularization: Added Dropout(0.25) after each
convolutional block and Dropout(0.5) before the output layer in
model_def() to reduce overfitting.
4. Added class weights: compute_class_weight('balanced') applied during
fit() to prevent the model from biasing toward majority classes in
imbalanced rounds.
5. Tuned training hyperparameters: batch_size reduced from 128 to 32,
epochs increased from 1 to 5, and EarlyStopping patience set to 5
(previously commented out). These changes give the model more opportunity
to converge per round while still guarding against overfitting.
6. Fixed direct_inference(): Added normalization check
(if data.max() > 1.0: data = data / 255.0) so the inference endpoint
handles both raw 0–255 and pre-normalized 0–1 inputs correctly.
7. Replaced val_accuracy with run_inference(): Removed
validation_data from fit() and updated EarlyStopping to monitor
loss. After each training round, run_inference() is called to evaluate
against TEST_TABLE and log clean per-round test accuracy.
8. Simplified get_all_test_data(): Removed the old offset-based batching
loop (which was fetching only 50 rows and had the batching logic stubbed
out). Replaced with a single LIMIT 200 query, consistent with the
run_inference() approach.



### gui/edgefl-gui/src/components/InputDataSelector.js

Wider canvas brush

The draw canvas used a 1×1 pixel brush. MNIST digits have strokes 2–4 pixels
wide, so thin canvas strokes produced weak activations in the model's
convolutional filters. Changed to a 5-cell cross-shaped brush — each mouse
position now fills the target cell plus its 4 cardinal neighbors (up, down,
left, right), better matching MNIST stroke width.


### gui/edgefl-gui/src/pages/InferPage.js

Canvas preprocessing — auto-centering and Gaussian blur

Two preprocessing steps are now applied to canvas input before inference:


1. centerAndScale() — Computes the bounding box of all drawn pixels,
scales the digit so its largest dimension fits within a 20×20 target area,
and translates it to the center of the 28×28 grid. MNIST digits are
centered and scaled to fill roughly 20×20 of the 28×28 grid; freehand
drawings are not, causing the model's spatially-trained filters to
misfire.
2. gaussianBlur() — Applies 3 passes of a Gaussian kernel and
normalizes to max=1.0. Converts the hard binary 0/1 canvas output into
smooth gradients that more closely resemble the normalized float values
the model was trained on.


Pipeline for canvas input: draw → centerAndScale → gaussianBlur → inference


Test Results


JSON array inference (smooth 0–255 normalized): ~92% on 30-sample test set, originally was ~68%, about ~24% improvement.
Canvas inference: all digits 0–9 correctly classified after fixes;
noticeable improvement on curved digits (6, 9) after auto-centering