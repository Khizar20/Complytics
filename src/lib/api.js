import { API_URL } from '@/config';

const LOCAL_BASE = 'http://localhost:8000';

export const buildApiUrl = (path = '') => {
  if (!path) {
    return API_URL;
  }

  if (path.startsWith('http://localhost:8000')) {
    return API_URL + path.slice(LOCAL_BASE.length);
  }

  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }

  if (path.startsWith('/') || path.startsWith('$')) {
    return `${API_URL}${path}`;
  }

  return `${API_URL}/${path}`;
};

