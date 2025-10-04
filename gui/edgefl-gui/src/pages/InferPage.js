import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useServer } from '../contexts/ServerContext';
import {runInference, validateInputArray, generateSampleArray, validateAndProcessImage, evaluateTestSet} from '../services/api';
import InputDataSelector from '../components/InputDataSelector';

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
        // For grid drawings, the data is already in the correct format
        inputArray = typeof inputData === 'string' ? JSON.parse(inputData) : inputData;
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
