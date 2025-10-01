import React from 'react';
import { createRoot } from 'react-dom/client';
import { AppRouter } from './routes';
import './index.css';
import { ToastProvider } from './components/ui/toast';

const root = createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <ToastProvider>
      <AppRouter />
    </ToastProvider>
  </React.StrictMode>
);