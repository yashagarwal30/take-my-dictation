import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { UserProvider } from './context/UserContext';
import ProtectedRoute from './components/ProtectedRoute';

// Pages
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import RecordingPage from './pages/RecordingPage';
import ProcessingPage from './pages/ProcessingPage';
import SummaryPage from './pages/SummaryPage';
import SubscriptionPage from './pages/SubscriptionPage';
import DashboardPage from './pages/DashboardPage';
import ProfilePage from './pages/ProfilePage';
import SubscriptionManagementPage from './pages/SubscriptionManagementPage';

function App() {
  return (
    <UserProvider>
      <Router>
        <div className="App">
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route path="/record" element={<RecordingPage />} />
            <Route path="/processing" element={<ProcessingPage />} />
            <Route path="/summary" element={<SummaryPage />} />
            <Route path="/subscribe" element={<SubscriptionPage />} />

            {/* Protected routes */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <DashboardPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/profile"
              element={
                <ProtectedRoute>
                  <ProfilePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/subscription/manage"
              element={
                <ProtectedRoute>
                  <SubscriptionManagementPage />
                </ProtectedRoute>
              }
            />
          </Routes>
        </div>
      </Router>
    </UserProvider>
  );
}

export default App;
