// API Configuration
// Use Azure backend URL in production, localhost for development
const isProduction = import.meta.env.PROD || window.location.hostname !== 'localhost';
export const API_URL = isProduction 
  ? 'https://complytics-backend.victoriousforest-1b629d31.centralindia.azurecontainerapps.io'
  : 'http://localhost:8000';

// Other configuration constants can be added here 