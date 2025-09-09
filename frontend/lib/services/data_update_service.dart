import 'dart:async';
import 'dart:developer' as developer;
import 'package:flutter/foundation.dart';
import 'api/api_client.dart';

enum DataUpdateStatus {
  idle,
  checking,
  updating,
  success,
  error,
}

class DataUpdateEvent {
  final DataUpdateStatus status;
  final String message;
  final DateTime timestamp;
  final Map<String, dynamic>? data;
  final String? error;

  DataUpdateEvent({
    required this.status,
    required this.message,
    required this.timestamp,
    this.data,
    this.error,
  });
}

class DataUpdateService extends ChangeNotifier {
  static final DataUpdateService _instance = DataUpdateService._internal();
  factory DataUpdateService() => _instance;
  DataUpdateService._internal();

  final ApiClient _apiClient = ApiClient();
  
  Timer? _updateTimer;
  Timer? _heartbeatTimer;
  
  DataUpdateStatus _status = DataUpdateStatus.idle;
  String _message = 'Ready';
  DateTime _lastUpdate = DateTime.now();
  Map<String, dynamic> _lastUpdateData = {};
  String? _error;
  
  // Update frequency settings
  Duration _updateInterval = const Duration(minutes: 30);
  Duration _heartbeatInterval = const Duration(minutes: 5);
  
  // Stream for real-time updates
  final StreamController<DataUpdateEvent> _eventController = 
      StreamController<DataUpdateEvent>.broadcast();
  
  Stream<DataUpdateEvent> get updateStream => _eventController.stream;
  
  // Getters
  DataUpdateStatus get status => _status;
  String get message => _message;
  DateTime get lastUpdate => _lastUpdate;
  Map<String, dynamic> get lastUpdateData => _lastUpdateData;
  String? get error => _error;
  Duration get updateInterval => _updateInterval;
  bool get isRunning => _updateTimer?.isActive ?? false;

  // Configuration
  void setUpdateInterval(Duration interval) {
    _updateInterval = interval;
    if (isRunning) {
      stop();
      start();
    }
  }

  void setHeartbeatInterval(Duration interval) {
    _heartbeatInterval = interval;
    if (isRunning) {
      _startHeartbeat();
    }
  }

  // Control methods
  void start() {
    if (_updateTimer?.isActive == true) {
      stop();
    }
    
    developer.log('Starting real-time data update service');
    _updateStatus(DataUpdateStatus.checking, 'Starting data update service...');
    
    // Start periodic updates
    _updateTimer = Timer.periodic(_updateInterval, (_) => _performUpdate());
    
    // Start heartbeat for connection monitoring
    _startHeartbeat();
    
    // Perform initial update
    _performUpdate();
  }

  void stop() {
    developer.log('Stopping real-time data update service');
    _updateTimer?.cancel();
    _heartbeatTimer?.cancel();
    _updateStatus(DataUpdateStatus.idle, 'Data update service stopped');
  }

  void forceUpdate() {
    developer.log('Forcing immediate data update');
    _performUpdate();
  }

