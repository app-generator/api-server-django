import useMediaQuery from '@mui/material/useMediaQuery';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';

// assets
import Google from 'assets/images/icons/google.svg';
import Twitter from 'assets/images/icons/twitter.svg';
import Facebook from 'assets/images/icons/facebook.svg';
import Github from 'assets/images/icons/github.svg'

import axios from 'axios';

// ==============================|| FIREBASE - SOCIAL BUTTON ||============================== //

export default function FirebaseSocial() {
  const downSM = useMediaQuery((theme) => theme.breakpoints.down('sm'));

  // @ts-ignore
  const googleHandler = async () => {
    // login || singup
  };

  const twitterHandler = async () => {
    // login || singup
  };

  const githubHandler = async () => {
    try {
      window.location.href = `${import.meta.env.VITE_APP_PUBLIC_URL}/auth/login`;
    } catch (error) {
      console.error('GitHub login failed:', error);
    }
  };

  return (
    <Stack
      direction="row"
      spacing={{ xs: 1, sm: 2 }}
      justifyContent={{ xs: 'space-around', sm: 'space-between' }}
      sx={{ '& .MuiButton-startIcon': { mr: { xs: 0, sm: 1 }, ml: { xs: 0, sm: -0.5 } } }}
    >
      {/* <Button
        variant="outlined"
        color="secondary"
        fullWidth={!downSM}
        startIcon={<img src={Google} alt="Google" />}
        onClick={googleHandler}
      >
        {!downSM && 'Google'}
      </Button>
      <Button
        variant="outlined"
        color="secondary"
        fullWidth={!downSM}
        startIcon={<img src={Twitter} alt="Twitter" />}
        onClick={twitterHandler}
      >
        {!downSM && 'Twitter'}
      </Button> */}
      <Button
        variant="outlined"
        color="secondary"
        fullWidth={!downSM}
        startIcon={<img src={Github} alt="Github" />}
        onClick={githubHandler}
      >
        {!downSM && 'GitHub'}
      </Button>
    </Stack>
  );
}
