import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useServer } from '../contexts/ServerContext';
import { startTraining } from '../services/api';

const StartTrainingPage = () => {
  const navigate = useNavigate();
  const { serverUrl, indexValue, setIndexValue } = useServer();
  const [totalRounds, setTotalRounds] = useState(10);
  const [minParams, setMinParams] = useState(3);
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const data = await startTraining(serverUrl, { totalRounds, minParams, index: indexValue });
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
        <h1>Step 2: Start Training</h1>
        <p>Begin the EDGEFL training process</p>
      </div>

      <form onSubmit={handleSubmit} className="form-container">
        <div className="info-box">
          <h3>Training Configuration</h3>
          <p>Configure the parameters for your federated learning training process.</p>
        </div>

        <div className="form-group">
          <label htmlFor="totalRounds">Total Rounds:</label>
          <input
            type="number"
            id="totalRounds"
            value={totalRounds}
            onChange={(e) => setTotalRounds(e.target.value)}
            min="1"
            max="100"
            required
          />
          <small>Number of federated learning rounds to execute</small>
        </div>

        <div className="form-group">
          <label htmlFor="minParams">Minimum Parameters:</label>
          <input
            type="number"
            id="minParams"
            value={minParams}
            onChange={(e) => setMinParams(e.target.value)}
            min="1"
            max="10"
            required
          />
          <small>Minimum number of parameters required for aggregation</small>
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
          <small>Index name to use for this training session</small>
        </div>

        <button type="submit" disabled={loading} className="btn-primary">
          {loading ? 'Starting Training...' : 'Start Training'}
        </button>
      </form>

      {error && (
        <div className="error-message">
          <h3>Error:</h3>
          <p>{error}</p>
        </div>
      )}

      {response && (
        <div className="success-message">
          <h3>Success!</h3>
          <p>Training has been started successfully.</p>
          <pre>{JSON.stringify(response, null, 2)}</pre>
          <p>Click Next to continue to inference step.</p>
        </div>
      )}

      <div className="navigation-buttons">
        <button onClick={() => navigate('/init')} className="btn-secondary">
          ← Previous
        </button>
        {response && (
          <button onClick={() => navigate('/infer')} className="btn-primary">
            Next →
          </button>
        )}
      </div>
    </div>
  );
};

export default StartTrainingPage;
