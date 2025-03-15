import { UserOutlined } from "@ant-design/icons";

const icons = {
    UserOutlined,
}

const users = {
    id: 'users',
    title: 'Users Mangement',
    type: 'group',
    children: [
        {
            id: 'users/management',
            title: 'Users',
            type: 'item',
            url: '/usermanagement',
            icon: icons.UserOutlined,
            breadcrumbs: false
        },
    ]
};

export default users;