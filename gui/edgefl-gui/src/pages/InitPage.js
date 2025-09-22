import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useServer } from '../contexts/ServerContext';
import { initializeEDGEFL } from '../services/api';

const InitPage = () => {
  const navigate = useNavigate();
  const { serverUrl, indexValue, setIndexValue } = useServer();
  const [nodeUrls, setNodeUrls] = useState(['http://localhost:8081', 'http://localhost:8082', 'http://localhost:8083']);
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);

  const addNodeUrl = () => {
    setNodeUrls([...nodeUrls, '']);
  };

  const updateNodeUrl = (index, value) => {
    const newUrls = [...nodeUrls];
    newUrls[index] = value;
    setNodeUrls(newUrls);
  };

  const removeNodeUrl = (index) => {
    const newUrls = nodeUrls.filter((_, i) => i !== index);
    setNodeUrls(newUrls);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const data = await initializeEDGEFL(serverUrl, { nodeUrls, index: indexValue });
      setResponse(data);
      // Navigate to next page after successful init
      setTimeout(() => {
        navigate('/start-training');
      }, 2000);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Step 1: Initialize EDGEFL</h1>
        <p>Configure the initial setup for your EDGEFL training session</p>
      </div>

      <form onSubmit={handleSubmit} className="form-container">
        <div className="form-group">
          <label htmlFor="index">Index Name:</label>
          <input
            type="text"
            id="index"
            value={indexValue}
            onChange={(e) => setIndexValue(e.target.value)}
            placeholder="Enter index name"
            required
          />
        </div>

        <div className="form-group">
          <label>Node URLs:</label>
          {nodeUrls.map((url, index) => (
            <div key={index} className="node-url-row">
              <input
                type="url"
                value={url}
                onChange={(e) => updateNodeUrl(index, e.target.value)}
                placeholder="http://localhost:8081"
                required
              />
              {nodeUrls.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeNodeUrl(index)}
                  className="btn-danger"
                >
                  Remove
                </button>
              )}
            </div>
          ))}
          <button
            type="button"
            onClick={addNodeUrl}
            className="btn-success"
          >
            Add Node URL
          </button>
        </div>

        <button type="submit" disabled={loading} className="btn-primary">
          {loading ? 'Initializing...' : 'Initialize'}
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
          <p>EDGEFL has been initialized successfully.</p>
          <pre>{JSON.stringify(response, null, 2)}</pre>
          <p>Redirecting to next step...</p>
        </div>
      )}

      <div className="navigation-buttons">
        <button onClick={() => navigate('/start-training')} className="btn-primary">
          Next →
        </button>
      </div>
    </div>
  );
};

export default InitPage;
