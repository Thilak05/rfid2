import React, { useState, useEffect } from 'react';
import { X, User, Mail, Phone, CreditCard, Loader, CheckCircle, AlertCircle, Wifi } from 'lucide-react';
import { User as UserType } from '../types';
import { rfidAPI } from '../services/api';

interface UserModalProps {
  user: UserType | null;
  onSave: (user: Omit<UserType, 'id' | 'created_at'>) => Promise<void>;
  onClose: () => void;
}

export const UserModal: React.FC<UserModalProps> = ({ user, onSave, onClose }) => {
  const [formData, setFormData] = useState({
    name: '',
    unique_id: '',
    email: '',
    phone: '',
    status: 'active' as 'active' | 'inactive',
  });
  const [isScanning, setIsScanning] = useState(false);
  const [scanStatus, setScanStatus] = useState<'idle' | 'success' | 'error' | 'timeout'>('idle');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [scanMessage, setScanMessage] = useState('');

  useEffect(() => {
    if (user) {
      setFormData({
        name: user.name,
        unique_id: user.unique_id,
        email: user.email || '',
        phone: user.phone || '',
        status: user.status,
      });
    }
  }, [user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');

    try {
      await onSave(formData);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to save user');
    } finally {
      setSaving(false);
    }
  };

  const handleScanRFID = async () => {
    setIsScanning(true);
    setScanStatus('idle');
    setError('');
    setScanMessage('Please scan your RFID card now...');

    try {
      const result = await rfidAPI.read();
      
      if (result.status === 'success' && result.rfid_id) {
        setFormData({ ...formData, unique_id: result.rfid_id });
        setScanStatus('success');
        setScanMessage(`RFID captured: ${result.rfid_id}`);
      } else if (result.status === 'timeout') {
        setScanStatus('timeout');
        setScanMessage('Scan timeout. Please try again.');
      } else {
        setScanStatus('error');
        setScanMessage(result.message || 'Failed to scan RFID');
        setError(result.message);
      }
    } catch (err: any) {
      setScanStatus('error');
      const errorMsg = err.response?.data?.message || 'Failed to read RFID';
      setScanMessage(errorMsg);
      setError(errorMsg);
    } finally {
      setIsScanning(false);
    }
  };

  const generateRFID = () => {
    const rfid = Math.random().toString(16).substr(2, 10).toUpperCase();
    setFormData({ ...formData, unique_id: rfid });
    setScanStatus('idle');
    setScanMessage('');
  };

  const getScanButtonColor = () => {
    if (isScanning) return 'bg-yellow-600 hover:bg-yellow-700';
    if (scanStatus === 'success') return 'bg-green-600 hover:bg-green-700';
    if (scanStatus === 'error') return 'bg-red-600 hover:bg-red-700';
    return 'bg-blue-600 hover:bg-blue-700';
  };

  const getScanButtonIcon = () => {
    if (isScanning) return <Loader className="w-4 h-4 mr-2 animate-spin" />;
    if (scanStatus === 'success') return <CheckCircle className="w-4 h-4 mr-2" />;
    if (scanStatus === 'error') return <AlertCircle className="w-4 h-4 mr-2" />;
    return <Wifi className="w-4 h-4 mr-2" />;
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            {user ? 'Edit User' : 'Register New User'}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 p-1 rounded hover:bg-gray-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Full Name *
            </label>
            <div className="relative">
              <User className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
                placeholder="Enter full name"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              RFID ID *
            </label>
            <div className="space-y-3">
              <div className="relative">
                <CreditCard className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  value={formData.unique_id}
                  onChange={(e) => setFormData({ ...formData, unique_id: e.target.value })}
                  className="w-full pl-10 pr-12 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors font-mono text-sm"
                  placeholder="Scan or enter RFID ID"
                  required
                />
                {scanStatus === 'success' && (
                  <CheckCircle className="absolute right-3 top-3 w-4 h-4 text-green-500" />
                )}
                {scanStatus === 'error' && (
                  <AlertCircle className="absolute right-3 top-3 w-4 h-4 text-red-500" />
                )}
              </div>
              
              <div className="flex space-x-2">
                <button
                  type="button"
                  onClick={handleScanRFID}
                  disabled={isScanning}
                  className={`flex-1 px-4 py-2 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center ${getScanButtonColor()}`}
                >
                  {getScanButtonIcon()}
                  {isScanning ? 'Scanning...' : 'Scan RFID'}
                </button>
                <button
                  type="button"
                  onClick={generateRFID}
                  className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                >
                  Generate
                </button>
              </div>

              {scanMessage && (
                <div className={`text-sm p-3 rounded-lg ${
                  scanStatus === 'success' ? 'bg-green-50 text-green-700' :
                  scanStatus === 'error' ? 'bg-red-50 text-red-700' :
                  scanStatus === 'timeout' ? 'bg-yellow-50 text-yellow-700' :
                  'bg-blue-50 text-blue-700'
                }`}>
                  {scanMessage}
                </div>
              )}

              {isScanning && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-center">
                    <Loader className="w-5 h-5 text-blue-600 animate-spin mr-3" />
                    <div>
                      <p className="text-sm font-medium text-blue-800">Scanning for RFID...</p>
                      <p className="text-xs text-blue-600">Please place your RFID card near the reader</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Email Address
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
                placeholder="Enter email address"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Phone Number
            </label>
            <div className="relative">
              <Phone className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
              <input
                type="tel"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
                placeholder="Enter phone number"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Status
            </label>
            <select
              value={formData.status}
              onChange={(e) => setFormData({ ...formData, status: e.target.value as 'active' | 'inactive' })}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
            >
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>

          {error && (
            <div className="text-red-600 text-sm bg-red-50 py-3 px-4 rounded-lg border border-red-200">
              <div className="flex items-center">
                <AlertCircle className="w-4 h-4 mr-2" />
                {error}
              </div>
            </div>
          )}

          <div className="flex space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || isScanning}
              className="flex-1 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
            >
              {saving ? (
                <>
                  <Loader className="w-4 h-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  {user ? 'Update' : 'Register'} User
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};