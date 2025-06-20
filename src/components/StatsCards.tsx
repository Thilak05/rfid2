import React from 'react';
import { Users, UserCheck, LogIn, LogOut } from 'lucide-react';
import { Stats } from '../types';

interface StatsCardsProps {
  stats: Stats;
}

export const StatsCards: React.FC<StatsCardsProps> = ({ stats }) => {
  const cards = [
    {
      title: 'Total Users',
      value: stats.total_users,
      icon: Users,
      color: 'bg-blue-500',
      bgColor: 'bg-blue-50',
      textColor: 'text-blue-600',
    },
    {
      title: 'Currently Inside',
      value: stats.inside_count,
      icon: LogIn,
      color: 'bg-green-500',
      bgColor: 'bg-green-50',
      textColor: 'text-green-600',
    },
    {
      title: 'Currently Outside',
      value: stats.outside_count,
      icon: LogOut,
      color: 'bg-orange-500',
      bgColor: 'bg-orange-50',
      textColor: 'text-orange-600',
    },
    {
      title: 'Today\'s Entries',
      value: stats.today_entries,
      icon: UserCheck,
      color: 'bg-purple-500',
      bgColor: 'bg-purple-50',
      textColor: 'text-purple-600',
    },
  ];

  return (
    <>
      {cards.map((card, index) => (
        <div
          key={index}
          className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-all duration-200 hover:scale-105"
        >
          <div className="flex items-center">
            <div className={`${card.bgColor} p-3 rounded-lg`}>
              <card.icon className={`w-6 h-6 ${card.textColor}`} />
            </div>
            <div className="ml-4 flex-1">
              <p className="text-sm font-medium text-gray-600">{card.title}</p>
              <p className="text-2xl font-bold text-gray-900">{card.value}</p>
            </div>
          </div>
        </div>
      ))}
    </>
  );
};