import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Paper,
  Typography,
  TextField,
  Button,
  MenuItem,
  Grid,
  Stepper,
  Step,
  StepLabel,
  FormControl,
  InputLabel,
  Select,
  Chip,
  OutlinedInput,
  AppBar,
  Toolbar,
  IconButton,
} from '@mui/material';
import {
  ArrowBack as BackIcon,
  PlayArrow as StartIcon,
  Save as SaveIcon,
} from '@mui/icons-material';
import api from '../api';

const steps = ['Basic Configuration', 'Sensors & Traffic', 'Network Conditions', 'Review'];

function NewExperiment({ darkMode, setDarkMode }) {
  const navigate = useNavigate();
  const [activeStep, setActiveStep] = useState(0);
  
  // Configuration state
  const [config, setConfig] = useState({
    name: '',
    protocol: 'mqtt',
    mode: 'active',
    server_ip: '127.0.0.1',
    server_port: 1883,
    num_clients: 10,
    duration: 30,
    sensors: ['temp', 'humidity'],
    network_profile: 'perfect',
    deployment_mode: 'single',
  });

  // Available options
  const [protocols, setProtocols] = useState([]);
  const [sensorTypes, setSensorTypes] = useState([]);
  const [networkProfiles, setNetworkProfiles] = useState([]);

  useEffect(() => {
    loadOptions();
  }, []);

  const loadOptions = async () => {
    try {
      const [protocolsRes, sensorsRes, profilesRes] = await Promise.all([
        api.getProtocols(),
        api.getSensors(),
        api.getNetworkProfiles()
      ]);
      setProtocols(protocolsRes.data.protocols);
      setSensorTypes(sensorsRes.data.sensors);
      setNetworkProfiles(profilesRes.data.profiles);
    } catch (error) {
      console.error('Error loading options:', error);
    }
  };

  const handleNext = () => {
    setActiveStep((prev) => prev + 1);
  };

  const handleBack = () => {
    setActiveStep((prev) => prev - 1);
  };

  const handleSubmit = async (startImmediately = false) => {
    try {
      const response = await api.createExperiment(config);
      const expId = response.data.id;
      
      if (startImmediately) {
        await api.startExperiment(expId);
      }
      
      navigate(`/experiment/${expId}`);
    } catch (error) {
      console.error('Error creating experiment:', error);
      alert('Failed to create experiment: ' + error.message);
    }
  };

  const handleProtocolChange = (protocol) => {
    const selected = protocols.find(p => p.id === protocol);
    setConfig({
      ...config,
      protocol: protocol,
      server_port: selected?.port || 1883
    });
  };

  const renderStepContent = (step) => {
    switch (step) {
      case 0:
        return (
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Experiment Name"
                value={config.name}
                onChange={(e) => setConfig({ ...config, name: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Protocol</InputLabel>
                <Select
                  value={config.protocol}
                  onChange={(e) => handleProtocolChange(e.target.value)}
                  label="Protocol"
                >
                  {protocols.map((p) => (
                    <MenuItem key={p.id} value={p.id}>
                      {p.name} - {p.description}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Mode</InputLabel>
                <Select
                  value={config.mode}
                  onChange={(e) => setConfig({ ...config, mode: e.target.value })}
                  label="Mode"
                >
                  <MenuItem value="active">Active (Generate Traffic)</MenuItem>
                  <MenuItem value="passive">Passive (Replay)</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Server IP"
                value={config.server_ip}
                onChange={(e) => setConfig({ ...config, server_ip: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                type="number"
                label="Server Port"
                value={config.server_port}
                onChange={(e) => setConfig({ ...config, server_port: parseInt(e.target.value) || 0 })}
              />
            </Grid>
          </Grid>
        );

      case 1:
        return (
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                type="number"
                label="Number of Clients"
                value={config.num_clients}
                onChange={(e) => setConfig({ ...config, num_clients: parseInt(e.target.value) || 1 })}
                InputProps={{ inputProps: { min: 1, max: 1000 } }}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                type="number"
                label="Duration (seconds)"
                value={config.duration}
                onChange={(e) => setConfig({ ...config, duration: parseInt(e.target.value) || 5 })}
                InputProps={{ inputProps: { min: 5, max: 3600 } }}
              />
            </Grid>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Sensor Types</InputLabel>
                <Select
                  multiple
                  value={config.sensors}
                  onChange={(e) => setConfig({ ...config, sensors: e.target.value })}
                  input={<OutlinedInput label="Sensor Types" />}
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {selected.map((value) => (
                        <Chip key={value} label={value} size="small" />
                      ))}
                    </Box>
                  )}
                >
                  {sensorTypes.map((sensor) => (
                    <MenuItem key={sensor.id} value={sensor.id}>
                      {sensor.name} ({sensor.rate_hz} Hz)
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        );

      case 2:
        return (
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Network Profile</InputLabel>
                <Select
                  value={config.network_profile}
                  onChange={(e) => setConfig({ ...config, network_profile: e.target.value })}
                  label="Network Profile"
                >
                  {networkProfiles.map((profile) => (
                    <MenuItem key={profile.id} value={profile.id}>
                      <Box>
                        <Typography>{profile.name}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          Latency: {profile.latency}ms, Loss: {profile.loss}%, BW: {profile.bandwidth}
                        </Typography>
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Deployment Mode</InputLabel>
                <Select
                  value={config.deployment_mode}
                  onChange={(e) => setConfig({ ...config, deployment_mode: e.target.value })}
                  label="Deployment Mode"
                >
                  <MenuItem value="single">Single Machine</MenuItem>
                  <MenuItem value="distributed">Distributed</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        );

      case 3:
        return (
          <Box>
            <Typography variant="h6" sx={{ mb: 3 }}>Review Configuration</Typography>
            <Paper sx={{ p: 3, bgcolor: 'action.hover' }}>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Typography variant="body2" color="text.secondary">Name:</Typography>
                  <Typography variant="body1" fontWeight={600}>{config.name}</Typography>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="body2" color="text.secondary">Protocol:</Typography>
                  <Typography variant="body1" fontWeight={600}>{config.protocol.toUpperCase()}</Typography>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="body2" color="text.secondary">Clients:</Typography>
                  <Typography variant="body1" fontWeight={600}>{config.num_clients}</Typography>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="body2" color="text.secondary">Duration:</Typography>
                  <Typography variant="body1" fontWeight={600}>{config.duration}s</Typography>
                </Grid>
                <Grid item xs={12}>
                  <Typography variant="body2" color="text.secondary">Sensors:</Typography>
                  <Box sx={{ mt: 1 }}>
                    {config.sensors.map(s => (
                      <Chip key={s} label={s} size="small" sx={{ mr: 1, mb: 1 }} />
                    ))}
                  </Box>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="body2" color="text.secondary">Network Profile:</Typography>
                  <Typography variant="body1" fontWeight={600}>{config.network_profile}</Typography>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="body2" color="text.secondary">Server:</Typography>
                  <Typography variant="body1" fontWeight={600}>{config.server_ip}:{config.server_port}</Typography>
                </Grid>
              </Grid>
            </Paper>
          </Box>
        );

      default:
        return null;
    }
  };

  return (
    <Box sx={{ minHeight: '100vh', pb: 4 }}>
      <AppBar position="static" elevation={0}>
        <Toolbar>
          <IconButton color="inherit" onClick={() => navigate('/')} sx={{ mr: 2 }}>
            <BackIcon />
          </IconButton>
          <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 700 }}>
            New Experiment
          </Typography>
        </Toolbar>
      </AppBar>

      <Container maxWidth="md" sx={{ mt: 4 }}>
        <Paper sx={{ p: 4 }}>
          <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
            {steps.map((label) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>

          <Box sx={{ mb: 4 }}>
            {renderStepContent(activeStep)}
          </Box>

          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Button
              disabled={activeStep === 0}
              onClick={handleBack}
            >
              Back
            </Button>
            <Box>
              {activeStep === steps.length - 1 ? (
                <>
                  <Button
                    variant="outlined"
                    onClick={() => handleSubmit(false)}
                    startIcon={<SaveIcon />}
                    sx={{ mr: 2 }}
                  >
                    Save Only
                  </Button>
                  <Button
                    variant="contained"
                    onClick={() => handleSubmit(true)}
                    startIcon={<StartIcon />}
                  >
                    Create & Start
                  </Button>
                </>
              ) : (
                <Button
                  variant="contained"
                  onClick={handleNext}
                >
                  Next
                </Button>
              )}
            </Box>
          </Box>
        </Paper>
      </Container>
    </Box>
  );
}

export default NewExperiment;
