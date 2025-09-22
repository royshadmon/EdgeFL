import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useServer } from '../contexts/ServerContext';
import { runInference, validateInputArray, generateSampleArray } from '../services/api';

const InferPage = () => {
  const navigate = useNavigate();
  const { serverUrl } = useServer();
  const [inputData, setInputData] = useState('');
  const [index, setIndex] = useState('test-index');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);

  const generateSampleData = () => {
    const array = generateSampleArray();
    setInputData(JSON.stringify(array, null, 2));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const inputArray = validateInputArray(inputData);
      const data = await runInference(serverUrl, { input: inputArray, index });
      setResponse(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
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
          <p>Provide a 28x28 array of input data for inference. This is typically image data (e.g., MNIST digits).</p>
        </div>

        <div className="form-group">
          <label htmlFor="index">Index Name:</label>
          <input
            type="text"
            id="index"
            value={index}
            onChange={(e) => setIndex(e.target.value)}
            placeholder="test-index"
            required
          />
          <small>Index name to use for inference</small>
        </div>

        <div className="form-group">
          <label htmlFor="inputData">Input Data (28x28 Array):</label>
          <textarea
            id="inputData"
            value={inputData}
            onChange={(e) => setInputData(e.target.value)}
            placeholder="Enter a 28x28 JSON array..."
            rows={8}
            required
          />
          <small>Provide a 28x28 array in JSON format. Use the "Generate Sample Data" button for a quick start.</small>
        </div>

        <div className="button-group">
          <button type="button" onClick={generateSampleData} className="btn-secondary">
            Generate Sample Data
          </button>
          <button type="submit" disabled={loading} className="btn-primary">
            {loading ? 'Running Inference...' : 'Run Inference'}
          </button>
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

      <div className="navigation-buttons">
        <button onClick={() => navigate('/start-training')} className="btn-secondary">
          ← Previous: Start Training
        </button>
        <button onClick={() => navigate('/init')} className="btn-secondary">
          ← Back to Initialize
        </button>
      </div>
    </div>
  );
};

export default InferPage;
