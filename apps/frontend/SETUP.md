# CognitoAI Engine Frontend Setup

## Prerequisites

- Node.js 18+
- npm or yarn package manager

## Installation

1. Install dependencies:
```bash
npm install
```

2. Install additional required dependencies:
```bash
npm install next-auth@beta @radix-ui/react-label @radix-ui/react-dropdown-menu tailwindcss-animate
```

3. Create environment file:
```bash
cp .env.local.example .env.local
```

4. Update the environment variables in `.env.local`:
```env
NEXTAUTH_SECRET=your-secret-key-here
NEXTAUTH_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
NODE_ENV=development
```

## Development

Start the development server:
```bash
npm run dev
```

The application will be available at http://localhost:3000

## Features Implemented

✅ **Story 8.1: Authentication & Authorization System**
- NextAuth.js integration with JWT strategy
- Role-based access control (admin, researcher, viewer, compliance_officer)
- Protected routes with middleware
- Login form with MFA support
- Session management with automatic refresh

✅ **Story 8.2: Main Application Shell & Navigation**
- Responsive sidebar navigation
- Header with search, notifications, and user menu
- Mobile-friendly hamburger menu
- Role-based navigation filtering

✅ **Story 8.3: Dashboard Home with Overview Metrics**
- Statistics cards with trend indicators
- Recent activity feed with real-time updates
- Quick actions panel with permission-based filtering
- Loading states and error handling

✅ **Story 8.4: Theme System (Dark/Light Mode)**
- System, light, and dark theme support
- Persistent theme selection
- Smooth theme transitions
- CSS custom properties for consistent theming

✅ **Story 8.5: API Integration Layer & Error Handling**
- Typed API client with authentication
- React Query integration for caching
- Comprehensive error handling
- Toast notifications for user feedback
- Error boundaries for graceful failure handling

## Project Structure

```
src/
├── app/                    # Next.js 14 App Router
│   ├── (dashboard)/       # Dashboard route group
│   ├── auth/              # Authentication pages
│   ├── api/               # API routes
│   └── layout.tsx         # Root layout with providers
├── components/            # Reusable components
│   ├── auth/              # Authentication components
│   ├── dashboard/         # Dashboard-specific components
│   ├── layout/            # Layout components
│   └── ui/                # Base UI components
├── hooks/                 # Custom React hooks
├── lib/                   # Utility libraries
├── providers/             # Context providers
└── stores/                # Zustand state stores
```

## Key Components

### Authentication
- `/D:/Projects/CognitoAI-Engine/apps/frontend/src/components/auth/login-form.tsx` - Login form with MFA
- `/D:/Projects/CognitoAI-Engine/apps/frontend/src/components/auth/protected-route.tsx` - Route protection
- `/D:/Projects/CognitoAI-Engine/apps/frontend/src/middleware.ts` - Route middleware

### Layout
- `/D:/Projects/CognitoAI-Engine/apps/frontend/src/components/layout/main-layout.tsx` - Main app layout
- `/D:/Projects/CognitoAI-Engine/apps/frontend/src/components/layout/sidebar.tsx` - Navigation sidebar
- `/D:/Projects/CognitoAI-Engine/apps/frontend/src/components/layout/header.tsx` - App header

### Dashboard
- `/D:/Projects/CognitoAI-Engine/apps/frontend/src/app/(dashboard)/page.tsx` - Dashboard home page
- `/D:/Projects/CognitoAI-Engine/apps/frontend/src/components/dashboard/stats-cards.tsx` - Metrics display
- `/D:/Projects/CognitoAI-Engine/apps/frontend/src/components/dashboard/recent-activity.tsx` - Activity feed

### Theme System
- `/D:/Projects/CognitoAI-Engine/apps/frontend/src/providers/theme-provider.tsx` - Theme context
- `/D:/Projects/CognitoAI-Engine/apps/frontend/src/components/theme-toggle.tsx` - Theme switcher

### API Integration
- `/D:/Projects/CognitoAI-Engine/apps/frontend/src/lib/api.ts` - API client
- `/D:/Projects/CognitoAI-Engine/apps/frontend/src/hooks/use-api.ts` - API hooks with React Query

## Next Steps

To continue development, consider implementing:

1. **Additional Pages**: Requests, Analysis, Reports, Users, Settings
2. **Data Tables**: Using @tanstack/react-table for complex data display
3. **Forms**: Request creation, user management forms
4. **Charts**: Data visualization for analysis results
5. **File Upload**: Document upload with drag-and-drop
6. **Real-time Updates**: WebSocket integration for live updates
7. **Testing**: Unit and integration tests
8. **Accessibility**: ARIA labels and keyboard navigation

## Production Deployment

1. Build the application:
```bash
npm run build
```

2. Start production server:
```bash
npm start
```

3. Configure environment variables for production
4. Set up SSL certificates
5. Configure database connections
6. Set up monitoring and logging