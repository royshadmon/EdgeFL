import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useServer } from '../contexts/ServerContext';

const Layout = ({ children }) => {
  const { nodeUrl, setNodeUrl } = useServer();
  const location = useLocation();

  const navigation = [
    { path: '/init', label: 'Initialize', step: 1 },
    { path: '/start-training', label: 'Start Training', step: 2 },
    { path: '/infer', label: 'Inference', step: 3 },
  ];

  return (
    <div className="layout">
      <header className="header">
        <div className="header-content">
          <h1 className="logo">EDGEFL Demo</h1>
          <div className="server-config">
            <label htmlFor="nodeUrl">Node:</label>
            <input
              id="nodeUrl"
              type="text"
              value={nodeUrl}
              onChange={(e) => setNodeUrl(e.target.value)}
              placeholder="localhost:8080"
              className="server-input"
            />
          </div>
        </div>
      </header>

      <nav className="navigation">
        <div className="nav-content">
          {navigation.map(({ path, label, step }) => (
            <Link
              key={path}
              to={path}
              className={`nav-item ${location.pathname === path ? 'active' : ''}`}
            >
              <span className="step-number">{step}</span>
              <span className="step-label">{label}</span>
            </Link>
          ))}
        </div>
      </nav>

      <main className="main-content">
        {children}
      </main>

      <footer className="footer">
        <p>EDGEFL GUI Demo - Step through the federated learning process</p>
      </footer>
    </div>
  );
};

export default Layout;
