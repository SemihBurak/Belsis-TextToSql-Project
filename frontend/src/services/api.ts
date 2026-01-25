import axios from 'axios';
import { ChatResponse, Database } from '../types';

const API_BASE = '/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export async function sendQuestion(question: string): Promise<ChatResponse> {
  const response = await api.post<ChatResponse>('/chat', { question });
  return response.data;
}

export async function getDatabases(): Promise<{ count: number; databases: Database[] }> {
  const response = await api.get('/databases');
  return response.data;
}

export async function getDatabaseSchema(dbName: string): Promise<unknown> {
  const response = await api.get(`/database/${encodeURIComponent(dbName)}/schema`);
  return response.data;
}
