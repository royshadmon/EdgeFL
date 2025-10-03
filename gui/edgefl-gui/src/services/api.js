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
  console.log(`${serverUrl}/init`);
  return apiCall(`${serverUrl}/init`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      nodeUrls: nodeUrls.filter(url => url.trim() !== ''),
      index: index.trim()
    }),
  });
};

// export const initializeEDGEFL = async (serverUrl, { nodeUrls, index }) => {
//   console.log(`${serverUrl}/init`);
//   return apiCall(`${serverUrl}/init`, {
//     method: 'POST',
//     body: JSON.stringify({
//       nodeUrls: nodeUrls.filter(url => url.trim() !== ''),
//       index: index.trim()
//     }),
//   });
// };

/**
 * Start training with specified parameters
 */
export const startTraining = async (serverUrl, { totalRounds, minParams, index }) => {
  return apiCall(`${serverUrl}/start-training`, {
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
// export const runInference = async (serverUrl, { input, index }) => {

export const runInference = async (serverUrl, { input, index }) => {
  console.log(`${serverUrl}/infer`);
  console.log({ input, index: index.trim() });

  return apiCall(`${serverUrl}/infer`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      input: input,
      index: index.trim()
    }),
  });
};

/**
 * Process PNG for xray FL  demo. this function will only work for the xray dataset
 */
export const validateAndProcessImage = (file) => {
  return new Promise((resolve, reject) => {
    if (!file || !file.type.startsWith('image/png')) {
      return reject(new Error('Please upload a valid PNG image.'));
    }

    const img = new Image();
    const reader = new FileReader();

    reader.onload = () => {
      img.src = reader.result;
    };

    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = 224;
      canvas.height = 224;
      const ctx = canvas.getContext('2d');

      ctx.drawImage(img, 0, 0, 224, 224);
      const imageData = ctx.getImageData(0, 0, 224, 224);
      const grayData = new Float32Array(224 * 224);

      for (let i = 0; i < imageData.data.length; i += 4) {
        const r = imageData.data[i];
        const g = imageData.data[i + 1];
        const b = imageData.data[i + 2];
        grayData[i / 4] = (r + g + b) / 3 / 255; // grayscale + normalization
      }

      resolve(grayData);
    };

    reader.onerror = () => {
      reject(new Error('Failed to read the image file.'));
    };

    reader.readAsDataURL(file);
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
