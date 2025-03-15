import React, { useState, useEffect } from 'react';
import {
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Pagination,
  OutlinedInput,
  Stack
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { SearchOutlined } from '@ant-design/icons';
import { useAuth } from 'contexts/authContext.jsx';

const PAGE_SIZE = 5;
const UserManagement = () => {
  const [users, setUsers] = useState([]);
  const [totalUsers, setTotalUsers] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);

  const [searchValue, setSearchValue] = useState('');
  const navigate = useNavigate();
  const { setUser, user: loggedInUser } = useAuth();

  const handlePageChange = (event, page) => {
    setCurrentPage(page);
  };

  const fetchData = async (page, search) => {
    try {


      const response = await axios.get(`${import.meta.env.VITE_APP_PUBLIC_URL}/users?page=${page}&size=${PAGE_SIZE}&search=${search}`, {});

      setUsers(response.data.data);
      setTotalUsers(response.data.meta.totalItems);

    } catch (error) {
      console.error('Error fetching profile data:', error);
    }
  };

  useEffect(() => {
    fetchData(currentPage, searchValue);
  }, [currentPage, loggedInUser]);


  useEffect(() => {
    const checkUser = async () => {
      const urlParams = new URLSearchParams(window.location.search);
      let authUser = urlParams.get('user');

      if (authUser) {
        localStorage.setItem('mantis_user', authUser);
        window.history.replaceState({}, document.title, window.location.pathname);
      }

      authUser = JSON.parse(localStorage.getItem('mantis_user'));
      setUser(authUser)

    }

    checkUser();
  }, []);

  const handleEditUser = (userId) => {
    navigate(`/user/edit-profile/${userId}`);
  };

  const handleDeleteUser = async (userId) => {
    try {
      const response = await axios.delete(`${import.meta.env.VITE_APP_PUBLIC_URL}/users/${userId}`, {
        headers: {
          Authorization: `Bearer ${user.auth_token}`
        }
      });

      if (response.status === 200) {
        alert('User deleted successfully');
        fetchData(currentPage, searchValue);
      }
    } catch (error) {
      console.error('Error deleting user:', error);
    }
  };


  return (
    <Box sx={{ width: '100%', overflowX: 'auto' }}>
      <h1>User Management</h1>
      <Stack direction="row" spacing={2} my={3}>
        <OutlinedInput
          placeholder="Email / Name"
          startAdornment={<SearchOutlined />}
          value={searchValue}
          onChange={(e) => setSearchValue(e.target.value)}
        />
        <Button variant="contained" color="primary" onClick={() => fetchData(1, searchValue)}>
          Search
        </Button>
      </Stack>
      <TableContainer
        sx={{
          width: '100%',
          overflowX: 'auto',
          position: 'relative',
          display: 'block',
          maxWidth: '100%',
          '& td, & th': { whiteSpace: 'nowrap' }
        }}
      >
        <Table aria-labelledby="tableTitle">
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>First Name</TableCell>
              <TableCell>Last Name</TableCell>
              <TableCell>Email</TableCell>
              <TableCell>Bio</TableCell>
              <TableCell>Country</TableCell>
              <TableCell>Address</TableCell>
              <TableCell>Job</TableCell>
              <TableCell align="center">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {users.map((user) => {
              const isUserRole = loggedInUser?.role === 'user';
              const isCurrentUser = loggedInUser?.id === user.id;
              const isButtonEnabled = isUserRole ? isCurrentUser : true;

              return (
                <TableRow key={user.id} hover sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                  <TableCell>{user.id}</TableCell>
                  <TableCell>{user.firstName}</TableCell>
                  <TableCell>{user.lastName}</TableCell>
                  <TableCell>{user.email}</TableCell>
                  <TableCell>{user.bio}</TableCell>
                  <TableCell>{user.country}</TableCell>
                  <TableCell>{user.address}</TableCell>
                  <TableCell>{user.job}</TableCell>
                  <TableCell align="center">
                    <>
                      <Button
                        variant="contained"
                        color="info"
                        size="small"
                        onClick={() => navigate(`/apps/profiles/account/${user.id}`)}
                        sx={{ marginRight: 1 }}
                      >
                        Detail
                      </Button>

                      <Button
                        variant="contained"
                        color={isButtonEnabled ? 'primary' : 'secondary'}
                        size="small"
                        onClick={() => handleEditUser(user.id)}
                        disabled={(loggedInUser?.role !== 'admin' || !isButtonEnabled) && !isCurrentUser}
                        sx={{
                          backgroundColor: isButtonEnabled ? 'primary.main' : 'grey.400',
                          '&:hover': { backgroundColor: isButtonEnabled ? 'primary.dark' : 'grey.400' }
                        }}
                      >
                        Edit
                      </Button>


                      <Button
                        variant="contained"
                        color="error"
                        size="small"
                        onClick={() => handleDeleteUser(user.id)}
                        disabled={(loggedInUser?.role !== 'admin' || !isButtonEnabled) && !isCurrentUser}
                        sx={{
                          marginLeft: 1,
                          backgroundColor: isButtonEnabled ? 'error.main' : 'grey.400',
                          '&:hover': { backgroundColor: isButtonEnabled ? 'error.dark' : 'grey.400' }
                        }}
                      >
                        Delete
                      </Button>

                    </>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
      <Pagination
        count={Math.ceil(totalUsers / PAGE_SIZE)}
        variant="outlined"
        shape="rounded"
        sx={{ marginTop: 2 }}
        page={currentPage}
        onChange={handlePageChange}
      />
    </Box>
  );
};

export default UserManagement;
