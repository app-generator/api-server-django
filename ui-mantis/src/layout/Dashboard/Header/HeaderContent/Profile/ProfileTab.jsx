import PropTypes from 'prop-types';
import { useState, useEffect } from 'react';

// material-ui
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';

// assets
import EditOutlined from '@ant-design/icons/EditOutlined';
import ProfileOutlined from '@ant-design/icons/ProfileOutlined';
import LogoutOutlined from '@ant-design/icons/LogoutOutlined';
import UserOutlined from '@ant-design/icons/UserOutlined';
import WalletOutlined from '@ant-design/icons/WalletOutlined';

import { useNavigate } from 'react-router-dom';
import { useAuth } from 'contexts/authContext.jsx';


// ==============================|| HEADER PROFILE - PROFILE TAB ||============================== //

export default function ProfileTab({ callback }) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const { user, setUser, logout } = useAuth();

  const navigate = useNavigate();

  const handleListItemClick = (event, index, path) => {
    setSelectedIndex(index);
    callback();
    if (path) navigate(path);
  };

  const handleLogout = () => {
    logout()
    callback();
    navigate('/dashboard/default');
  };

  useEffect(() => {
    const storedUser = JSON.parse(localStorage.getItem('mantis_user'));
    if (storedUser) {
      setUser(storedUser);
    }
  }, []);

  return (
    <List component="nav" sx={{ p: 0, '& .MuiListItemIcon-root': { minWidth: 32 } }}>
      <ListItemButton
        selected={selectedIndex === 0}
        onClick={(event) => handleListItemClick(event, 0, `/user/edit-profile/${user.id}`)}
      >
        <ListItemIcon>
          <EditOutlined />
        </ListItemIcon>
        <ListItemText primary="Edit Profile" />
      </ListItemButton>

      <ListItemButton
        selected={selectedIndex === 1}
        onClick={(event) => handleListItemClick(event, 1, '/apps/profiles/account/' + user.id)}
      >
        <ListItemIcon>
          <UserOutlined />
        </ListItemIcon>
        <ListItemText primary="View Profile" />
      </ListItemButton>

      <ListItemButton
        selected={selectedIndex === 2}
        onClick={(event) => handleListItemClick(event, 2, '/apps/profiles/account/' + user.id)}
      >
        <ListItemIcon>
          <ProfileOutlined />
        </ListItemIcon>
        <ListItemText primary="Social Profile" />
      </ListItemButton>

      <ListItemButton
        selected={selectedIndex === 3}
        onClick={(event) => handleListItemClick(event, 3, '/apps/invoice/details/1')}
      >
        <ListItemIcon>
          <WalletOutlined />
        </ListItemIcon>
        <ListItemText primary="Billing" />
      </ListItemButton>

      <ListItemButton
        selected={selectedIndex === 4}
        onClick={() => handleLogout && handleLogout()}
      >
        <ListItemIcon>
          <LogoutOutlined />
        </ListItemIcon>
        <ListItemText primary="Logout" />
      </ListItemButton>
    </List>
  );
}

ProfileTab.propTypes = {
  callback: PropTypes.func
};
