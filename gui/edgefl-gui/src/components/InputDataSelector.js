import React, { useState } from 'react';

const InputDataSelector = ({ inputData, setInputData, onDataChange }) => {
  const [inputType, setInputType] = useState('json');
  const [selectedFile, setSelectedFile] = useState(null);
  
  // Grid state for draw canvas
  const [gridData, setGridData] = useState(() => 
    Array(28).fill().map(() => Array(28).fill(0))
  );

  const handleInputTypeChange = (type) => {
    setInputType(type);
    setInputData('');
    setSelectedFile(null);
    // Reset grid when switching away from draw
    if (type !== 'draw') {
      setGridData(Array(28).fill().map(() => Array(28).fill(0)));
    }
    if (onDataChange) onDataChange('', type);
  };

  const toggleGridCell = (row, col) => {
    const newGridData = gridData.map((rowData, r) => 
      rowData.map((cell, c) => 
        r === row && c === col ? (cell === 1 ? 0 : 1) : cell
      )
    );
    setGridData(newGridData);
    setInputData(JSON.stringify(newGridData, null, 2));
    if (onDataChange) onDataChange(newGridData, 'draw');
  };

  const clearGrid = () => {
    const emptyGrid = Array(28).fill().map(() => Array(28).fill(0));
    setGridData(emptyGrid);
    setInputData(JSON.stringify(emptyGrid, null, 2));
    if (onDataChange) onDataChange(emptyGrid, 'draw');
  };

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setSelectedFile(file);

    const reader = new FileReader();
    reader.onload = (e) => {
      if (inputType === 'json') {
        try {
          const jsonData = JSON.parse(e.target.result);
          setInputData(JSON.stringify(jsonData, null, 2));
          if (onDataChange) onDataChange(JSON.stringify(jsonData, null, 2), inputType);
        } catch (error) {
          setInputData('Invalid JSON file');
          if (onDataChange) onDataChange('Invalid JSON file', inputType);
        }
      } else if (inputType === 'png' || inputType === 'jpg' || inputType === 'wav') {
        // For binary files, we'll store the file info and let the parent handle the actual file
        setInputData(`File: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`);
        if (onDataChange) onDataChange(file, inputType);
      }
    };

    if (inputType === 'json') {
      reader.readAsText(file);
    } else {
      // For binary files, we'll pass the file object to parent
      if (onDataChange) onDataChange(file, inputType);
    }
  };


  const renderInputTypeSelector = () => (
    <div className="form-group">
      <label>Input Data Type:</label>
      <div className="input-type-selector">
        {[
          { value: 'json', label: 'JSON Array', icon: '📄' },
          { value: 'jpg', label: 'JPG Image', icon: '🖼️' },
          { value: 'png', label: 'PNG Image', icon: '🖼️' },
          { value: 'wav', label: 'WAV Audio', icon: '🎵' },
          { value: 'draw', label: 'Draw Canvas', icon: '✏️' }
        ].map(({ value, label, icon }) => (
          <button
            key={value}
            type="button"
            className={`input-type-btn ${inputType === value ? 'active' : ''}`}
            onClick={() => handleInputTypeChange(value)}
          >
            <span className="input-type-icon">{icon}</span>
            <span className="input-type-label">{label}</span>
          </button>
        ))}
      </div>
    </div>
  );

  const renderJsonInput = () => (
    <div className="form-group">
      <label htmlFor="inputData">JSON Array Input:</label>
      <textarea
        id="inputData"
        value={inputData}
        onChange={(e) => {
          setInputData(e.target.value);
          if (onDataChange) onDataChange(e.target.value, inputType);
        }}
        placeholder="Enter a 28x28 JSON array or upload a JSON file..."
        rows={8}
        required
      />
      <small>Provide a 28x28 array in JSON format or upload a JSON file.</small>
    </div>
  );

  const renderFileUpload = () => (
    <div className="form-group">
      <label htmlFor="fileUpload">
        Upload {inputType.toUpperCase()} File:
      </label>
      <div className="file-upload-container">
        <input
          type="file"
          id="fileUpload"
          accept={inputType === 'png' ? '.png' : inputType === 'jpg' ? '.jpg,.jpeg' : inputType === 'wav' ? '.wav' : '.json'}
          // accept={
          //   inputType === 'image' ? '.jpg,.jpeg,.png' :
          //   inputType === 'audio' ? '.wav' :
          //   '.json'
          // }
          onChange={handleFileUpload}
          className="file-input"
        />
        <label htmlFor="fileUpload" className="file-upload-label">
          <span className="file-upload-icon">📁</span>
          Choose {inputType.toUpperCase()} File
        </label>
        {selectedFile && (
          <div className="file-info">
            <span className="file-name">{selectedFile.name}</span>
            <span className="file-size">({(selectedFile.size / 1024).toFixed(1)} KB)</span>
          </div>
        )}
      </div>
      <small>
        {inputType === 'jpg' && 'Upload a JPG image file for inference.'}
        {inputType === 'png' && 'Upload a PNG image file for inference.'}
        {inputType === 'wav' && 'Upload a WAV audio file for inference.'}
        {inputType === 'json' && 'Upload a JSON file containing your data array.'}
      </small>
    </div>
  );

  const renderDrawCanvas = () => (
    <div className="form-group">
      <label>Draw Canvas (28x28 Grid):</label>
      <div className="draw-canvas-container">
        <div className="grid-container">
          {gridData.map((row, rowIndex) => (
            <div key={rowIndex} className="grid-row">
              {row.map((cell, colIndex) => (
                <div
                  key={`${rowIndex}-${colIndex}`}
                  className={`grid-cell ${cell ? 'filled' : ''}`}
                  onClick={() => toggleGridCell(rowIndex, colIndex)}
                  onMouseEnter={(e) => {
                    if (e.buttons === 1) { // Left mouse button is pressed
                      toggleGridCell(rowIndex, colIndex);
                    }
                  }}
                />
              ))}
            </div>
          ))}
        </div>
        <div className="draw-controls">
          <button type="button" onClick={clearGrid} className="btn-secondary">
            Clear Grid
          </button>
          <div className="grid-info">
            <small>Click cells to draw. Click and drag to draw continuously.</small>
          </div>
        </div>
      </div>
      <small>Draw on the 28x28 grid above. Each cell represents a pixel in your drawing.</small>
    </div>
  );

  return (
    <div className="input-data-selector">
      {renderInputTypeSelector()}
      
      {inputType === 'json' && renderJsonInput()}
      {(inputType === 'png' || inputType === 'jpg' || inputType === 'wav') && renderFileUpload()}
      {inputType === 'draw' && renderDrawCanvas()}
    </div>
  );
};

export default InputDataSelector;
