import { useState, useEffect } from 'react';
import DashboardLayout from '../components/DashboardLayout';
import { fetchParameters, updateParameters } from '../api/dashboard';

export default function Parameters() {
  const [parameters, setParameters] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [formValues, setFormValues] = useState({});
  
  useEffect(() => {
    const loadParameters = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const data = await fetchParameters();
        setParameters(data);
        
        // 폼 초기값 설정
        const initialValues = {};
        for (const category in data) {
          for (const param of data[category]) {
            initialValues[param.id] = param.value;
          }
        }
        setFormValues(initialValues);
      } catch (err) {
        console.error('Failed to load parameters:', err);
        setError('Failed to load strategy parameters. Please try again later.');
      } finally {
        setLoading(false);
      }
    };
    
    loadParameters();
  }, []);
  
  const handleInputChange = (paramId, value) => {
    setFormValues({
      ...formValues,
      [paramId]: value
    });
  };
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      setSaving(true);
      setError(null);
      setSuccess(null);
      
      // 파라미터 업데이트 요청
      await updateParameters(formValues);
      
      setSuccess('Parameters updated successfully');
      
      // 3초 후 성공 메시지 숨기기
      setTimeout(() => {
        setSuccess(null);
      }, 3000);
    } catch (err) {
      console.error('Failed to update parameters:', err);
      setError('Failed to update parameters. Please try again.');
    } finally {
      setSaving(false);
    }
  };
  
  if (loading) {
    return (
      <DashboardLayout>
        <h1 className="text-2xl font-bold mb-6">Strategy Parameters</h1>
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      </DashboardLayout>
    );
  }
  
  return (
    <DashboardLayout>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Strategy Parameters</h1>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-gray-200 dark:bg-slate-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-300 dark:hover:bg-slate-600 focus:outline-none"
        >
          Refresh
        </button>
      </div>
      
      {error && (
        <div className="mb-6 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 p-4 rounded-md">
          {error}
        </div>
      )}
      
      {success && (
        <div className="mb-6 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-200 p-4 rounded-md">
          {success}
        </div>
      )}
      
      <form onSubmit={handleSubmit}>
        {parameters && Object.keys(parameters).map((category) => (
          <div key={category} className="card mb-6">
            <h2 className="text-xl font-bold mb-4 capitalize">{category.replace('_', ' ')}</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {parameters[category].map((param) => (
                <div key={param.id} className="bg-gray-50 dark:bg-slate-700 p-4 rounded-lg">
                  <div className="flex justify-between items-start mb-2">
                    <label htmlFor={param.id} className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      {param.name}
                    </label>
                    {param.description && (
                      <div className="group relative">
                        <button
                          type="button"
                          className="text-gray-400 hover:text-gray-500 dark:text-gray-500 dark:hover:text-gray-400"
                        >
                          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                        </button>
                        <div className="absolute z-10 w-64 p-2 bg-white dark:bg-slate-800 rounded-md shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-opacity duration-300 text-xs text-gray-700 dark:text-gray-300 -top-2 transform -translate-y-full left-1/2 -translate-x-1/2">
                          {param.description}
                        </div>
                      </div>
                    )}
                  </div>
                  
                  {param.type === 'number' && (
                    <div className="mt-1 relative rounded-md shadow-sm">
                      <input
                        type="number"
                        id={param.id}
                        name={param.id}
                        value={formValues[param.id] || ''}
                        onChange={(e) => handleInputChange(param.id, parseFloat(e.target.value))}
                        min={param.min}
                        max={param.max}
                        step={param.step || 'any'}
                        className="block w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary dark:bg-slate-800 dark:text-white"
                      />
                      {param.unit && (
                        <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                          <span className="text-gray-500 dark:text-gray-400 sm:text-sm">{param.unit}</span>
                        </div>
                      )}
                    </div>
                  )}
                  
                  {param.type === 'boolean' && (
                    <div className="mt-1">
                      <label className="inline-flex items-center">
                        <input
                          type="checkbox"
                          id={param.id}
                          name={param.id}
                          checked={formValues[param.id] || false}
                          onChange={(e) => handleInputChange(param.id, e.target.checked)}
                          className="rounded border-gray-300 text-primary focus:ring-primary dark:border-slate-600 dark:bg-slate-800"
                        />
                        <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Enabled</span>
                      </label>
                    </div>
                  )}
                  
                  {param.type === 'select' && (
                    <div className="mt-1">
                      <select
                        id={param.id}
                        name={param.id}
                        value={formValues[param.id] || ''}
                        onChange={(e) => handleInputChange(param.id, e.target.value)}
                        className="block w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary dark:bg-slate-800 dark:text-white"
                      >
                        {param.options.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
                  
                  {param.type === 'string' && (
                    <div className="mt-1">
                      <input
                        type="text"
                        id={param.id}
                        name={param.id}
                        value={formValues[param.id] || ''}
                        onChange={(e) => handleInputChange(param.id, e.target.value)}
                        className="block w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary dark:bg-slate-800 dark:text-white"
                      />
                    </div>
                  )}
                  
                  {param.default !== undefined && (
                    <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      Default: {typeof param.default === 'boolean' ? (param.default ? 'Enabled' : 'Disabled') : param.default}
                      {param.unit && ` ${param.unit}`}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
        
        <div className="flex justify-end space-x-3 mt-6">
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="px-4 py-2 border border-gray-300 dark:border-slate-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-slate-700 hover:bg-gray-50 dark:hover:bg-slate-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving}
            className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </DashboardLayout>
  );
}
