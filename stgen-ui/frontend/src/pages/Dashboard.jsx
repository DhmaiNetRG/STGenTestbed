import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  IconButton,
  Chip,
  LinearProgress,
  AppBar,
  Toolbar,
  Paper,
} from '@mui/material';
import {
  Add as AddIcon,
  Refresh as RefreshIcon,
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Delete as DeleteIcon,
  Brightness4 as DarkIcon,
  Brightness7 as LightIcon,
  Assessment as AssessmentIcon,
  Memory as MemoryIcon,
  Speed as SpeedIcon,
} from '@mui/icons-material';
import api from '../api';

function Dashboard({ darkMode, setDarkMode }) {
  const navigate = useNavigate();
  const [experiments, setExperiments] = useState([]);
  const [systemStats, setSystemStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const [expResponse, statsResponse] = await Promise.all([
        api.listExperiments(),
        api.getSystemStats()
      ]);
      setExperiments(expResponse.data);
      setSystemStats(statsResponse.data);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleStart = async (id) => {
    try {
      await api.startExperiment(id);
      loadData();
    } catch (error) {
      console.error('Error starting experiment:', error);
    }
  };

  const handleStop = async (id) => {
    try {
      await api.stopExperiment(id);
      loadData();
    } catch (error) {
      console.error('Error stopping experiment:', error);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this experiment?')) {
      try {
        await api.deleteExperiment(id);
        loadData();
      } catch (error) {
        console.error('Error deleting experiment:', error);
      }
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      created: 'default',
      running: 'primary',
      completed: 'success',
      failed: 'error',
      stopped: 'warning',
    };
    return colors[status] || 'default';
  };

  return (
    <Box sx={{ minHeight: '100vh', pb: 4 }}>
      <AppBar position="static" elevation={0}>
        <Toolbar>
          <AssessmentIcon sx={{ mr: 2 }} />
          <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 700 }}>
            STGen Dashboard
          </Typography>
          <IconButton color="inherit" onClick={() => setDarkMode(!darkMode)}>
            {darkMode ? <LightIcon /> : <DarkIcon />}
          </IconButton>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ mt: 4 }}>
        {/* System Stats */}
        {systemStats && (
          <Grid container spacing={3} sx={{ mb: 4 }}>
            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <MemoryIcon sx={{ mr: 1, color: 'primary.main' }} />
                  <Typography variant="h6">CPU Usage</Typography>
                </Box>
                <Typography variant="h3" sx={{ mb: 1 }}>
                  {systemStats.cpu.percent.toFixed(1)}%
                </Typography>
                <LinearProgress 
                  variant="determinate" 
                  value={systemStats.cpu.percent} 
                  sx={{ height: 8, borderRadius: 4 }}
                />
              </Paper>
            </Grid>
            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <SpeedIcon sx={{ mr: 1, color: 'success.main' }} />
                  <Typography variant="h6">Memory</Typography>
                </Box>
                <Typography variant="h3" sx={{ mb: 1 }}>
                  {systemStats.memory.percent.toFixed(1)}%
                </Typography>
                <LinearProgress 
                  variant="determinate" 
                  value={systemStats.memory.percent} 
                  color="success"
                  sx={{ height: 8, borderRadius: 4 }}
                />
                <Typography variant="caption" sx={{ mt: 1, display: 'block' }}>
                  {systemStats.memory.available_gb.toFixed(1)} GB / {systemStats.memory.total_gb.toFixed(1)} GB available
                </Typography>
              </Paper>
            </Grid>
            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" sx={{ mb: 2 }}>Experiments</Typography>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography>Total:</Typography>
                  <Typography fontWeight={600}>{experiments.length}</Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography>Running:</Typography>
                  <Typography fontWeight={600} color="primary.main">
                    {experiments.filter(e => e.status === 'running').length}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography>Completed:</Typography>
                  <Typography fontWeight={600} color="success.main">
                    {experiments.filter(e => e.status === 'completed').length}
                  </Typography>
                </Box>
              </Paper>
            </Grid>
          </Grid>
        )}

        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h5">Experiments</Typography>
          <Box>
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={loadData}
              sx={{ mr: 2 }}
            >
              Refresh
            </Button>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => navigate('/new')}
            >
              New Experiment
            </Button>
          </Box>
        </Box>

        {/* Experiments List */}
        {loading ? (
          <LinearProgress />
        ) : experiments.length === 0 ? (
          <Paper sx={{ p: 8, textAlign: 'center' }}>
            <Typography variant="h6" color="text.secondary" sx={{ mb: 2 }}>
              No experiments yet
            </Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => navigate('/new')}
            >
              Create Your First Experiment
            </Button>
          </Paper>
        ) : (
          <Grid container spacing={3}>
            {experiments.map((exp) => (
              <Grid item xs={12} md={6} lg={4} key={exp.id}>
                <Card
                  sx={{
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    '&:hover': {
                      boxShadow: 6,
                      transform: 'translateY(-4px)',
                      transition: 'all 0.3s ease',
                    },
                  }}
                >
                  <CardContent sx={{ flexGrow: 1 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                      <Typography variant="h6" sx={{ fontWeight: 600 }}>
                        {exp.name}
                      </Typography>
                      <Chip 
                        label={exp.status} 
                        color={getStatusColor(exp.status)}
                        size="small"
                      />
                    </Box>

                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      Protocol: <strong>{exp.config.protocol.toUpperCase()}</strong>
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      Clients: <strong>{exp.config.num_clients}</strong>
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      Duration: <strong>{exp.config.duration}s</strong>
                    </Typography>

                    {exp.metrics && (
                      <Box sx={{ mt: 2, p: 2, bgcolor: 'action.hover', borderRadius: 2 }}>
                        <Typography variant="caption" display="block">
                          Sent: {exp.metrics.messages_sent || 0}
                        </Typography>
                        <Typography variant="caption" display="block">
                          Received: {exp.metrics.messages_received || 0}
                        </Typography>
                        <Typography variant="caption" display="block">
                          Loss: {exp.metrics.packet_loss_percent?.toFixed(2) || 0}%
                        </Typography>
                      </Box>
                    )}

                    <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                      {exp.status === 'created' && (
                        <Button
                          size="small"
                          variant="contained"
                          startIcon={<PlayIcon />}
                          onClick={() => handleStart(exp.id)}
                        >
                          Start
                        </Button>
                      )}
                      {exp.status === 'running' && (
                        <Button
                          size="small"
                          variant="outlined"
                          color="warning"
                          startIcon={<StopIcon />}
                          onClick={() => handleStop(exp.id)}
                        >
                          Stop
                        </Button>
                      )}
                      <Button
                        size="small"
                        variant="outlined"
                        onClick={() => navigate(`/experiment/${exp.id}`)}
                      >
                        Details
                      </Button>
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => handleDelete(exp.id)}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}
      </Container>
    </Box>
  );
}

export default Dashboard;
