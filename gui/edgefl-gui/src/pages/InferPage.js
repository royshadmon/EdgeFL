import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useServer } from '../contexts/ServerContext';
import {runInference, validateInputArray, generateSampleArray, validateAndProcessImage, evaluateTestSet} from '../services/api';
import InputDataSelector from '../components/InputDataSelector';

function centerAndScale(grid) {
  const size = 28;
  const target = 20; // digits fill ~20x20 in MNIST

  // Find bounding box of all non-zero pixels
  let minR = size, maxR = -1, minC = size, maxC = -1;
  for (let r = 0; r < size; r++)
    for (let c = 0; c < size; c++)
      if (grid[r][c] > 0) {
        if (r < minR) minR = r;
        if (r > maxR) maxR = r;
        if (c < minC) minC = c;
        if (c > maxC) maxC = c;
      }

  // Nothing drawn — return as-is
  if (maxR === -1) return grid;

  const h = maxR - minR + 1;
  const w = maxC - minC + 1;

  // Scale factor to fit the larger dimension into target
  const scale = target / Math.max(h, w);

  const newH = Math.round(h * scale);
  const newW = Math.round(w * scale);

  // Top-left corner to center the scaled digit
  const startR = Math.round((size - newH) / 2);
  const startC = Math.round((size - newW) / 2);

  const out = Array.from({length: size}, () => Array(size).fill(0));

  for (let r = 0; r < newH; r++)
    for (let c = 0; c < newW; c++) {
      const srcR = Math.round(r / scale) + minR;
      const srcC = Math.round(c / scale) + minC;
      const dstR = startR + r;
      const dstC = startC + c;
      if (dstR >= 0 && dstR < size && dstC >= 0 && dstC < size)
        out[dstR][dstC] = grid[srcR][srcC];
    }

  return out;
}

function gaussianBlur(grid) {
  const kernel = [[1,2,1],[2,4,2],[1,2,1]];
  const size = 28;

  function blurOnce(g) {
    const out = Array.from({length: size}, () => Array(size).fill(0));
    for (let r = 1; r < size - 1; r++)
      for (let c = 1; c < size - 1; c++) {
        let val = 0;
        for (let kr = -1; kr <= 1; kr++)
          for (let kc = -1; kc <= 1; kc++)
            val += g[r + kr][c + kc] * kernel[kr + 1][kc + 1];
        out[r][c] = val / 16;
      }
    return out;
  }

  let result = blurOnce(blurOnce(blurOnce(grid)));

  let maxVal = 0;
  for (let r = 0; r < size; r++)
    for (let c = 0; c < size; c++)
      if (result[r][c] > maxVal) maxVal = result[r][c];
  if (maxVal > 0)
    for (let r = 0; r < size; r++)
      for (let c = 0; c < size; c++)
        result[r][c] /= maxVal;

  return result;
}

const InferPage = () => {
  const navigate = useNavigate();
  const { serverUrl, indexValue, setIndexValue } = useServer();
  const [inputData, setInputData] = useState('');
  const [inputType, setInputType] = useState('json');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);
  const [testEvalLoading, setTestEvalLoading] = useState(false);
  const [testEvalResponse, setTestEvalResponse] = useState(null);
  const [testEvalError, setTestEvalError] = useState(null);

  const generateSampleData = () => {
    const array = generateSampleArray();
    setInputData(JSON.stringify(array, null, 2));
  };

  const handleDataChange = (data, type) => {
    setInputData(data);
    setInputType(type);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResponse(null);

    let inputArray;
    try {

      if (inputType === 'json') {
        inputArray = validateInputArray(inputData);
      } else if (inputType === 'png' || inputType === 'jpg' || inputType === 'wav') {
        // For file uploads, we'll need to process the file
        // For now, we'll show an error that this feature is coming soon

        try {
            const floatArray = await validateAndProcessImage(inputData);
            console.log('Float32Array:', floatArray);

            inputArray = Array.from(floatArray);
            console.log('Converted to regular array:', inputArray);

            // You can now send `inputArray` to your FastAPI backend
          } catch (error) {
            console.error('Error processing image:', error.message);
          }

          // console.log(inputArray)
        // throw new Error(`${inputType.toUpperCase()} file processing is coming soon!`);
      } else if (inputType === 'draw') {
        const rawGrid = typeof inputData === 'string' ? JSON.parse(inputData) : inputData;
        inputArray = gaussianBlur(centerAndScale(rawGrid));
      }

      console.log("FINAL ARRAY:", inputArray)
      const data = await runInference(serverUrl, { input: inputArray, index: indexValue });
      setResponse(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleTestSetEvaluation = async () => {
    setTestEvalLoading(true);
    setTestEvalError(null);
    setTestEvalResponse(null);

    try {
      const data = await evaluateTestSet(serverUrl, indexValue);
      setTestEvalResponse(data);
    } catch (err) {
      setTestEvalError(err.message);
    } finally {
      setTestEvalLoading(false);
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Step 3: Inference</h1>
        <p>Run inference on the trained model</p>
      </div>

      <form onSubmit={handleSubmit} className="form-container">
        <div className="info-box">
          <h3>Inference Configuration</h3>
          <p>Choose your input data type and provide the data for inference.</p>
        </div>

        <div className="form-group">
          <label htmlFor="index">Index Name:</label>
          <input
            type="text"
            id="index"
            value={indexValue}
            onChange={(e) => setIndexValue(e.target.value)}
            placeholder="test-index"
            required
          />
          <small>Index name to use for inference</small>
        </div>

        <InputDataSelector
          inputData={inputData}
          setInputData={setInputData}
          onDataChange={handleDataChange}
        />

        <div className="button-group">
          {inputType === 'json' && (
            <button type="button" onClick={generateSampleData} className="btn-secondary">
              Generate Sample Data
            </button>
          )}
          <button type="submit" disabled={loading} className="btn-primary">
            {loading ? 'Running Inference...' : 'Run Inference'}
          </button>
        </div>

        <div className="button-group" style={{ marginTop: '20px', borderTop: '1px solid #eee', paddingTop: '20px' }}>
          <button 
            type="button" 
            onClick={handleTestSetEvaluation} 
            disabled={testEvalLoading || !indexValue.trim()} 
            className="btn-primary"
            style={{ backgroundColor: '#28a745' }}
          >
            {testEvalLoading ? 'Evaluating Test Set...' : 'Evaluate Test Set'}
          </button>
          <small style={{ display: 'block', marginTop: '5px', color: '#666' }}>
            Run model evaluation against the test dataset for index: {indexValue || 'test-index'}
          </small>
        </div>
      </form>

      {error && (
        <div className="error-message">
          <h3>Error:</h3>
          <p>{error}</p>
        </div>
      )}

      {response && (
        <div className="success-message">
          <h3>Inference Results:</h3>
          <pre>{JSON.stringify(response, null, 2)}</pre>
        </div>
      )}

      {testEvalError && (
        <div className="error-message">
          <h3>Test Set Evaluation Error:</h3>
          <p>{testEvalError}</p>
        </div>
      )}

      {testEvalResponse && (
        <div className="success-message">
          <h3>Test Set Evaluation Results:</h3>
          <pre>{JSON.stringify(testEvalResponse, null, 2)}</pre>
        </div>
      )}

      <div className="navigation-buttons">
        <button onClick={() => navigate('/start-training')} className="btn-secondary">
          ← Previous
        </button>
      </div>
    </div>
  );
};

export default InferPage;
