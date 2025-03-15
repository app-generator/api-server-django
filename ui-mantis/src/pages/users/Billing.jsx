// src/BillingDetail.js
import React, { useEffect, useState } from 'react';
import { Paper, Typography, Grid } from '@mui/material';
import { useAuth } from 'contexts/authContext.jsx';
const BillingDetail = () => {
    const [billingData, setBillingData] = useState(null);
    const { user } = useAuth();

    useEffect(() => {
        const fetchBillingData = async () => {
            const response = await fetch(`${import.meta.env.VITE_APP_PUBLIC_URL}/users/${user.id}`);
            const data = await response.json();
            console.log(data);


            setBillingData(data);
        };
        fetchBillingData();
    }, []);

    return (
        <Paper elevation={3} style={{ padding: '20px', marginTop: '20px' }}>
            <Typography variant="h5" gutterBottom>
                Billing Details
            </Typography>
            <Grid container spacing={2}>
                <Grid item xs={12}>
                    <Typography variant="h6">
                        Name: {billingData?.firstName} {billingData?.lastName}
                    </Typography>
                </Grid>
                <Grid item xs={12}>
                    <Typography variant="body1">
                        Email: {billingData?.email}
                    </Typography>
                </Grid>
                <Grid item xs={12}>
                    <Typography variant="body1">
                        Address: {billingData?.address}, {billingData?.country}
                    </Typography>
                </Grid>
                <Grid item xs={12}>
                    <Typography variant="body1">
                        Job: {billingData?.job}
                    </Typography>
                </Grid>
                <Grid item xs={12}>
                    <Typography variant="body1">
                        Bio: {billingData?.bio}
                    </Typography>
                </Grid>
            </Grid>
        </Paper>
    );
};

export default BillingDetail;