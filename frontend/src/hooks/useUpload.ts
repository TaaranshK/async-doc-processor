import { useState, useCallback } from 'react';
import { uploadDocuments } from '@/api/documents';

interface UploadState {
  files: File[];
  uploading: boolean;
  progress: number;
  error: string | null;
}

const ALLOWED_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/msword',
  'text/plain',
  'text/csv',
];
const MAX_SIZE = 50 * 1024 * 1024; // 50MB

export function useUpload() {
  const [state, setState] = useState<UploadState>({
    files: [],
    uploading: false,
    progress: 0,
    error: null,
  });

  const validateFile = useCallback((file: File): string | null => {
    if (!ALLOWED_TYPES.includes(file.type) && !file.name.match(/\.(pdf|docx|doc|txt|csv)$/i)) {
      return `Unsupported file type: ${file.type || file.name.split('.').pop()}`;
    }
    if (file.size > MAX_SIZE) {
      return `File too large: ${(file.size / 1024 / 1024).toFixed(1)}MB (max 50MB)`;
    }
    return null;
  }, []);

  const addFiles = useCallback((newFiles: File[]) => {
    setState(prev => {
      const validFiles: File[] = [];
      let error: string | null = null;

      for (const file of newFiles) {
        const err = validateFile(file);
        if (err) {
          error = err;
        } else {
          validFiles.push(file);
        }
      }

      return {
        ...prev,
        files: [...prev.files, ...validFiles],
        error,
      };
    });
  }, [validateFile]);

  const removeFile = useCallback((index: number) => {
    setState(prev => ({
      ...prev,
      files: prev.files.filter((_, i) => i !== index),
      error: null,
    }));
  }, []);

  const upload = useCallback(async (): Promise<string[]> => {
    setState(prev => ({ ...prev, uploading: true, progress: 0, error: null }));
    try {
      const response = await uploadDocuments(state.files);
      setState(prev => ({ ...prev, uploading: false, files: [], progress: 100 }));
      return response.items.map(item => item.job_id);
    } catch (error) {
      setState(prev => ({ ...prev, uploading: false, error: 'Upload failed' }));
      throw error;
    }
  }, [state.files]);

  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  return {
    ...state,
    addFiles,
    removeFile,
    upload,
    clearError,
    validateFile,
  };
}
