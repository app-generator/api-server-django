// src/ProfileDetail.js
import React, { useEffect, useState } from 'react';
import { Paper, Typography, Grid } from '@mui/material';
import { useParams } from 'react-router';
import { useAuth } from 'contexts/authContext';

const ProfileDetail = () => {
    const { id } = useParams();
    const { user } = useAuth();
    const [profileData, setProfileData] = useState(null);


    useEffect(() => {
        const fetchProfileData = async () => {
            const response = await fetch(`${import.meta.env.VITE_APP_PUBLIC_URL}/users/${id}`);
            const data = await response.json();
            setProfileData(data);
        };
        fetchProfileData();
    }, []);


    return (
        <Paper elevation={3} style={{ padding: '20px', marginTop: '20px' }}>
            <Typography variant="h5" gutterBottom>
                Profile Details
            </Typography>
            <Grid container spacing={2}>
                <Grid item xs={12} sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
                    <img
                        src={profileData?.picture}
                        alt="Profile Avatar"
                        style={{
                            width: '150px',
                            height: '150px',
                            borderRadius: '50%',
                            border: '3px solid #f0f0f0'
                        }}
                    />
                </Grid>
                <Grid item xs={12}>
                    <Typography variant="h6">
                        Name: {profileData?.firstName} {profileData?.lastName}
                    </Typography>
                </Grid>
                <Grid item xs={12}>
                    <Typography variant="body1">
                        Email: {profileData?.email}
                    </Typography>
                </Grid>
                <Grid item xs={12}>
                    <Typography variant="body1">
                        Job: {profileData?.job}
                    </Typography>
                </Grid>
                <Grid item xs={12}>
                    <Typography variant="body1">
                        Bio: {profileData?.bio}
                    </Typography>
                </Grid>
                <Grid item xs={12}>
                    <Typography variant="body1">
                        Country: {profileData?.country}
                    </Typography>
                </Grid>
                <Grid item xs={12}>
                    <Typography variant="body1">
                        Address: {profileData?.address}
                    </Typography>
                </Grid>
            </Grid>
        </Paper>
    );
};

export default ProfileDetail;