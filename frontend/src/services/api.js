// /Users/kingal/mapem/frontend/src/services/api.js
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5050';

export const uploadTree = (file) => {
  const formData = new FormData();
  formData.append('gedcom_file', file);
  formData.append('tree_name', file.name);
  formData.append('uploader_name', 'King');
  return axios.post(`${API_BASE_URL}/api/upload/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
};

export const getTree = (treeId) => {
  return axios.get(`${API_BASE_URL}/api/trees/${treeId}`);
};

export const compareTrees = (newId, existingId) => {
  return axios.get(`${API_BASE_URL}/api/compare_trees`, {
    params: { new_id: newId, existing_id: existingId }
  });
};

export const search = (query) => {
  return axios.get(`${API_BASE_URL}/api/search`, { params: { q: query } });
};

export const getMovements = (treeId) =>
  axios.get(`${API_BASE_URL}/api/movements/${treeId}`).then(res => res.data);

export const getPeople = (treeId) =>
  axios.get(`${API_BASE_URL}/api/people`, { params: { tree_id: treeId } }).then(res => res.data);

export const getEvents = (treeId) =>
  axios.get(`${API_BASE_URL}/api/events`, { params: { tree_id: treeId } }).then(res => res.data);

export const getTimeline = (treeId) =>
  axios.get(`${API_BASE_URL}/api/timeline/${treeId}`).then(res => res.data);

export const getSchema = () =>
  axios.get(`${API_BASE_URL}/api/schema`).then(res => res.data);
