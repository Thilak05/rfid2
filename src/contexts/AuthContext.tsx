import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface User {
  id: string;
  username: string;
}

interface AuthContextType {
  user: User | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('rfid_token');
    const userData = localStorage.getItem('rfid_user');
    
    if (token && userData) {
      try {
        setUser(JSON.parse(userData));
      } catch (error) {
        localStorage.removeItem('rfid_token');
        localStorage.removeItem('rfid_user');
      }
    }
    setLoading(false);
  }, []);

  const login = async (username: string, password: string) => {
    // Fixed credentials for demo
    if (username === 'admin' && password === 'admin123') {
      const userData = { id: '1', username: 'admin' };
      const token = 'demo_jwt_token_' + Date.now();
      
      localStorage.setItem('rfid_token', token);
      localStorage.setItem('rfid_user', JSON.stringify(userData));
      setUser(userData);
    } else {
      throw new Error('Invalid credentials');
    }
  };

  const logout = () => {
    localStorage.removeItem('rfid_token');
    localStorage.removeItem('rfid_user');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};