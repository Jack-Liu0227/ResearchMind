import React, { useEffect, useState } from 'react';
import { getPhononResults, resolveFileUrl } from '../utils/apiClient';
import { API_CONFIG } from '../constants';

interface PhononViewerProps {
  composition?: string;  // 化学式,用于过滤
  className?: string;
}

export const PhononViewer: React.FC<PhononViewerProps> = ({ composition, className = '' }) => {
  const [phononFiles, setPhononFiles] = useState<string[]>([]);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [imageLoading, setImageLoading] = useState(false);

  useEffect(() => {
    loadPhononResults();
  }, [composition]);

  const loadPhononResults = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getPhononResults();
      const files = (response as any).files || [];

      // 如果指定了化学式,过滤相关文件
      const filteredFiles = composition
        ? files.filter((f: string) => f.includes(composition))
        : files;
      
      setPhononFiles(filteredFiles);
      
      // 自动选择第一个
      if (filteredFiles.length > 0) {
        setSelectedImage(filteredFiles[0]);
      } else {
        setSelectedImage(null);
      }
    } catch (err) {
      console.error('Failed to load phonon results:', err);
      setError(err instanceof Error ? err.message : 'Failed to load phonon results');
    } finally {
      setLoading(false);
    }
  };

  const getImageUrl = (filename: string): string => {
    // 统一使用 resolveFileUrl 处理相对路径（不包含 /api 前缀）
    return resolveFileUrl(`/images/phonon_results/${filename}`);
  };

  const handleImageLoad = () => {
    setImageLoading(false);
  };

  const handleImageError = () => {
    setImageLoading(false);
    setError('Failed to load image');
  };

  const handleImageSelect = (filename: string) => {
    setSelectedImage(filename);
    setImageLoading(true);
    setError(null);
  };

  if (loading) {
    return (
      <div className={`phonon-viewer ${className}`}>
        <div className="flex items-center justify-center p-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <span className="ml-3 text-gray-600">Loading phonon results...</span>
        </div>
      </div>
    );
  }

  if (error && phononFiles.length === 0) {
    return (
      <div className={`phonon-viewer ${className}`}>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-600">❌ {error}</p>
          <button
            onClick={loadPhononResults}
            className="mt-2 px-4 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (phononFiles.length === 0) {
    return (
      <div className={`phonon-viewer ${className}`}>
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
          <p className="text-gray-500">
            {composition 
              ? `No phonon results available for ${composition}` 
              : 'No phonon results available'}
          </p>
          <button
            onClick={loadPhononResults}
            className="mt-3 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded"
          >
            Refresh
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`phonon-viewer ${className}`}>
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm">
        {/* Header */}
        <div className="border-b border-gray-200 px-4 py-3 bg-gray-50">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-800">
              📊 Phonon Spectrum
            </h3>
            <button
              onClick={loadPhononResults}
              className="px-3 py-1 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded"
              title="Refresh phonon results"
            >
              🔄 Refresh
            </button>
          </div>
        </div>

        {/* File Selector */}
        <div className="px-4 py-3 border-b border-gray-200">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select Phonon Result:
          </label>
          <select
            value={selectedImage || ''}
            onChange={(e) => handleImageSelect(e.target.value)}
            className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            {phononFiles.map(file => (
              <option key={file} value={file}>
                {file}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-gray-500">
            {phononFiles.length} result{phononFiles.length !== 1 ? 's' : ''} available
          </p>
        </div>

        {/* Image Display */}
        {selectedImage && (
          <div className="p-4">
            <div className="relative bg-gray-50 rounded-lg overflow-hidden">
              {imageLoading && (
                <div className="absolute inset-0 flex items-center justify-center bg-gray-100 bg-opacity-75 z-10">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                </div>
              )}
              
              <img
                src={getImageUrl(selectedImage)}
                alt={selectedImage}
                className="w-full h-auto"
                onLoad={handleImageLoad}
                onError={handleImageError}
              />
              
              {error && (
                <div className="absolute inset-0 flex items-center justify-center bg-red-50 bg-opacity-90">
                  <p className="text-red-600">❌ {error}</p>
                </div>
              )}
            </div>
            
            {/* Image Info */}
            <div className="mt-3 p-3 bg-gray-50 rounded border border-gray-200">
              <p className="text-sm text-gray-700">
                <span className="font-medium">File:</span> {selectedImage}
              </p>
              {composition && (
                <p className="text-sm text-gray-700 mt-1">
                  <span className="font-medium">Composition:</span> {composition}
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default PhononViewer;

