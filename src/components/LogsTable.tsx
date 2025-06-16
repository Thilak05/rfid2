import React, { useState } from 'react';
import { FileText, Edit, Trash2, Clock, Calendar, User, CreditCard } from 'lucide-react';
import { Log, User as UserType } from '../types';
import { format, differenceInMinutes, differenceInHours } from 'date-fns';

interface LogsTableProps {
  logs: Log[];
  users: UserType[];
  onEditUser: (user: UserType) => void;
  onDeleteUser: (id: number) => void;
}

export const LogsTable: React.FC<LogsTableProps> = ({ logs, users, onEditUser, onDeleteUser }) => {
  const [currentPage, setCurrentPage] = useState(1);
  const logsPerPage = 10;

  // Calculate duration between entry and exit
  const calculateDuration = (entryTime?: string, exitTime?: string) => {
    if (!entryTime || !exitTime) return 'Active';
    
    const entry = new Date(entryTime);
    const exit = new Date(exitTime);
    const minutes = differenceInMinutes(exit, entry);
    const hours = differenceInHours(exit, entry);
    
    if (hours > 0) {
      const remainingMinutes = minutes % 60;
      return `${hours}h ${remainingMinutes}m`;
    }
    return `${minutes}m`;
  };

  // Get user details from users array
  const getUserDetails = (uniqueId: string) => {
    return users.find(user => user.unique_id === uniqueId);
  };

  // Paginate logs
  const indexOfLastLog = currentPage * logsPerPage;
  const indexOfFirstLog = indexOfLastLog - logsPerPage;
  const currentLogs = logs.slice(indexOfFirstLog, indexOfLastLog);
  const totalPages = Math.ceil(logs.length / logsPerPage);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200">
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <FileText className="w-6 h-6 text-gray-400 mr-3" />
            <h2 className="text-2xl font-bold text-gray-900">ACCESS LOGS</h2>
          </div>
          <div className="text-sm text-gray-500">
            Total: {logs.length} entries
          </div>
        </div>
        <p className="text-gray-600 mt-1">Complete access history with entry/exit tracking</p>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <div className="flex items-center">
                  <User className="w-4 h-4 mr-1" />
                  Name
                </div>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <div className="flex items-center">
                  <CreditCard className="w-4 h-4 mr-1" />
                  RFID
                </div>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <div className="flex items-center">
                  <Calendar className="w-4 h-4 mr-1" />
                  Date
                </div>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Entry Time
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Exit Time
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <div className="flex items-center">
                  <Clock className="w-4 h-4 mr-1" />
                  Duration
                </div>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {currentLogs.map((log) => {
              const userDetails = getUserDetails(log.unique_id);
              const entryDate = log.entry_time ? format(new Date(log.entry_time), 'MMM dd, yyyy') : '';
              const entryTime = log.entry_time ? format(new Date(log.entry_time), 'HH:mm:ss') : '';
              const exitTime = log.exit_time ? format(new Date(log.exit_time), 'HH:mm:ss') : '';
              const duration = calculateDuration(log.entry_time, log.exit_time);
              
              return (
                <tr key={log.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">
                      {log.user_name || log.name}
                    </div>
                    {(userDetails?.email || (log as any).user_email) && (
                      <div className="text-sm text-gray-500">
                        {userDetails?.email || (log as any).user_email}
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900 font-mono bg-gray-100 px-2 py-1 rounded text-center">
                      {log.unique_id}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {entryDate}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {entryTime ? (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        {entryTime}
                      </span>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {exitTime ? (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                        {exitTime}
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                        Inside
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      duration === 'Active' 
                        ? 'bg-blue-100 text-blue-800' 
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {duration}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    {userDetails && (
                      <div className="flex space-x-2">
                        <button
                          onClick={() => onEditUser(userDetails)}
                          className="text-blue-600 hover:text-blue-900 p-1 rounded hover:bg-blue-50 transition-colors"
                          title="Edit user"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => onDeleteUser(userDetails.id)}
                          className="text-red-600 hover:text-red-900 p-1 rounded hover:bg-red-50 transition-colors"
                          title="Delete user"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="px-6 py-4 border-t border-gray-200">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-700">
              Showing {indexOfFirstLog + 1} to {Math.min(indexOfLastLog, logs.length)} of {logs.length} entries
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                disabled={currentPage === 1}
                className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <span className="px-3 py-1 text-sm bg-blue-50 text-blue-600 border border-blue-200 rounded-md">
                {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                disabled={currentPage === totalPages}
                className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}

      {logs.length === 0 && (
        <div className="text-center py-12">
          <FileText className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-lg font-medium text-gray-900">No access logs</h3>
          <p className="mt-1 text-sm text-gray-500">Access logs will appear here when users enter or exit.</p>
        </div>
      )}
    </div>
  );
};