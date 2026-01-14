# Take My Dictation - Frontend

React-based web interface for Take My Dictation voice recording and transcription app.

## Quick Start

### Prerequisites
- Node.js 16+ and npm
- Backend server running on http://localhost:8000

### Installation

```bash
cd frontend
npm install
```

### Configuration

Create a `.env` file:

```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_STRIPE_PUBLISHABLE_KEY=pk_test_your_key_here
```

### Run Development Server

```bash
npm start
```

The app will open at http://localhost:3000

## Available Scripts

- `npm start` - Run development server
- `npm test` - Run tests
- `npm run build` - Build for production
- `npm run eject` - Eject from Create React App (one-way operation)

## Features

- **Audio Recording**: Record audio with real-time timer and waveform
- **Transcription**: Automatic speech-to-text processing
- **AI Summaries**: Generate summaries in multiple formats (Meeting Notes, Product Spec, MoM, Quick Summary)
- **Dashboard**: View and manage saved recordings
- **Responsive Design**: Works on desktop and mobile

## Pages

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | LandingPage | Homepage with hero section |
| `/record` | RecordingPage | Audio recording interface |
| `/processing` | ProcessingPage | Processing status |
| `/summary` | SummaryPage | Transcription and summary display |
| `/dashboard` | DashboardPage | Saved recordings (protected) |
| `/subscribe` | SubscriptionPage | Pricing plans |

## Project Structure

```
frontend/
├── src/
│   ├── components/         # Reusable components
│   │   ├── Navbar.js
│   │   ├── Footer.js
│   │   ├── AudioRecorder.js
│   │   └── AudioWaveform.js
│   ├── pages/             # Page components
│   │   ├── LandingPage.js
│   │   ├── RecordingPage.js
│   │   ├── ProcessingPage.js
│   │   ├── SummaryPage.js
│   │   ├── DashboardPage.js
│   │   └── SubscriptionPage.js
│   ├── context/           # State management
│   │   └── UserContext.js
│   ├── utils/             # Utilities
│   │   └── api.js
│   ├── App.js             # Main app component
│   └── index.js           # Entry point
├── public/                # Static assets
├── .env                   # Environment variables
├── tailwind.config.js     # Tailwind configuration
└── package.json           # Dependencies
```

## Tech Stack

- **React 18**: UI framework
- **React Router v6**: Client-side routing
- **Tailwind CSS**: Utility-first styling
- **Axios**: HTTP client
- **React Context API**: State management

## API Integration

The frontend connects to the FastAPI backend using the `api.js` service layer. All API calls are configured through the `REACT_APP_API_URL` environment variable.

## Development

### Customization

**Change API URL:**
Edit `.env`:
```env
REACT_APP_API_URL=http://your-backend-url
```

**Change Colors:**
Edit `tailwind.config.js`:
```javascript
colors: {
  primary: '#6366f1',
  secondary: '#8b5cf6',
  accent: '#10b981',
}
```

**Change Recording Time Limit:**
Edit `src/pages/RecordingPage.js`:
```javascript
<AudioRecorder maxDuration={600} /> // 600 seconds = 10 minutes
```

## Build for Production

```bash
npm run build
```

This creates an optimized production build in the `build/` directory.

## Troubleshooting

### CORS Errors
Ensure the backend has CORS configured to allow http://localhost:3000

### Recording Not Working
- Check microphone permissions
- Use Chrome, Firefox, or Edge (MediaRecorder API support)
- HTTPS required in production

### Blank Page
- Check browser console (F12) for errors
- Verify backend is running and accessible
- Check `.env` file for correct API URL

## Learn More

- [React Documentation](https://react.dev)
- [Create React App Documentation](https://create-react-app.dev)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
