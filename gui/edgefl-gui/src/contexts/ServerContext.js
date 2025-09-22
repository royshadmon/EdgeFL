import React, { createContext, useContext, useState } from 'react';

const ServerContext = createContext();

export const useServer = () => {
  const context = useContext(ServerContext);
  if (!context) {
    throw new Error('useServer must be used within a ServerProvider');
  }
  return context;
};

export const ServerProvider = ({ children }) => {
  const [nodeUrl, setNodeUrl] = useState('localhost:8080');

  const getServerUrl = () => {
    return nodeUrl.startsWith('http://') || nodeUrl.startsWith('https://') 
      ? nodeUrl 
      : `http://${nodeUrl}`;
  };

  const value = {
    nodeUrl,
    setNodeUrl,
    serverUrl: getServerUrl(),
  };

  return (
    <ServerContext.Provider value={value}>
      {children}
    </ServerContext.Provider>
  );
};
