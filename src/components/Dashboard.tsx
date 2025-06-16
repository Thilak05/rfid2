import React, { useState, useEffect } from 'react';
import { Header } from './Header';
import { StatsCards } from './StatsCards';
import { RegisterUserCard } from './RegisterUserCard';
import { LogsTable } from './LogsTable';
import { ActivityLog } from './ActivityLog';
import { UserModal } from './UserModal';
import { UsersTable } from './UsersTable';
import { User, Log, Stats } from '../types';
import { usersAPI, logsAPI, statsAPI } from '../services/api';

export const Dashboard: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [logs, setLogs] = useState<Log[]>([]);
  const [stats, setStats] = useState<Stats>({
    total_users: 0,
    inside_count: 0,
    outside_count: 0,
    today_entries: 0,
    today_exits: 0
  });
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [showUsersTable, setShowUsersTable] = useState(false);

  const fetchData = async () => {
    try {
      const [usersData, logsData, statsData] = await Promise.all([
        usersAPI.getAll(),
        logsAPI.getAll(),
        statsAPI.get()
      ]);
      setUsers(usersData);
      setLogs(logsData);
      setStats(statsData);
      console.log('Fetched users:', usersData); // Debug log
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Refresh data every 5 seconds for real-time updates
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleAddUser = () => {
    setEditingUser(null);
    setIsModalOpen(true);
  };

  const handleEditUser = (user: User) => {
    setEditingUser(user);
    setIsModalOpen(true);
  };

  const handleDeleteUser = async (id: number) => {
    if (window.confirm('Are you sure you want to delete this user?')) {
      try {
        await usersAPI.delete(id);
        await fetchData();
      } catch (error) {
        console.error('Failed to delete user:', error);
        alert('Failed to delete user');
      }
    }
  };

  const handleSaveUser = async (userData: Omit<User, 'id' | 'created_at'>) => {
    try {
      if (editingUser) {
        await usersAPI.update(editingUser.id, userData);
      } else {
        await usersAPI.create(userData);
      }
      setIsModalOpen(false);
      await fetchData();
    } catch (error) {
      console.error('Failed to save user:', error);
      throw error;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <Header />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">RFID Access Control System</h1>
          <p className="text-gray-600 mt-2">Real-time monitoring and user management</p>
        </div>

        {/* Stats Cards Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
          <StatsCards stats={stats} />
          <RegisterUserCard onRegister={handleAddUser} />
        </div>

        {/* View Registered Users Button */}
        <div className="mb-6">
          <button
            onClick={() => setShowUsersTable(!showUsersTable)}
            className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 transition-colors"
          >
            {showUsersTable ? 'Hide' : 'View'} Registered Users ({users.length})
          </button>
        </div>

        {/* Registered Users Table (Collapsible) */}
        {showUsersTable && (
          <div className="mb-8">
            <UsersTable
              users={users}
              onAdd={handleAddUser}
              onEdit={handleEditUser}
              onDelete={handleDeleteUser}
            />
          </div>
        )}

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
          {/* Logs Table - Takes 2 columns */}
          <div className="xl:col-span-2">
            <LogsTable 
              logs={logs} 
              users={users}
              onEditUser={handleEditUser}
              onDeleteUser={handleDeleteUser}
            />
          </div>
          
          {/* Activity Log - Takes 1 column */}
          <div className="xl:col-span-1">
            <ActivityLog logs={logs} />
          </div>
        </div>
      </main>

      {isModalOpen && (
        <UserModal
          user={editingUser}
          onSave={handleSaveUser}
          onClose={() => setIsModalOpen(false)}
        />
      )}
    </div>
  );
};