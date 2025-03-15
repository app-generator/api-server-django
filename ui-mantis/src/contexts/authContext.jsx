// create context for authentication
import { createContext, useContext, useState } from 'react';

export const AuthContext = createContext();

export const useAuth = () => {
    return useContext(AuthContext);
};

export const AuthContextProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    
    const logout = () => {
        setUser(null)
        localStorage.removeItem('mantis_user');
    };

    return <AuthContext.Provider value={{ user, setUser,logout }}>{children}</AuthContext.Provider>;
};

