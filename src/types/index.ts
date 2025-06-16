export interface User {
  id: number;
  name: string;
  unique_id: string;
  email?: string;
  phone?: string;
  created_at: string;
  status: 'active' | 'inactive';
}

export interface Log {
  id: number;
  name: string;
  unique_id: string;
  entry_time?: string;
  exit_time?: string;
  status: string;
  user_name: string;
}

export interface Stats {
  total_users: number;
  inside_count: number;
  outside_count: number;
  today_entries: number;
  today_exits: number;
}