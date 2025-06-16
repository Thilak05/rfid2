// Get network IP from environment or use localhost as fallback
const getApiUrl = () => {
  // Try to get the current hostname/IP
  const hostname = window.location.hostname;
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'http://localhost:5000/api';
  }
  return `http://${hostname}:5000/api`;
};

const API_URL = getApiUrl();

// Create axios instance with default config
import axios from 'axios';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout for RFID operations
});

export interface User {
  id: number;
  name: string;
  unique_id: string;
  email?: string;
  phone?: string;
  created_at: string;
  status: 'active' | 'inactive';
}

export interface Log {
  id: number;
  name: string;
  unique_id: string;
  entry_time?: string;
  exit_time?: string;
  status: string;
  user_name: string;
}

export interface Stats {
  total_users: number;
  inside_count: number;
  outside_count: number;
  today_entries: number;
  today_exits: number;
}

export const usersAPI = {
  getAll: async (): Promise<User[]> => {
    const response = await api.get('/users');
    return response.data;
  },

  create: async (user: Omit<User, 'id' | 'created_at'>): Promise<any> => {
    const response = await api.post('/users', user);
    return response.data;
  },

  update: async (id: number, user: Partial<User>): Promise<any> => {
    const response = await api.put(`/users/${id}`, user);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/users/${id}`);
  },
};

export const logsAPI = {
  getAll: async (): Promise<Log[]> => {
    const response = await api.get('/logs');
    return response.data;
  },
};

export const statsAPI = {
  get: async (): Promise<Stats> => {
    const response = await api.get('/stats');
    return response.data;
  },
};

export const rfidAPI = {
  read: async (): Promise<{ status: string; rfid_id?: string; message: string }> => {
    const response = await api.post('/rfid/read');
    return response.data;
  },

  getStatus: async (): Promise<{ rfid_id?: string; timestamp?: number; status: string }> => {
    const response = await api.get('/rfid/status');
    return response.data;
  },
};