##! @file sensor_data_logger.py
##! @brief Sensor Data Logger - Persistent storage for sensor readings
##!
##! @details
##! Writes sensor data to separate files based on sensor type.
##! All files stored in a single directory with clean formatting.
##!
##! @author STGen Development Team
##! @version 1.0
##! @date 2024

import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional

_LOG = logging.getLogger("sensor_logger")


class SensorDataLogger:
    """
    Logger for writing sensor data to disk, organized by sensor type.
    
    Creates separate files for each sensor type:
    - sensor_log/temp_data.txt
    - sensor_log/humidity_data.txt
    - sensor_log/motion_data.txt
    - etc.
    """
    
    def __init__(self, log_dir: str = "sensor_log"):
        """
        Initialize logger with output directory.
        
        Args:
            log_dir: Directory to store sensor data files (default: sensor_log/)
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # File handles: {sensor_type: file_handle}
        self.file_handles: Dict[str, Any] = {}
        
        # Statistics: {sensor_type: count}
        self.record_count: Dict[str, int] = {}
        
        _LOG.info(f"Sensor logger initialized: {self.log_dir}")
    
    def _get_sensor_type(self, dev_id: str) -> str:
        """
        Extract sensor type from device ID.
        
        Examples:
            - "temp_0" → "temp"
            - "humidity_1" → "humidity"
            - "gps_2" → "gps"
            - "motion_3" → "motion"
        
        Args:
            dev_id: Device identifier (format: sensor_type_index)
        
        Returns:
            Sensor type string
        """
        parts = dev_id.split("_")
        if len(parts) >= 2:
            return parts[0]
        return dev_id
    
    def _get_file_handle(self, sensor_type: str) -> Any:
        """
        Get or create file handle for sensor type.
        
        Args:
            sensor_type: Type of sensor (temp, humidity, etc.)
        
        Returns:
            Open file handle
        """
        if sensor_type not in self.file_handles:
            file_path = self.log_dir / f"{sensor_type}_data.txt"
            
            # Write header if file is new
            is_new = not file_path.exists()
            
            handle = open(file_path, "a")  # Append mode
            
            if is_new:
                handle.write("# Sensor Type: {}\n".format(sensor_type))
                handle.write("# Format: timestamp | sequence | dev_id | sensor_value\n")
                handle.write("# " + "="*70 + "\n")
            
            self.file_handles[sensor_type] = handle
            self.record_count[sensor_type] = 0
            
            _LOG.info(f"Created data file: {file_path}")
        
        return self.file_handles[sensor_type]
    
    def log_sensor_data(self, data: Dict[str, Any]) -> None:
        """
        Write sensor reading to appropriate file.
        
        Args:
            data: Sensor data dict with keys:
                - dev_id: Device identifier (e.g., "temp_0")
                - ts: Timestamp
                - seq_no: Sequence number
                - sensor_data: Sensor reading dict
        """
        try:
            dev_id = data.get("dev_id", "unknown")
            sensor_type = self._get_sensor_type(dev_id)
            ts = data.get("ts", time.time())
            seq_no = data.get("seq_no", 0)
            sensor_data = data.get("sensor_data", {})
            
            # Get file handle
            handle = self._get_file_handle(sensor_type)
            
            # Format sensor value for display
            if isinstance(sensor_data, dict):
                # Extract value and unit if available
                value = sensor_data.get("value", sensor_data.get("detected", str(sensor_data)))
                unit = sensor_data.get("unit", "")
                sensor_str = f"{value} {unit}".strip()
            else:
                sensor_str = str(sensor_data)
            
            # Write line: timestamp | seq_no | dev_id | sensor_value
            line = f"{ts:.3f} | {seq_no:6d} | {dev_id:15s} | {sensor_str}\n"
            handle.write(line)
            
            # Increment counter
            self.record_count[sensor_type] = self.record_count.get(sensor_type, 0) + 1
            
            # Flush periodically (every 10 records)
            if self.record_count[sensor_type] % 10 == 0:
                handle.flush()
        
        except Exception as e:
            _LOG.error(f"Failed to log sensor data: {e}")
    
    def log_sensor_data_json(self, data: Dict[str, Any]) -> None:
        """
        Write sensor reading as JSON (alternative format).
        
        Args:
            data: Sensor data dict
        """
        try:
            dev_id = data.get("dev_id", "unknown")
            sensor_type = self._get_sensor_type(dev_id)
            
            # Key must match: use "sensor_type_json" for identification AND storage
            json_key = f"{sensor_type}_json"
            file_path = self.log_dir / f"{sensor_type}_data.jsonl"

            # FIX: Check in self.file_handles using the same key we store under
            if json_key not in self.file_handles:
                handle = open(file_path, "a")
                self.file_handles[json_key] = handle
            else:
                handle = self.file_handles[json_key]
            
            # Write as JSON line
            json_line = json.dumps(data) + "\n"
            handle.write(json_line)
            
            # Increment counter for this sensor type
            self.record_count[sensor_type] = self.record_count.get(sensor_type, 0) + 1
            
            # Flush periodically
            if self.record_count.get(sensor_type, 0) % 10 == 0:
                handle.flush()
        
        except Exception as e:
            _LOG.error(f"Failed to log JSON: {e}")
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get record count per sensor type.
        
        Returns:
            Dict mapping sensor type to record count
        """
        return dict(self.record_count)
    
    def flush_all(self) -> None:
        """Flush all file buffers."""
        for handle in self.file_handles.values():
            try:
                handle.flush()
            except:
                pass
    
    def close(self) -> None:
        """
        Close all file handles and print summary.
        """
        # Flush all data
        self.flush_all()
        
        # Close files
        for sensor_type, handle in self.file_handles.items():
            try:
                handle.close()
                _LOG.info(f"Closed {sensor_type}: {self.record_count.get(sensor_type, 0)} records")
            except:
                pass
        
        # Print summary
        _LOG.info(f"Sensor data logging complete")
        _LOG.info(f"Output directory: {self.log_dir}")
        _LOG.info(f"Files written:")
        for sensor_type, count in sorted(self.record_count.items()):
            if count > 0:
                file_path = self.log_dir / f"{sensor_type}_data.txt"
                _LOG.info(f"  - {file_path.name}: {count} records")
        
        self.file_handles.clear()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False