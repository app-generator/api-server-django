import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { Box, TextField, Button, Typography, Grid } from '@mui/material';

const EditProfile = () => {
  const { id } = useParams(); 
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    bio: '',
    country: '',
    address: '',
    job: ''
  });
  const [loading, setLoading] = useState(true); // Loading state to handle API call status

  // Fetch user data from the API
  useEffect(() => {
    const fetchUserData = async () => {
      try {
        const response = await axios.get(`${import.meta.env.VITE_APP_PUBLIC_URL}/users/${id}`); 
        const user = response.data;
        console.log('User Data:', user);
        setFormData({
          firstName: user.firstName || '',
          lastName: user.lastName || '',
          email: user.email || '',
          bio: user.bio || '',
          country: user.country || '',
          address: user.address || '',
          job: user.job || ''
        });
      } catch (error) {
        console.error('Error fetching user data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchUserData();
  }, [id]);

  // Handle input changes
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prevData) => ({
      ...prevData,
      [name]: value
    }));
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      console.log('Updated User Data:', formData);
      const user = JSON.parse(localStorage.getItem('mantis_user'))
      console.log(user);
      

      if (user.id != id && user.role != "admin") throw new Error("Wrong user signed in")
      
        const response = await axios.put(
        `${import.meta.env.VITE_APP_PUBLIC_URL}/users/${id}`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${user.auth_token}`,
          },
        }
      );
      console.log('Profile updated', response.data);
      alert('Profile updated successfully!');
    } catch (error) {
      console.error('Error updating user data:', error);
      alert('Failed to update profile. Please try again.');
    }
  };

  if (loading) {
    return (
      <Box 
        sx={{ 
          width: '100%', 
          maxWidth: 600, 
          mx: 'auto', 
          mt: 4, 
          p: 3, 
          textAlign: 'center' 
        }}
      >
        <Typography variant="h5">Loading user data...</Typography>
      </Box>
    );
  }

  return (
    <Box 
      sx={{ 
        width: '100%', 
        maxWidth: 600, 
        mx: 'auto', 
        mt: 4, 
        p: 3, 
        borderRadius: 2, 
        boxShadow: 3, 
        backgroundColor: 'white' 
      }}
    >
      <Typography variant="h4" sx={{ mb: 3, textAlign: 'center' }}>
        Edit Profile
      </Typography>

      <form onSubmit={handleSubmit}>
        <Grid container spacing={3}>
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="First Name"
              name="firstName"
              value={formData.firstName}
              onChange={handleInputChange}
              variant="outlined"
              required
            />
          </Grid>

          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="Last Name"
              name="lastName"
              value={formData.lastName}
              onChange={handleInputChange}
              variant="outlined"
              required
            />
          </Grid>

          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Email"
              name="email"
              type="email"
              value={formData.email}
              onChange={handleInputChange}
              variant="outlined"
              required
            />
          </Grid>

          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Bio"
              name="bio"
              value={formData.bio}
              onChange={handleInputChange}
              variant="outlined"
              multiline
              rows={3}
            />
          </Grid>

          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Country"
              name="country"
              value={formData.country}
              onChange={handleInputChange}
              variant="outlined"
            />
          </Grid>

          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Address"
              name="address"
              value={formData.address}
              onChange={handleInputChange}
              variant="outlined"
            />
          </Grid>

          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Job"
              name="job"
              value={formData.job}
              onChange={handleInputChange}
              variant="outlined"
            />
          </Grid>

          <Grid item xs={12}>
            <Button 
              type="submit" 
              variant="contained" 
              color="primary" 
              fullWidth
              sx={{ mt: 2 }}
            >
              Save Changes
            </Button>
          </Grid>
        </Grid>
      </form>
    </Box>
  );
};

export default EditProfile;
