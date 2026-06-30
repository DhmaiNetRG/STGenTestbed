import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Paper,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  AppBar,
  Toolbar,
  IconButton,
  Chip,
  Tabs,
  Tab,
  LinearProgress,
} from '@mui/material';
import {
  ArrowBack as BackIcon,
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Download as DownloadIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts';
import api from '../api';

function ExperimentDetail({ darkMode, setDarkMode }) {
  const { id } = useParams();
  const navigate = useNavigate();
  
  const [experiment, setExperiment] = useState(null);
  const [logs, setLogs] = useState('');
  const [metrics, setMetrics] = useState([]);
  const [activeTab, setActiveTab] = useState(0);
  const [ws, setWs] = useState(null);

  useEffect(() => {
    loadExperiment();
    loadLogs();
    
    // Poll for updates every 2 seconds
    const interval = setInterval(() => {
      loadExperiment();
      loadLogs();
    }, 2000);
    
    return () => clearInterval(interval);
  }, [id]);
  
  // Separate useEffect for WebSocket to avoid dependency issues
  useEffect(() => {
    if (experiment?.status === 'running') {
      const websocket = new WebSocket(api.getWebSocketURL(id));
      
      websocket.onopen = () => {
        console.log('WebSocket connected for experiment', id);
      };
      
      websocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'metrics') {
          setMetrics(prev => [...prev.slice(-50), data.data]);
        }
      };
      
      websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
      
      setWs(websocket);
      
      return () => {
        console.log('Closing WebSocket for experiment', id);
        websocket.close();
      };
    }
  }, [experiment?.status, id]);

  const loadExperiment = async () => {
    try {
      const response = await api.getExperiment(id);
      setExperiment(response.data);
    } catch (error) {
      console.error('Error loading experiment:', error);
      console.error('Error details:', error.response?.data || error.message);
    }
  };

  const loadLogs = async () => {
    try {
      const response = await api.getExperimentLogs(id);
      console.log('Logs response:', response.data);
      const logText = response.data.logs || response.data || '';
      setLogs(logText);
    } catch (error) {
      console.error('Error loading logs:', error);
      console.error('Error details:', error.response?.data || error.message);
      // Set empty logs on error  
      setLogs('');
    }
  };

  const handleStart = async () => {
    try {
      await api.startExperiment(id);
      loadExperiment();
    } catch (error) {
      console.error('Error starting experiment:', error);
    }
  };

  const handleStop = async () => {
    try {
      await api.stopExperiment(id);
      loadExperiment();
    } catch (error) {
      console.error('Error stopping experiment:', error);
    }
  };

  const handleDownload = () => {
    window.open(api.downloadResults(id), '_blank');
  };

  if (!experiment) {
    return <LinearProgress />;
  }

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
          <IconButton color="inherit" onClick={() => navigate('/')} sx={{ mr: 2 }}>
            <BackIcon />
          </IconButton>
          <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 700 }}>
            {experiment.name}
          </Typography>
          <Chip 
            label={experiment.status} 
            color={getStatusColor(experiment.status)}
            sx={{ mr: 2 }}
          />
          {experiment.status === 'created' && (
            <Button
              variant="contained"
              startIcon={<PlayIcon />}
              onClick={handleStart}
              sx={{ mr: 1 }}
            >
              Start
            </Button>
          )}
          {experiment.status === 'running' && (
            <Button
              variant="outlined"
              color="warning"
              startIcon={<StopIcon />}
              onClick={handleStop}
              sx={{ mr: 1 }}
            >
              Stop
            </Button>
          )}
          {(experiment.status === 'completed' || experiment.status === 'stopped') && (
            <Button
              variant="outlined"
              startIcon={<DownloadIcon />}
              onClick={handleDownload}
            >
              Download
            </Button>
          )}
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ mt: 4 }}>
        {/* Configuration Overview */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" sx={{ mb: 2 }}>Configuration</Typography>
          <Grid container spacing={2}>
            <Grid item xs={6} md={3}>
              <Typography variant="body2" color="text.secondary">Protocol</Typography>
              <Typography variant="body1" fontWeight={600}>
                {experiment.config.protocol.toUpperCase()}
              </Typography>
            </Grid>
            <Grid item xs={6} md={3}>
              <Typography variant="body2" color="text.secondary">Clients</Typography>
              <Typography variant="body1" fontWeight={600}>
                {experiment.config.num_clients}
              </Typography>
            </Grid>
            <Grid item xs={6} md={3}>
              <Typography variant="body2" color="text.secondary">Duration</Typography>
              <Typography variant="body1" fontWeight={600}>
                {experiment.config.duration}s
              </Typography>
            </Grid>
            <Grid item xs={6} md={3}>
              <Typography variant="body2" color="text.secondary">Network Profile</Typography>
              <Typography variant="body1" fontWeight={600}>
                {experiment.config.network_profile}
              </Typography>
            </Grid>
          </Grid>
        </Paper>

        {/* Metrics */}
        {experiment.metrics && (
          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={12} md={3}>
              <Card>
                <CardContent>
                  <Typography variant="body2" color="text.secondary">Messages Sent</Typography>
                  <Typography variant="h4">{experiment.metrics.messages_sent || 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={3}>
              <Card>
                <CardContent>
                  <Typography variant="body2" color="text.secondary">Messages Received</Typography>
                  <Typography variant="h4">{experiment.metrics.messages_received || 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={3}>
              <Card>
                <CardContent>
                  <Typography variant="body2" color="text.secondary">Packet Loss</Typography>
                  <Typography variant="h4">
                    {experiment.metrics.packet_loss_percent?.toFixed(2) || 0}%
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={3}>
              <Card>
                <CardContent>
                  <Typography variant="body2" color="text.secondary">Avg Latency</Typography>
                  <Typography variant="h4">
                    {experiment.metrics.avg_latency_ms?.toFixed(2) || 0}ms
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}

        {/* Tabs */}
        <Paper>
          <Tabs value={activeTab} onChange={(e, v) => setActiveTab(v)}>
            <Tab label="Real-time Metrics" />
            <Tab label="Logs" />
          </Tabs>

          <Box sx={{ p: 3 }}>
            {activeTab === 0 && (
              <Box>
                {metrics.length > 0 ? (
                  <>
                    <Typography variant="h6" sx={{ mb: 2 }}>CPU & Memory Usage</Typography>
                    <ResponsiveContainer width="100%" height={300}>
                      <AreaChart data={metrics}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="uptime_seconds" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Area 
                          type="monotone" 
                          dataKey="cpu_percent" 
                          stroke="#8884d8" 
                          fill="#8884d8"
                          name="CPU %"
                        />
                        <Area 
                          type="monotone" 
                          dataKey="memory_mb" 
                          stroke="#82ca9d" 
                          fill="#82ca9d"
                          name="Memory (MB)"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </>
                ) : (
                  <Typography color="text.secondary">
                    No real-time metrics available. Start the experiment to see live data.
                  </Typography>
                )}
              </Box>
            )}

            {activeTab === 1 && (
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                  <Typography variant="h6">Logs</Typography>
                  <Button
                    size="small"
                    startIcon={<RefreshIcon />}
                    onClick={loadLogs}
                  >
                    Refresh
                  </Button>
                </Box>
                <Paper 
                  sx={{ 
                    p: 2, 
                    bgcolor: darkMode ? '#000' : '#f5f5f5',
                    maxHeight: 400,
                    overflow: 'auto'
                  }}
                >
                  <pre style={{ margin: 0, fontSize: '0.875rem', whiteSpace: 'pre-wrap' }}>
                    {logs || 'No logs available'}
                  </pre>
                </Paper>
              </Box>
            )}
          </Box>
        </Paper>
      </Container>
    </Box>
  );
}

export default ExperimentDetail;
