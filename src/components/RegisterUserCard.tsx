import React from 'react';
import { UserPlus } from 'lucide-react';

interface RegisterUserCardProps {
  onRegister: () => void;
}

export const RegisterUserCard: React.FC<RegisterUserCardProps> = ({ onRegister }) => {
  return (
    <div className="bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl shadow-sm border border-indigo-200 p-6 hover:shadow-md transition-all duration-200 hover:scale-105 cursor-pointer"
         onClick={onRegister}>
      <div className="flex items-center">
        <div className="bg-white bg-opacity-20 p-3 rounded-lg">
          <UserPlus className="w-6 h-6 text-white" />
        </div>
        <div className="ml-4 flex-1">
          <p className="text-sm font-medium text-white opacity-90">Register</p>
          <p className="text-2xl font-bold text-white">New User</p>
        </div>
      </div>
    </div>
  );
};