import { lazy } from 'react';

// project import
import Loadable from 'components/Loadable';
import Dashboard from 'layout/Dashboard';
import EditProfile from 'pages/users/EditProfile';
import BillingPage from 'pages/users/Billing';
import ProfileDetail from 'pages/users/Detail';

const Color = Loadable(lazy(() => import('pages/component-overview/color')));
const Typography = Loadable(lazy(() => import('pages/component-overview/typography')));
const Shadow = Loadable(lazy(() => import('pages/component-overview/shadows')));
const DashboardDefault = Loadable(lazy(() => import('pages/dashboard/index')));

// render - sample page
const SamplePage = Loadable(lazy(() => import('pages/extra-pages/sample-page')));
const UserManagement = Loadable(lazy(() => import('pages/users/UserManagement')));

// ==============================|| MAIN ROUTING ||============================== //

const MainRoutes = {
  path: '/',
  element: <Dashboard />,
  children: [
    {
      path: '/',
      element: <DashboardDefault />
    },
    {
      path: 'color',
      element: <Color />
    },
    {
      path: 'dashboard',
      children: [
        {
          path: 'default',
          element: <DashboardDefault />
        }
      ]
    },
    {
      path: 'sample-page',
      element: <SamplePage />
    },
    {
      path: 'shadow',
      element: <Shadow />
    },
    {
      path: 'typography',
      element: <Typography />
    },
    {
      path: 'usermanagement',
      element: <UserManagement />
    },
    {
      path: 'user/edit-profile/:id',
      element: <EditProfile />
    },
    {
      path: 'apps/invoice/details/1',
      element: <BillingPage />
    },
    {
      path: 'apps/profiles/account/:id',
      element: <ProfileDetail />
    }
  ]
};

export default MainRoutes;
