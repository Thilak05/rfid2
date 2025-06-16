import React from 'react';
import { Activity, LogIn, LogOut, Clock, User } from 'lucide-react';
import { Log } from '../types';
import { format } from 'date-fns';

interface ActivityLogProps {
  logs: Log[];
}

export const ActivityLog: React.FC<ActivityLogProps> = ({ logs }) => {
  const getActionIcon = (log: Log) => {
    if (log.entry_time && !log.exit_time) {
      return <LogIn className="w-4 h-4 text-green-600" />;
    } else if (log.exit_time) {
      return <LogOut className="w-4 h-4 text-red-600" />;
    }
    return <User className="w-4 h-4 text-gray-600" />;
  };

  const getActionColor = (log: Log) => {
    if (log.entry_time && !log.exit_time) {
      return 'bg-green-100';
    } else if (log.exit_time) {
      return 'bg-red-100';
    }
    return 'bg-gray-100';
  };

  const getActionText = (log: Log) => {
    if (log.entry_time && !log.exit_time) {
      return 'Entered';
    } else if (log.exit_time) {
      return 'Exited';
    }
    return 'Activity';
  };

  const getActionTime = (log: Log) => {
    if (log.exit_time) {
      return log.exit_time;
    } else if (log.entry_time) {
      return log.entry_time;
    }
    return '';
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200">
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <Activity className="w-5 h-5 text-gray-400 mr-2" />
            <h2 className="text-lg font-semibold text-gray-900">Live Activity</h2>
          </div>
          <div className="flex items-center">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse mr-2"></div>
            <span className="text-xs text-gray-500">Real-time</span>
          </div>
        </div>
      </div>

      <div className="p-6">
        <div className="space-y-4 max-h-96 overflow-y-auto">
          {logs.slice(0, 20).map((log) => (
            <div key={log.id} className="flex items-start space-x-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
              <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${getActionColor(log)}`}>
                {getActionIcon(log)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-gray-900">
                  {log.user_name || log.name}
                </div>
                <div className="text-sm text-gray-500">
                  {getActionText(log)} the building
                </div>
                <div className="flex items-center mt-1 text-xs text-gray-400">
                  <Clock className="w-3 h-3 mr-1" />
                  {getActionTime(log) && format(new Date(getActionTime(log)), 'MMM dd, HH:mm:ss')}
                </div>
                <div className="text-xs text-gray-400 font-mono">
                  RFID: {log.unique_id}
                </div>
              </div>
            </div>
          ))}
        </div>

        {logs.length === 0 && (
          <div className="text-center py-8">
            <Activity className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No recent activity</h3>
            <p className="mt-1 text-sm text-gray-500">Entry and exit logs will appear here in real-time.</p>
          </div>
        )}
      </div>
    </div>
  );
};