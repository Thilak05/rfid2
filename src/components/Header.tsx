import React from 'react';
import { Shield, Wifi } from 'lucide-react';

export const Header: React.FC = () => {
  const networkIP = window.location.hostname;
  
  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center">
            <Shield className="w-8 h-8 text-blue-600 mr-3" />
            <h1 className="text-xl font-semibold text-gray-900">RFID Access Control</h1>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="flex items-center text-sm text-gray-600">
              <Wifi className="w-4 h-4 mr-2 text-green-500" />
              <span>Connected to {networkIP}</span>
            </div>
            <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse" title="Live monitoring active"></div>
          </div>
        </div>
      </div>
    </header>
  );
};