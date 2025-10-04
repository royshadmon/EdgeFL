import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ServerProvider } from './contexts/ServerContext';
import Layout from './components/Layout';
import InitPage from './pages/InitPage';
import StartTrainingPage from './pages/StartTrainingPage';
import InferPage from './pages/InferPage';
import './styles/App.css';

function App() {
  return (
    <ServerProvider>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Navigate to="/init" replace />} />
            <Route path="/init" element={<InitPage />} />
            <Route path="/start-training" element={<StartTrainingPage />} />
            <Route path="/infer" element={<InferPage />} />
          </Routes>
        </Layout>
      </Router>
    </ServerProvider>
  );
}

export default App;
