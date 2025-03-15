// material-ui
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';

// project import
import NavGroup from './NavGroup';
import menuItem from 'menu-items';
import { useEffect, useState } from 'react';
import axios from 'axios';
import { useAuth } from 'contexts/authContext.jsx';

// ==============================|| DRAWER CONTENT - NAVIGATION ||============================== //

export default function Navigation() {
 const {user} = useAuth()

  console.log(user);
  

  const navGroups = menuItem.items.filter(item => {
    if (item.id === 'authentication' && user !== null) {
      return
    }

    return item
  }).map((item) => {
    switch (item.type) {
      case 'group':
        return <NavGroup key={item.id} item={item} />;
      default:
        return (
          <Typography key={item.id} variant="h6" color="error" align="center">
            Fix - Navigation Group
          </Typography>
        );
    }
  });

  return <Box sx={{ pt: 2 }}>{navGroups}</Box>;
}