  // Private methods
  void _startHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer.periodic(_heartbeatInterval, (_) => _performHeartbeat());
  }

  Future<void> _performUpdate() async {
    if (_status == DataUpdateStatus.updating) {
      developer.log('Update already in progress, skipping');
      return;
    }

    try {
      _updateStatus(DataUpdateStatus.updating, 'Checking for data updates...');
      
      // Check for new ARGO data
      final updateInfo = await _checkForNewData();
      
      if (updateInfo['hasNewData'] == true) {
        _updateStatus(DataUpdateStatus.updating, 'Downloading new data...');
        await _downloadNewData(updateInfo);
        
        _lastUpdate = DateTime.now();
        _lastUpdateData = updateInfo;
        
        _updateStatus(
          DataUpdateStatus.success,
          'Updated successfully - ${updateInfo['newFloats'] ?? 0} floats, ${updateInfo['newProfiles'] ?? 0} profiles',
        );
        
        // Notify listeners about successful update
        _eventController.add(DataUpdateEvent(
          status: DataUpdateStatus.success,
          message: 'Data updated successfully',
          timestamp: DateTime.now(),
          data: updateInfo,
        ));
        
      } else {
        _updateStatus(DataUpdateStatus.success, 'Data is up to date');
      }
      
    } catch (e) {
      _error = e.toString();
      _updateStatus(DataUpdateStatus.error, 'Update failed: $e');
      
      // Notify listeners about error
      _eventController.add(DataUpdateEvent(
        status: DataUpdateStatus.error,
        message: 'Update failed',
        timestamp: DateTime.now(),
        error: e.toString(),
      ));
      
      developer.log('Data update failed: $e');
    }
  }

  Future<void> _performHeartbeat() async {
    try {
      // Simple health check to ensure backend connectivity
      await _apiClient.healthCheck();
      
      // If we were in error state, mark as recovered
      if (_status == DataUpdateStatus.error) {
        _updateStatus(DataUpdateStatus.idle, 'Connection restored');
        _error = null;
      }
      
    } catch (e) {
      if (_status != DataUpdateStatus.error) {
        _updateStatus(DataUpdateStatus.error, 'Connection lost');
        _error = 'Backend connection failed';
        
        _eventController.add(DataUpdateEvent(
          status: DataUpdateStatus.error,
          message: 'Connection lost',
          timestamp: DateTime.now(),
          error: e.toString(),
        ));
      }
      
      developer.log('Heartbeat failed: $e');
    }
  }

  Future<Map<String, dynamic>> _checkForNewData() async {
    // Get current statistics
    final currentStats = await _apiClient.getArgoStatistics();
    
    // Compare with last known state
    final lastKnownFloats = _lastUpdateData['totalFloats'] ?? 0;
    final lastKnownProfiles = _lastUpdateData['totalProfiles'] ?? 0;
    
    final currentFloats = currentStats['total_floats'] ?? 0;
    final currentProfiles = currentStats['total_profiles'] ?? 0;
    
    final hasNewFloats = currentFloats > lastKnownFloats;
    final hasNewProfiles = currentProfiles > lastKnownProfiles;
    final hasNewData = hasNewFloats || hasNewProfiles;
    
    developer.log('Data check: Floats: $lastKnownFloats -> $currentFloats, Profiles: $lastKnownProfiles -> $currentProfiles');
    
    return {
      'hasNewData': hasNewData,
      'totalFloats': currentFloats,
      'totalProfiles': currentProfiles,
      'newFloats': currentFloats - lastKnownFloats,
      'newProfiles': currentProfiles - lastKnownProfiles,
      'lastUpdated': currentStats['last_updated'],
      'statistics': currentStats,
    };
  }

  Future<void> _downloadNewData(Map<String, dynamic> updateInfo) async {
    // Simulate data download process
    // In a real implementation, this would:
    // 1. Download new NetCDF files from ARGO repositories
    // 2. Process and ingest them into the database
    // 3. Update local caches
    
    await Future.delayed(const Duration(seconds: 2)); // Simulate processing time
    
    developer.log('Downloaded ${updateInfo['newFloats']} new floats and ${updateInfo['newProfiles']} new profiles');
  }

  void _updateStatus(DataUpdateStatus status, String message) {
    _status = status;
    _message = message;
    notifyListeners();
    
    developer.log('DataUpdateService: $message');
  }

  // Utility methods for UI components
  String get statusDisplayText {
    switch (_status) {
      case DataUpdateStatus.idle:
        return 'Ready';
      case DataUpdateStatus.checking:
        return 'Checking...';
      case DataUpdateStatus.updating:
        return 'Updating...';
      case DataUpdateStatus.success:
        return 'Up to date';
      case DataUpdateStatus.error:
        return 'Error';
    }
  }

  String get lastUpdateDisplayText {
    final now = DateTime.now();
    final difference = now.difference(_lastUpdate);
    
    if (difference.inMinutes < 1) {
      return 'Just now';
    } else if (difference.inHours < 1) {
      return '${difference.inMinutes} minutes ago';
    } else if (difference.inDays < 1) {
      return '${difference.inHours} hours ago';
    } else {
      return '${difference.inDays} days ago';
    }
  }

  // Configuration methods
  Map<String, dynamic> getConfiguration() {
    return {
      'updateInterval': _updateInterval.inMinutes,
      'heartbeatInterval': _heartbeatInterval.inMinutes,
      'isRunning': isRunning,
      'autoStart': true, // Could be made configurable
    };
  }

  void updateConfiguration(Map<String, dynamic> config) {
    if (config.containsKey('updateInterval')) {
      setUpdateInterval(Duration(minutes: config['updateInterval']));
    }
    
    if (config.containsKey('heartbeatInterval')) {
      setHeartbeatInterval(Duration(minutes: config['heartbeatInterval']));
    }
    
    if (config.containsKey('isRunning')) {
      final shouldRun = config['isRunning'] as bool;
      if (shouldRun && !isRunning) {
        start();
      } else if (!shouldRun && isRunning) {
        stop();
      }
    }
  }

  @override
  void dispose() {
    stop();
    _eventController.close();
    super.dispose();
  }
}
