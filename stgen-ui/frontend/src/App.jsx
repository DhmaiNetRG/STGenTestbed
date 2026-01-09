import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material';

// Pages
import Dashboard from './pages/Dashboard';
import NewExperiment from './pages/NewExperiment';
import ExperimentDetail from './pages/ExperimentDetail';
import Results from './pages/Results';

// API client
import api from './api';

function App() {
  const [darkMode, setDarkMode] = useState(true);
  
  const theme = createTheme({
    palette: {
      mode: darkMode ? 'dark' : 'light',
      primary: {
        main: '#2196f3',
      },
      secondary: {
        main: '#f50057',
      },
      background: {
        default: darkMode ? '#0a1929' : '#f5f5f5',
        paper: darkMode ? '#132f4c' : '#ffffff',
      },
    },
    typography: {
      fontFamily: 'Inter, sans-serif',
      h4: {
        fontWeight: 600,
      },
      h5: {
        fontWeight: 600,
      },
      h6: {
        fontWeight: 600,
      },
    },
    shape: {
      borderRadius: 12,
    },
    components: {
      MuiButton: {
        styleOverrides: {
          root: {
            textTransform: 'none',
            fontWeight: 500,
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            backgroundImage: 'none',
          },
        },
      },
    },
  });

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Routes>
          <Route path="/" element={<Dashboard darkMode={darkMode} setDarkMode={setDarkMode} />} />
          <Route path="/new" element={<NewExperiment darkMode={darkMode} setDarkMode={setDarkMode} />} />
          <Route path="/experiment/:id" element={<ExperimentDetail darkMode={darkMode} setDarkMode={setDarkMode} />} />
          <Route path="/results" element={<Results darkMode={darkMode} setDarkMode={setDarkMode} />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </Router>
    </ThemeProvider>
  );
}

export default App;
