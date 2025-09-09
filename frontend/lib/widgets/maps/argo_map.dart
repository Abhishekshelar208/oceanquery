import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../../themes/app_theme.dart';
import '../../services/api/api_client.dart';

class ArgoMap extends StatefulWidget {
  const ArgoMap({super.key});

  @override
  State<ArgoMap> createState() => _ArgoMapState();
}

class _ArgoMapState extends State<ArgoMap> {
  final MapController _mapController = MapController();
  final ApiClient _apiClient = ApiClient();
  
  List<Map<String, dynamic>> _floats = [];
  bool _isLoading = true;
  String? _error;
  
  @override
  void initState() {
    super.initState();
    _loadFloats();
  }
  
  Future<void> _loadFloats() async {
    try {
      setState(() {
        _isLoading = true;
        _error = null;
      });
      
      final floats = await _apiClient.getFloats(limit: 100);
      
      setState(() {
        _floats = floats.cast<Map<String, dynamic>>();
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Container(
        height: 400,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Colors.grey.shade300),
        ),
        child: const Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              CircularProgressIndicator(),
              SizedBox(height: 16),
              Text('Loading ARGO floats...'),
            ],
          ),
        ),
      );
    }
    
    if (_error != null) {
      return Container(
        height: 400,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Colors.red.shade300),
        ),
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error, color: Colors.red, size: 48),
              const SizedBox(height: 16),
              Text('Error loading floats: $_error'),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: _loadFloats,
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }
    
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.grey.shade300),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: FlutterMap(
          mapController: _mapController,
          options: const MapOptions(
            initialCenter: LatLng(15.0, 75.0), // Indian Ocean
            initialZoom: 5.0,
            minZoom: 2.0,
            maxZoom: 18.0,
            interactionOptions: InteractionOptions(
              enableMultiFingerGestureRace: true,
            ),
          ),
          children: [
            // Base map layer
            TileLayer(
              urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
              userAgentPackageName: 'com.oceanquery.app',
              maxZoom: 18,
            ),
            
            // ARGO float markers
            MarkerLayer(
              markers: _generateFloatMarkers(),
            ),
            
            // Map attribution
            const SimpleAttributionWidget(
              source: Text('© OpenStreetMap'),
            ),
            
            // Custom controls
            Positioned(
              top: 10,
              right: 10,
              child: Column(
                children: [
                  Container(
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(8),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.1),
                          blurRadius: 4,
                          offset: const Offset(0, 2),
                        ),
                      ],
                    ),
                    child: Column(
                      children: [
                        IconButton(
                          icon: const Icon(Icons.add),
                          onPressed: () {
                            _mapController.move(
                              _mapController.camera.center,
                              _mapController.camera.zoom + 1,
                            );
                          },
                          tooltip: 'Zoom in',
                        ),
                        IconButton(
                          icon: const Icon(Icons.remove),
                          onPressed: () {
                            _mapController.move(
                              _mapController.camera.center,
                              _mapController.camera.zoom - 1,
                            );
                          },
                          tooltip: 'Zoom out',
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(4),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.1),
                          blurRadius: 4,
                          offset: const Offset(0, 2),
                        ),
                      ],
                    ),
                    child: Text(
                      '${_floats.length} Floats',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: AppTheme.primaryBlue,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            
            // Legend
            Positioned(
              bottom: 30,
              left: 10,
              child: Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.9),
                  borderRadius: BorderRadius.circular(8),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.1),
                      blurRadius: 4,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Text(
                      'ARGO Floats',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 12,
                          height: 12,
                          decoration: const BoxDecoration(
                            color: AppTheme.success,
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 4),
                        const Text('Active', style: TextStyle(fontSize: 10)),
                      ],
                    ),
                    const SizedBox(height: 2),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 12,
                          height: 12,
                          decoration: const BoxDecoration(
                            color: AppTheme.warning,
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 4),
                        const Text('Inactive', style: TextStyle(fontSize: 10)),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  List<Marker> _generateFloatMarkers() {
    if (_floats.isEmpty) return [];
    
    return _floats.map((floatData) {
      final lastPosition = floatData['last_position'];
      if (lastPosition == null || 
          lastPosition['lat'] == null || 
          lastPosition['lon'] == null) {
        return null;
      }
      
      final isActive = floatData['status'] == 'active';
      final lat = lastPosition['lat'] as double;
      final lon = lastPosition['lon'] as double;
      
      return Marker(
        point: LatLng(lat, lon),
        child: GestureDetector(
          onTap: () => _showFloatInfo(floatData),
          child: Container(
            width: 16,
            height: 16,
            decoration: BoxDecoration(
              color: isActive ? AppTheme.success : AppTheme.warning,
              shape: BoxShape.circle,
              border: Border.all(color: Colors.white, width: 2),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.2),
                  blurRadius: 3,
                  offset: const Offset(0, 1),
                ),
              ],
            ),
            child: Icon(
              Icons.sensors,
              size: 8,
              color: Colors.white,
            ),
          ),
        ),
      );
    }).where((marker) => marker != null).cast<Marker>().toList();
  }

  void _showFloatInfo(Map<String, dynamic> floatData) {
    final isActive = floatData['status'] == 'active';
    final floatId = floatData['float_id'] as String;
    final lastPosition = floatData['last_position'];
    final totalProfiles = floatData['total_profiles'] ?? 0;
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('ARGO Float $floatId'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.circle,
                  size: 12,
                  color: isActive ? AppTheme.success : AppTheme.warning,
                ),
                const SizedBox(width: 4),
                Text(
                  isActive ? 'Active' : 'Inactive',
                  style: TextStyle(
                    color: isActive ? AppTheme.success : AppTheme.warning,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            if (lastPosition != null && lastPosition['date'] != null)
              Text('Last position: ${lastPosition['date']}'),
            const SizedBox(height: 4),
            Text('Profiles collected: $totalProfiles'),
            const SizedBox(height: 4),
            if (lastPosition != null)
              Text('Position: ${lastPosition['lat']?.toStringAsFixed(2)}°, ${lastPosition['lon']?.toStringAsFixed(2)}°'),
            const SizedBox(height: 4),
            Text('Platform: ${floatData['platform_number'] ?? 'Unknown'}'),
            const SizedBox(height: 4),
            Text('Institution: ${floatData['institution'] ?? 'Unknown'}'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.of(context).pop();
              _viewFloatDetails(floatId);
            },
            child: const Text('View Data'),
          ),
        ],
      ),
    );
  }
  
  void _viewFloatDetails(String floatId) {
    // TODO: Navigate to detailed float data view
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Viewing details for float $floatId'),
        backgroundColor: AppTheme.primaryBlue,
      ),
    );
  }
}
