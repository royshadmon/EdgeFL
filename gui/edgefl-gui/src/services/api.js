/**
 * API service for EDGEFL endpoints
 * Abstracts all HTTP calls to the EDGEFL backend
 */


/**
 * Generic API call function
 */
const apiCall = async (url, options = {}) => {
  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const config = {
    ...defaultOptions,
    ...options,
    headers: {
      ...defaultOptions.headers,
      ...options.headers,
    },
  };

  try {
    const response = await fetch(url, config);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.message || `HTTP error! status: ${response.status}`);
    }

    return data;
  } catch (error) {
    throw new Error(error.message || 'An unexpected error occurred');
  }
};

/**
 * Initialize EDGEFL with node URLs and index
 */
export const initializeEDGEFL = async (serverUrl, { nodeUrls, index }) => {
  return apiCall(`http://${serverUrl}/init`, {
    method: 'POST',
    body: JSON.stringify({
      nodeUrls: nodeUrls.filter(url => url.trim() !== ''),
      index: index.trim()
    }),
  });
};

/**
 * Start training with specified parameters
 */
export const startTraining = async (serverUrl, { totalRounds, minParams, index }) => {
  return apiCall(`http://${serverUrl}/start-training`, {
    method: 'POST',
    body: JSON.stringify({
      totalRounds: parseInt(totalRounds),
      minParams: parseInt(minParams),
      index: index.trim()
    }),
  });
};

/**
 * Run inference with input data
 */
export const runInference = async (serverUrl, { input, index }) => {
  return apiCall(`http://${serverUrl}/infer`, {
    method: 'POST',
    body: JSON.stringify({
      input: [input],
      index: index.trim()
    }),
  });
};

/**
 * Utility function to validate 28x28 array
 */
export const validateInputArray = (inputData) => {
  try {
    const parsed = JSON.parse(inputData);
    if (Array.isArray(parsed) && parsed.length === 28 && Array.isArray(parsed[0]) && parsed[0].length === 28) {
      return parsed;
    }
    throw new Error('Input must be a 28x28 array');
  } catch (err) {
    throw new Error('Invalid JSON format. Please provide a valid 28x28 array.');
  }
};

/**
 * Generate sample 28x28 array for testing
 */
export const generateSampleArray = () => {
  return Array.from({ length: 28 }, () => 
    Array.from({ length: 28 }, () => Math.random())
  );
};
